"""Log management API routes.

This module provides REST API endpoints for querying, searching, and analyzing
application logs.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from src.api.exceptions import DatabaseError, ValidationError
from src.api.models.schemas import (
    LogAnalysisRequest,
    LogAnalysisResponse,
    LogEntry,
    LogListResponse,
    LogStatistics,
)
from src.api.repositories.log_repository import LogRepository
from src.api.services.llm_analysis_service import LLMLogAnalyzer
from src.api.services.log_service import LogService

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


async def get_log_service(request: Request) -> LogService:
    """Dependency injection for log service.

    Args:
        request: FastAPI request object

    Returns:
        Log service instance

    Raises:
        HTTPException: If service container not available
    """
    try:
        container = request.app.state.container
        # Get database session
        async with container.database.get_session() as session:
            repository = LogRepository(session)
            return LogService(repository)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize log service: {e}")


async def get_llm_analyzer(request: Request) -> LLMLogAnalyzer:
    """Dependency injection for LLM log analyzer.

    Args:
        request: FastAPI request object

    Returns:
        LLM log analyzer instance

    Raises:
        HTTPException: If service container not available
    """
    try:
        container = request.app.state.container
        return LLMLogAnalyzer(container.ollama)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize LLM analyzer: {e}")


@router.get("", response_model=LogListResponse)
async def get_logs(
    start_time: str | None = Query(None, description="Start time (ISO format)"),
    end_time: str | None = Query(None, description="End time (ISO format)"),
    level: str | None = Query(None, description="Log level filter"),
    service_filter: str | None = Query(None, alias="service", description="Service name filter"),
    search: str | None = Query(None, description="Search term"),
    limit: int = Query(100, ge=1, le=1000, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    request: Request = None,
) -> LogListResponse:
    """Get logs with optional filters.

    This endpoint retrieves logs with pagination and filtering support.

    Args:
        start_time: Filter logs after this timestamp
        end_time: Filter logs before this timestamp
        level: Filter by log level
        service: Filter by service name
        search: Search term for message content
        limit: Maximum number of results
        offset: Offset for pagination
        request: FastAPI request object

    Returns:
        Paginated list of log entries

    Raises:
        HTTPException: If query fails or validation error occurs
    """
    # Create service instance with database session from container
    container = request.app.state.container

    try:
        async with container.database.get_session() as session:
            repository = LogRepository(session)
            log_service = LogService(repository)

            logs, total = await log_service.get_logs(
                start_time=start_time,
                end_time=end_time,
                level=level,
                service=service_filter,
                search=search,
                limit=limit,
                offset=offset,
            )

            return LogListResponse(
                logs=[LogEntry(**log) for log in logs],
                total=total,
                limit=limit,
                offset=offset,
            )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get("/search", response_model=LogListResponse)
async def search_logs(
    q: str = Query(..., description="Search query term"),
    limit: int = Query(100, ge=1, le=1000, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    request: Request = None,
) -> LogListResponse:
    """Full-text search in log messages.

    This endpoint performs full-text search on log messages using PostgreSQL
    full-text search capabilities.

    Args:
        q: Search query term
        limit: Maximum number of results
        offset: Offset for pagination
        request: FastAPI request object

    Returns:
        Paginated list of matching log entries

    Raises:
        HTTPException: If search fails
    """
    container = request.app.state.container

    try:
        async with container.database.get_session() as session:
            repository = LogRepository(session)
            service = LogService(repository)

            logs, total = await service.search_logs(
                search_term=q,
                limit=limit,
                offset=offset,
            )

            return LogListResponse(
                logs=[LogEntry(**log) for log in logs],
                total=total,
                limit=limit,
                offset=offset,
            )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get("/stats", response_model=LogStatistics)
async def get_log_statistics(
    start_time: str | None = Query(None, description="Start time (ISO format)"),
    end_time: str | None = Query(None, description="End time (ISO format)"),
    request: Request = None,
) -> LogStatistics:
    """Get aggregated log statistics.

    This endpoint returns statistics about logs including counts by level,
    service, and time range.

    Args:
        start_time: Start of time range (default: 24 hours ago)
        end_time: End of time range (default: now)
        request: FastAPI request object

    Returns:
        Log statistics

    Raises:
        HTTPException: If query fails
    """
    container = request.app.state.container

    try:
        async with container.database.get_session() as session:
            repository = LogRepository(session)
            service = LogService(repository)

            stats = await service.get_statistics(
                start_time=start_time,
                end_time=end_time,
            )

            return LogStatistics(**stats)

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get("/correlate", response_model=LogListResponse)
async def get_correlated_logs(
    request_id: str | None = Query(None, description="Request correlation ID"),
    task_id: str | None = Query(None, description="Task correlation ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    request: Request = None,
) -> LogListResponse:
    """Get logs related by correlation IDs.

    This endpoint finds logs that share the same request_id or task_id,
    useful for tracing operations across services.

    Args:
        request_id: Request correlation ID
        task_id: Task correlation ID
        limit: Maximum number of results
        request: FastAPI request object

    Returns:
        List of related log entries

    Raises:
        HTTPException: If query fails or validation error occurs
    """
    container = request.app.state.container

    try:
        async with container.database.get_session() as session:
            repository = LogRepository(session)
            service = LogService(repository)

            logs = await service.get_related_logs(
                request_id=request_id,
                task_id=task_id,
                limit=limit,
            )

            return LogListResponse(
                logs=[LogEntry(**log) for log in logs],
                total=len(logs),
                limit=limit,
                offset=0,
            )

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.post("/analyze", response_model=LogAnalysisResponse)
async def analyze_logs(
    analysis_request: LogAnalysisRequest,
    request: Request = None,
) -> LogAnalysisResponse:
    """Analyze logs using LLM.

    This endpoint uses Large Language Models to analyze logs and provide
    insights, root cause analysis, pattern detection, and recommendations.

    Args:
        analysis_request: Analysis request with log IDs or search criteria
        request: FastAPI request object

    Returns:
        Analysis results with findings and recommendations

    Raises:
        HTTPException: If analysis fails
    """
    container = request.app.state.container

    try:
        async with container.database.get_session() as session:
            repository = LogRepository(session)
            service = LogService(repository)

            # Get logs to analyze
            logs = []

            if analysis_request.log_ids:
                # Get specific logs by ID
                for log_id in analysis_request.log_ids[: analysis_request.max_logs]:
                    log = await service.get_log_by_id(log_id)
                    if log:
                        logs.append(log)

            elif analysis_request.search_criteria:
                # Get logs based on search criteria
                criteria = analysis_request.search_criteria
                result_logs, _ = await service.get_logs(
                    start_time=criteria.start_time,
                    end_time=criteria.end_time,
                    level=criteria.level,
                    service=criteria.service,
                    search=criteria.search,
                    limit=min(criteria.limit, analysis_request.max_logs),
                    offset=criteria.offset,
                )
                logs = result_logs

            if not logs:
                raise ValidationError("No logs found matching criteria")

            # Get baseline statistics for anomaly detection
            baseline_stats = None
            if analysis_request.analysis_type == "anomaly":
                baseline_stats = await service.get_statistics()

            # Analyze logs with LLM
            analyzer = LLMLogAnalyzer(container.ollama)
            analysis_result = await analyzer.analyze_logs(
                logs=logs,
                analysis_type=analysis_request.analysis_type,
                baseline_stats=baseline_stats,
            )

            return LogAnalysisResponse(**analysis_result)

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.get("/{log_id}", response_model=LogEntry)
async def get_log_by_id(
    log_id: int,
    request: Request = None,
) -> LogEntry:
    """Get a single log entry by ID.

    Args:
        log_id: Log entry ID
        request: FastAPI request object

    Returns:
        Log entry

    Raises:
        HTTPException: If log not found or query fails
    """
    container = request.app.state.container

    try:
        async with container.database.get_session() as session:
            repository = LogRepository(session)
            service = LogService(repository)

            log = await service.get_log_by_id(log_id)

            if not log:
                raise HTTPException(status_code=404, detail=f"Log entry {log_id} not found")

            return LogEntry(**log)

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
