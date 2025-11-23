from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.api.exceptions import ValidationError
from src.api.services.log_service import LogService


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_logs = AsyncMock(return_value=[{"id": 1}])
    repo.search_logs = AsyncMock(return_value=[{"id": 2}])
    repo.get_log_statistics = AsyncMock(return_value={"count": 3})
    repo.get_related_logs = AsyncMock(return_value=[{"id": 4}])
    repo.get_log_by_id = AsyncMock(return_value={"id": 5})
    repo.cleanup_old_logs = AsyncMock(return_value=10)
    return repo


@pytest.fixture
def log_service(mock_repo):
    return LogService(mock_repo)


@pytest.mark.asyncio
async def test_get_logs_happy(log_service):
    logs, total = await log_service.get_logs(level="info", limit=10, offset=0)
    assert isinstance(logs, list)
    assert total >= 1


@pytest.mark.asyncio
@pytest.mark.parametrize("level", ["fakE", ""])
async def test_get_logs_invalid_level(log_service, level):
    if level:
        with pytest.raises(ValidationError, match="Invalid log level"):
            await log_service.get_logs(level=level)
    else:
        # Should fall through
        logs, total = await log_service.get_logs(level=level)
        assert isinstance(logs, list)


@pytest.mark.asyncio
async def test_get_logs_invalid_limit_offset(log_service):
    for limit in [-1, 0, 1001]:
        with pytest.raises(ValidationError, match="Limit must be between"):
            await log_service.get_logs(limit=limit)
    for offset in [-10]:
        with pytest.raises(ValidationError, match="Offset must be non-negative"):
            await log_service.get_logs(offset=offset)


@pytest.mark.asyncio
async def test_search_logs_happy(log_service):
    logs, total = await log_service.search_logs(search_term="bug", limit=10)
    assert isinstance(logs, list)
    assert total >= 1


@pytest.mark.asyncio
async def test_search_logs_empty_term(log_service):
    for term in [None, "", "   "]:
        with pytest.raises(ValidationError, match="Search term cannot be empty"):
            await log_service.search_logs(search_term=term)


@pytest.mark.asyncio
async def test_search_logs_invalid_limit_offset(log_service):
    for limit in [-1, 0, 1001]:
        with pytest.raises(ValidationError, match="Limit must be between"):
            await log_service.search_logs(search_term="x", limit=limit)
    for offset in [-100]:
        with pytest.raises(ValidationError, match="Offset must be non-negative"):
            await log_service.search_logs(search_term="x", offset=offset)


@pytest.mark.asyncio
async def test_search_logs_strip_term(log_service):
    logs, total = await log_service.search_logs(search_term="  bug  ")
    assert isinstance(logs, list)


@pytest.mark.asyncio
async def test_get_statistics_happy(log_service):
    stats = await log_service.get_statistics(start_time=None, end_time=None)
    assert "count" in stats


@pytest.mark.asyncio
async def test_get_statistics_invalid_timestamp(log_service):
    with pytest.raises(ValidationError, match="Invalid timestamp format"):
        await log_service.get_statistics(start_time="not-a-date")


@pytest.mark.asyncio
async def test_get_related_logs_happy(log_service):
    uuid = str(uuid4())
    logs = await log_service.get_related_logs(request_id=uuid)
    assert isinstance(logs, list)


@pytest.mark.asyncio
async def test_get_related_logs_missing_ids(log_service):
    with pytest.raises(ValidationError, match="Must provide either request_id or task_id"):
        await log_service.get_related_logs()


@pytest.mark.asyncio
async def test_get_related_logs_parse_uuid(log_service):
    # bad UUID string
    with pytest.raises(ValidationError, match="Invalid UUID format"):
        await log_service.get_related_logs(request_id="bad-uuid")


@pytest.mark.asyncio
async def test_get_related_logs_invalid_limit(log_service):
    for limit in [0, -1, 1001]:
        with pytest.raises(ValidationError, match="Limit must be between"):
            await log_service.get_related_logs(request_id=str(uuid4()), limit=limit)


@pytest.mark.asyncio
async def test_get_log_by_id_happy(log_service):
    result = await log_service.get_log_by_id(5)
    assert result["id"] == 5


@pytest.mark.asyncio
async def test_get_log_by_id_invalid(log_service):
    with pytest.raises(ValidationError, match="Log ID must be positive"):
        await log_service.get_log_by_id(0)
    with pytest.raises(ValidationError, match="Log ID must be positive"):
        await log_service.get_log_by_id(-10)


@pytest.mark.asyncio
async def test_cleanup_old_logs_happy(log_service):
    result = await log_service.cleanup_old_logs(30)
    assert isinstance(result, int)


@pytest.mark.asyncio
async def test_cleanup_old_logs_invalid(log_service):
    for days in [0, -5]:
        with pytest.raises(ValidationError, match="Retention days must be positive"):
            await log_service.cleanup_old_logs(days)


def test_parse_timestamp_iso_and_date(log_service):
    # Valid ISO and date formats
    dt1 = log_service._parse_timestamp("2024-02-03T09:08:07Z")
    assert isinstance(dt1, datetime)
    dt2 = log_service._parse_timestamp("2024-02-03")
    assert isinstance(dt2, datetime)


def test_parse_timestamp_invalid(log_service):
    with pytest.raises(ValidationError, match="Invalid timestamp format"):
        log_service._parse_timestamp("bad-timestamp")
    with pytest.raises(ValidationError, match="Invalid timestamp format"):
        log_service._parse_timestamp("")


def test_parse_uuid_valid_and_invalid(log_service):
    u = str(uuid4())
    parsed = log_service._parse_uuid(u)
    assert str(parsed) == u
    with pytest.raises(ValidationError, match="Invalid UUID format"):
        log_service._parse_uuid("not-a-uuid")
