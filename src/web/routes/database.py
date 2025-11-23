"""Database management routes for web interface.

This module provides routes for the database management interface,
including table browsing, query execution, and data export.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from src.api.exceptions import DatabaseError, ValidationError
from src.api.repositories.query_history_repository import QueryHistory, QueryHistoryRepository
from src.api.services.database import DatabaseService
from src.api.services.db_management import DatabaseManagementService

router = APIRouter(prefix="", tags=["database"])

# Configure templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


class QueryRequest(BaseModel):
    """Request model for query execution.

    Attributes:
        sql: SQL query to execute
        confirmed: Whether destructive operations are confirmed
    """

    sql: str
    confirmed: bool = False


def get_db_service(request: Request) -> DatabaseService:
    """Get or create database service from request state.

    Args:
        request: The incoming HTTP request

    Returns:
        DatabaseService instance
    """
    # Check if service exists in app state
    if hasattr(request.app.state, "db_service"):
        return request.app.state.db_service

    # Create new service from environment
    postgres_dsn = os.environ.get("POSTGRES_DSN")
    if not postgres_dsn:
        raise HTTPException(status_code=500, detail="Database connection not configured")

    db_service = DatabaseService(postgres_dsn)
    request.app.state.db_service = db_service
    return db_service


def get_db_management_service(request: Request) -> DatabaseManagementService:
    """Get or create database management service from request state.

    Args:
        request: The incoming HTTP request

    Returns:
        DatabaseManagementService instance
    """
    # Check if service exists in app state
    if hasattr(request.app.state, "db_management_service"):
        return request.app.state.db_management_service

    # Create new service
    db_service = get_db_service(request)
    db_mgmt_service = DatabaseManagementService(db_service)
    request.app.state.db_management_service = db_mgmt_service
    return db_mgmt_service


def get_query_history_repo(request: Request) -> QueryHistoryRepository:
    """Get or create query history repository from request state.

    Args:
        request: The incoming HTTP request

    Returns:
        QueryHistoryRepository instance

    Note:
        This creates a repository without a session. The repository
        will need to obtain a session for each operation.
    """
    # Check if repo exists in app state
    if hasattr(request.app.state, "query_history_repo"):
        return request.app.state.query_history_repo

    # For now, return None - we'll handle session creation in routes
    return None


@router.get("/database", response_class=HTMLResponse)
async def database_page(request: Request) -> HTMLResponse:
    """Render the database management page.

    This endpoint serves the main database management interface with
    tabs for tables, query editor, statistics, and history.

    Args:
        request: The incoming HTTP request

    Returns:
        HTMLResponse with the rendered database management page
    """
    context = {
        "request": request,
        "title": "Database Management",
        "version": "1.5.0",
    }

    return templates.TemplateResponse("database.html", context)


@router.get("/database/tables")
async def get_tables(request: Request) -> list[dict[str, Any]]:
    """Get list of all database tables.

    Args:
        request: The incoming HTTP request

    Returns:
        List of table information dictionaries

    Raises:
        HTTPException: If table retrieval fails
    """
    try:
        service = get_db_management_service(request)
        tables = await service.get_all_tables()

        return [
            {
                "schema_name": table.schema_name,
                "table_name": table.table_name,
                "row_count": table.row_count,
                "size_bytes": table.size_bytes,
            }
            for table in tables
        ]
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/database/table/{table_name}")
async def get_table_schema(request: Request, table_name: str) -> dict[str, Any]:
    """Get schema information for a specific table.

    Args:
        request: The incoming HTTP request
        table_name: Name of the table

    Returns:
        Dictionary with table schema information

    Raises:
        HTTPException: If schema retrieval fails
    """
    try:
        service = get_db_management_service(request)
        schema = await service.get_table_schema(table_name)

        return {
            "table_name": schema.table_name,
            "columns": schema.columns,
        }
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/database/table/{table_name}/data")
async def get_table_data(
    request: Request,
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    search: Optional[str] = Query(None),
    order_by: Optional[str] = Query(None),
) -> dict[str, Any]:
    """Get paginated data from a table.

    Args:
        request: The incoming HTTP request
        table_name: Name of the table
        page: Page number (1-indexed)
        page_size: Number of rows per page
        search: Optional search term
        order_by: Optional ORDER BY clause

    Returns:
        Dictionary with query results

    Raises:
        HTTPException: If data retrieval fails
    """
    try:
        service = get_db_management_service(request)
        result = await service.get_table_data(
            table_name=table_name,
            page=page,
            page_size=page_size,
            search=search,
            order_by=order_by,
        )

        return {
            "success": result.success,
            "row_count": result.row_count,
            "columns": result.columns,
            "rows": result.rows,
            "error": result.error,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/database/query")
async def execute_query(request: Request, query_request: QueryRequest) -> dict[str, Any]:
    """Execute SQL query with safety checks.

    Args:
        request: The incoming HTTP request
        query_request: Query request with SQL and confirmation flag

    Returns:
        Dictionary with query execution results

    Raises:
        HTTPException: If query execution fails or validation error
    """
    try:
        service = get_db_management_service(request)
        result = await service.execute_query(
            sql=query_request.sql,
            confirmed=query_request.confirmed,
        )

        # Save to query history
        try:
            db_service = get_db_service(request)
            async with db_service.get_session() as session:
                repo = QueryHistoryRepository(session)
                history = QueryHistory(
                    id=None,
                    query_text=query_request.sql,
                    executed_at=datetime.now(),
                    execution_time_ms=result.execution_time_ms,
                    status="success" if result.success else "error",
                    row_count=result.row_count if result.success else None,
                    error_message=result.error,
                )
                await repo.create(history)
        except Exception:
            # Log but don't fail the query if history save fails
            pass

        return {
            "success": result.success,
            "row_count": result.row_count,
            "columns": result.columns,
            "rows": result.rows,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
        }
    except ValidationError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/database/stats")
async def get_database_stats(request: Request) -> dict[str, Any]:
    """Get database statistics and information.

    Args:
        request: The incoming HTTP request

    Returns:
        Dictionary with database statistics

    Raises:
        HTTPException: If stats retrieval fails
    """
    try:
        service = get_db_management_service(request)
        stats = await service.get_database_stats()

        return {
            "database_size_bytes": stats.database_size_bytes,
            "version": stats.version,
            "connection_count": stats.connection_count,
        }
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/database/export")
async def export_data(
    request: Request,
    query: str = Query(..., description="SQL query to export"),
    format: str = Query("csv", description="Export format (csv or json)"),
) -> Response:
    """Export query results in specified format.

    Args:
        request: The incoming HTTP request
        query: SQL query to execute
        format: Export format ('csv' or 'json')

    Returns:
        Response with exported data

    Raises:
        HTTPException: If export fails or validation error
    """
    try:
        service = get_db_management_service(request)
        content = await service.export_data(query=query, format=format)

        # Set appropriate content type and filename
        if format == "csv":
            media_type = "text/csv"
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:  # json
            media_type = "application/json"
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        }

        return Response(
            content=content,
            media_type=media_type,
            headers=headers,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/database/history")
async def get_query_history(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
) -> list[dict[str, Any]]:
    """Get query execution history.

    Args:
        request: The incoming HTTP request
        limit: Maximum number of records to return
        search: Optional search term for filtering queries

    Returns:
        List of query history records

    Raises:
        HTTPException: If history retrieval fails
    """
    try:
        db_service = get_db_service(request)
        async with db_service.get_session() as session:
            repo = QueryHistoryRepository(session)

            if search:
                history = await repo.search_queries(search_term=search, limit=limit)
            else:
                history = await repo.get_recent(limit=limit)

            return [
                {
                    "id": h.id,
                    "query_text": h.query_text,
                    "executed_at": h.executed_at.isoformat() if h.executed_at else None,
                    "execution_time_ms": h.execution_time_ms,
                    "status": h.status,
                    "row_count": h.row_count,
                    "error_message": h.error_message,
                }
                for h in history
            ]
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

