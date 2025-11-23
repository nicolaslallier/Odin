"""Database management service for PostgreSQL administration.

This module provides comprehensive database management capabilities including
table inspection, query execution, data export, and database statistics.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

import sqlparse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.api.exceptions import DatabaseError, ValidationError
from src.api.services.database import DatabaseService


@dataclass
class TableInfo:
    """Information about a database table.

    Attributes:
        schema_name: Schema containing the table
        table_name: Name of the table
        row_count: Approximate number of rows
        size_bytes: Size of the table in bytes
    """

    schema_name: str
    table_name: str
    row_count: int
    size_bytes: int


@dataclass
class TableSchema:
    """Schema information for a database table.

    Attributes:
        table_name: Name of the table
        columns: List of column definitions
    """

    table_name: str
    columns: List[dict[str, Any]]


@dataclass
class QueryResult:
    """Result of a query execution.

    Attributes:
        success: Whether the query executed successfully
        row_count: Number of rows affected or returned
        columns: List of column names (for SELECT queries)
        rows: List of result rows (for SELECT queries)
        error: Error message if query failed
        execution_time_ms: Time taken to execute query in milliseconds
    """

    success: bool
    row_count: int
    columns: List[str]
    rows: List[List[Any]]
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None


@dataclass
class DatabaseStats:
    """Database statistics and information.

    Attributes:
        database_size_bytes: Total size of the database
        version: PostgreSQL version string
        connection_count: Number of active connections
    """

    database_size_bytes: int
    version: str
    connection_count: int


class DatabaseManagementService:
    """Service for PostgreSQL database management operations.

    This service provides comprehensive database administration capabilities
    including table inspection, query execution, data browsing, and exports.
    """

    def __init__(self, db_service: DatabaseService) -> None:
        """Initialize database management service.

        Args:
            db_service: Database service for connection management
        """
        self.db_service = db_service

    async def get_all_tables(self) -> List[TableInfo]:
        """Get list of all tables in the database with metadata.

        Returns:
            List of TableInfo objects containing table metadata

        Raises:
            DatabaseError: If table retrieval fails
        """
        query = text("""
            SELECT 
                schemaname,
                relname as tablename,
                n_live_tup as row_count,
                pg_total_relation_size(schemaname||'.'||relname) as size_bytes
            FROM pg_stat_user_tables
            ORDER BY schemaname, relname
        """)

        try:
            async with self.db_service.get_session() as session:
                result = await session.execute(query)
                rows = result.fetchall()
                
                return [
                    TableInfo(
                        schema_name=row[0],
                        table_name=row[1],
                        row_count=row[2] or 0,
                        size_bytes=row[3] or 0,
                    )
                    for row in rows
                ]
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve tables: {e}")

    async def get_table_schema(self, table_name: str) -> TableSchema:
        """Get schema information for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            TableSchema object with column definitions

        Raises:
            DatabaseError: If table not found or schema retrieval fails
        """
        query = text("""
            SELECT 
                column_name,
                data_type,
                is_nullable::boolean as is_nullable,
                (
                    SELECT string_agg(constraint_type, ', ')
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE kcu.table_name = c.table_name 
                        AND kcu.column_name = c.column_name
                ) as constraints,
                column_default
            FROM information_schema.columns c
            WHERE table_name = :table_name
                AND table_schema = 'public'
            ORDER BY ordinal_position
        """)

        try:
            async with self.db_service.get_session() as session:
                result = await session.execute(query, {"table_name": table_name})
                rows = result.fetchall()
                
                if not rows:
                    raise DatabaseError(f"Table '{table_name}' not found or has no columns")
                
                columns = [
                    {
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2],
                        "constraint": row[3],
                        "default": row[4],
                    }
                    for row in rows
                ]
                
                return TableSchema(table_name=table_name, columns=columns)
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve table schema: {e}")

    def validate_sql(self, sql: str) -> dict[str, Any]:
        """Validate SQL query and detect destructive operations.

        Args:
            sql: SQL query string to validate

        Returns:
            Dictionary with validation results:
                - is_valid: Whether the query is valid
                - is_destructive: Whether the query modifies/deletes data
                - query_type: Type of query (SELECT, INSERT, etc.)
                - error: Error message if invalid
        """
        if not sql or not sql.strip():
            return {
                "is_valid": False,
                "is_destructive": False,
                "query_type": "UNKNOWN",
                "error": "Query is empty",
            }

        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                return {
                    "is_valid": False,
                    "is_destructive": False,
                    "query_type": "UNKNOWN",
                    "error": "Failed to parse query",
                }

            # Get the first statement
            statement = parsed[0]
            
            # Determine query type
            query_type = statement.get_type()
            if query_type is None:
                query_type = "UNKNOWN"
            else:
                query_type = query_type.upper()

            # Check if query is destructive
            destructive_types = {"DELETE", "DROP", "TRUNCATE", "ALTER"}
            is_destructive = query_type in destructive_types

            return {
                "is_valid": True,
                "is_destructive": is_destructive,
                "query_type": query_type,
                "error": None,
            }
        except Exception as e:
            return {
                "is_valid": False,
                "is_destructive": False,
                "query_type": "UNKNOWN",
                "error": str(e),
            }

    async def execute_query(self, sql: str, confirmed: bool = False) -> QueryResult:
        """Execute SQL query with safety checks.

        Args:
            sql: SQL query to execute
            confirmed: Whether destructive operations are confirmed

        Returns:
            QueryResult object with execution results

        Raises:
            ValidationError: If destructive query not confirmed
        """
        # Validate query
        validation = self.validate_sql(sql)
        
        if not validation["is_valid"]:
            return QueryResult(
                success=False,
                row_count=0,
                columns=[],
                rows=[],
                error=validation["error"],
            )

        # Check for destructive operations
        if validation["is_destructive"] and not confirmed:
            raise ValidationError(
                "Destructive query requires confirmation",
                {"query_type": validation["query_type"]},
            )

        start_time = datetime.now()
        
        try:
            async with self.db_service.get_session() as session:
                result = await session.execute(text(sql))
                
                # For SELECT queries, fetch results
                if validation["query_type"] == "SELECT":
                    rows = result.fetchall()
                    columns = list(result.keys())
                    
                    # Convert rows to list of lists, handling binary data
                    rows_list = []
                    for row in rows:
                        row_data = []
                        for value in row:
                            if isinstance(value, bytes):
                                # Convert bytes to hex string representation
                                row_data.append(f"<binary: {len(value)} bytes>")
                            elif isinstance(value, memoryview):
                                # Handle memoryview objects
                                row_data.append(f"<binary: {len(value)} bytes>")
                            else:
                                row_data.append(value)
                        rows_list.append(row_data)
                    
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    return QueryResult(
                        success=True,
                        row_count=len(rows),
                        columns=columns,
                        rows=rows_list,
                        execution_time_ms=execution_time,
                    )
                else:
                    # For INSERT, UPDATE, DELETE, etc.
                    row_count = result.rowcount
                    execution_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    return QueryResult(
                        success=True,
                        row_count=row_count,
                        columns=[],
                        rows=[],
                        execution_time_ms=execution_time,
                    )
        except (SQLAlchemyError, TimeoutError) as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return QueryResult(
                success=False,
                row_count=0,
                columns=[],
                rows=[],
                error=str(e),
                execution_time_ms=execution_time,
            )

    async def get_table_data(
        self,
        table_name: str,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None,
        order_by: Optional[str] = None,
    ) -> QueryResult:
        """Get paginated data from a table.

        Args:
            table_name: Name of the table to query
            page: Page number (1-indexed)
            page_size: Number of rows per page
            search: Optional search term (searches all columns)
            order_by: Optional ORDER BY clause

        Returns:
            QueryResult with table data

        Raises:
            DatabaseError: If query fails
        """
        offset = (page - 1) * page_size
        
        # Build query
        query_parts = [f"SELECT * FROM {table_name}"]
        
        # Add search condition if provided
        if search:
            # This is a simple implementation - in production, you'd want to
            # search specific columns based on schema
            query_parts.append(f"WHERE CAST({table_name} AS TEXT) ILIKE :search")
        
        # Add ordering
        if order_by:
            # Sanitize order_by to prevent SQL injection
            # In production, validate against actual column names
            query_parts.append(f"ORDER BY {order_by}")
        
        query_parts.append(f"LIMIT {page_size} OFFSET {offset}")
        
        query_str = " ".join(query_parts)
        
        try:
            async with self.db_service.get_session() as session:
                if search:
                    result = await session.execute(
                        text(query_str),
                        {"search": f"%{search}%"}
                    )
                else:
                    result = await session.execute(text(query_str))
                
                rows = result.fetchall()
                columns = list(result.keys())
                
                # Convert rows to list, handling binary data
                rows_list = []
                for row in rows:
                    row_data = []
                    for value in row:
                        if isinstance(value, bytes):
                            # Convert bytes to hex string representation
                            row_data.append(f"<binary: {len(value)} bytes>")
                        elif isinstance(value, memoryview):
                            # Handle memoryview objects
                            row_data.append(f"<binary: {len(value)} bytes>")
                        else:
                            row_data.append(value)
                    rows_list.append(row_data)
                
                return QueryResult(
                    success=True,
                    row_count=len(rows),
                    columns=columns,
                    rows=rows_list,
                )
        except Exception as e:
            return QueryResult(
                success=False,
                row_count=0,
                columns=[],
                rows=[],
                error=str(e),
            )

    async def get_database_stats(self) -> DatabaseStats:
        """Get database statistics and information.

        Returns:
            DatabaseStats object with database metrics

        Raises:
            DatabaseError: If stats retrieval fails
        """
        try:
            async with self.db_service.get_session() as session:
                # Get database size
                size_query = text("SELECT pg_database_size(current_database())")
                size_result = await session.execute(size_query)
                database_size = size_result.scalar() or 0
                
                # Get version
                version_query = text("SELECT version()")
                version_result = await session.execute(version_query)
                version = version_result.scalar() or "Unknown"
                
                # Get connection count
                conn_query = text("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
                conn_result = await session.execute(conn_query)
                connection_count = conn_result.scalar() or 0
                
                return DatabaseStats(
                    database_size_bytes=database_size,
                    version=version,
                    connection_count=connection_count,
                )
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve database statistics: {e}")

    async def export_data(self, query: str, format: str = "csv") -> str:
        """Export query results in specified format.

        Args:
            query: SQL query to execute
            format: Export format ('csv' or 'json')

        Returns:
            Exported data as string

        Raises:
            ValidationError: If format is unsupported
            DatabaseError: If export fails
        """
        if format not in ("csv", "json"):
            raise ValidationError(
                "Unsupported export format",
                {"format": format, "supported": ["csv", "json"]},
            )

        try:
            async with self.db_service.get_session() as session:
                result = await session.execute(text(query))
                rows = result.fetchall()
                columns = list(result.keys())
                
                if format == "csv":
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow(columns)
                    writer.writerows(rows)
                    return output.getvalue()
                else:  # json
                    data = [dict(zip(columns, row)) for row in rows]
                    return json.dumps(data, indent=2, default=str)
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to export data: {e}")

