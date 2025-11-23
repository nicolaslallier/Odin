from typing import Any

import pytest

from src.api.services import llm_prompts


@pytest.mark.unit
class TestLLMPrompts:
    def test_get_root_cause_analysis_prompt_basic(self) -> None:
        logs = [
            {
                "id": 1,
                "timestamp": "2025-01-01T00:00:00Z",
                "level": "ERROR",
                "service": "api",
                "message": "error occurred",
            }
        ]
        prompt = llm_prompts.get_root_cause_analysis_prompt(logs)
        assert "root cause analysis" in prompt.lower()
        assert str(logs[0]["id"]) in prompt

    def test_get_pattern_detection_prompt_basic(self) -> None:
        logs = [
            {
                "id": 2,
                "timestamp": "2025-01-01T00:01:00Z",
                "level": "INFO",
                "service": "worker",
                "message": "task done",
            }
        ]
        prompt = llm_prompts.get_pattern_detection_prompt(logs)
        assert "patterns and recurring issues" in prompt
        assert "2" in prompt

    def test_get_anomaly_detection_prompt_basic(self) -> None:
        logs = [
            {
                "id": 3,
                "timestamp": "2025-01-01T00:00:02Z",
                "level": "WARNING",
                "service": "web",
                "message": "spike detected",
            }
        ]
        baseline_stats = {
            "total_logs": 100,
            "by_level": {"INFO": 90, "WARNING": 10},
            "by_service": {"web": {"WARNING": {"count": 10}}},
        }
        prompt = llm_prompts.get_anomaly_detection_prompt(logs, baseline_stats)
        assert "analyzing application logs to detect anomalies" in prompt
        assert "Total logs: 100" in prompt
        assert "spike detected" in prompt

    def test_get_event_correlation_prompt_basic(self) -> None:
        logs = [
            {
                "id": 4,
                "timestamp": "2025-01-02T01:00:00Z",
                "level": "INFO",
                "service": "db",
                "message": "connected",
                "request_id": "abc",
            },
            {
                "id": 5,
                "timestamp": "2025-01-02T01:00:01Z",
                "level": "ERROR",
                "service": "db",
                "message": "disconnect",
                "task_id": "123",
            },
        ]
        prompt = llm_prompts.get_event_correlation_prompt(logs)
        assert "correlate related events" in prompt
        assert "abc" in prompt or "123" in prompt

    def test_get_error_summarization_prompt_basic(self) -> None:
        logs = [
            {
                "id": 6,
                "timestamp": "2025-01-02T02:00:00Z",
                "level": "ERROR",
                "service": "auth",
                "message": "invalid password",
            }
        ]
        prompt = llm_prompts.get_error_summarization_prompt(logs)
        assert "summarizing errors from application logs" in prompt
        assert "invalid password" in prompt
        assert "6" in prompt

    @pytest.mark.parametrize(
        "logs,expected",
        [
            ([], "(No logs provided)"),
            (
                [{"id": 8, "timestamp": "now", "level": "INFO", "service": "s1", "message": "msg"}],
                "[8] now | INFO | s1 | msg",
            ),
        ],
    )
    def test_format_logs_for_prompt_empty_and_one(
        self, logs: list[dict[str, Any]], expected: str
    ) -> None:
        result = llm_prompts._format_logs_for_prompt(logs)
        assert expected in result

    def test_format_logs_for_prompt_max_logs(self) -> None:
        logs = [
            {
                "id": i,
                "timestamp": f"t-{i}",
                "level": "INFO",
                "service": "srv",
                "message": f"msg{i}",
            }
            for i in range(100)
        ]
        result = llm_prompts._format_logs_for_prompt(logs, max_logs=10)
        assert result.count("[0]") == 1
        assert result.count("[9]") == 1
        assert "[10]" not in result

    def test_format_logs_for_prompt_all_optional_fields(self) -> None:
        logs = [
            {
                "id": 99,
                "timestamp": "now",
                "level": "DEBUG",
                "service": "x",
                "message": "hello",
                "request_id": "r1",
                "task_id": "t1",
                "exception": "long stacktrace" * 20,
            }
        ]
        result = llm_prompts._format_logs_for_prompt(logs)
        assert "request_id=r1" in result
        assert "task_id=t1" in result
        assert "Exception: long stack" in result
        # Exception is truncated
        assert result.count("...")

    @pytest.mark.parametrize(
        "stats,expected_lines",
        [
            ({}, "(No statistics available)"),
            ({"total_logs": 5}, "Total logs: 5"),
            ({"by_level": {"INFO": 3, "ERROR": 2}}, "Logs by level:"),
            (
                {"by_service": {"svc": {"INFO": {"count": 2}, "ERROR": {"count": 5}}}},
                "Logs by service:",
            ),
        ],
    )
    def test_format_stats_branches(self, stats: dict[str, Any], expected_lines: str) -> None:
        result = llm_prompts._format_stats(stats)
        assert expected_lines in result
        if not stats:
            assert result == "(No statistics available)"

    def test_format_stats_multiple_services(self) -> None:
        stats = {
            "by_service": {
                "svc1": {"INFO": {"count": 1}},
                "svc2": {"INFO": {"count": 2}, "ERROR": {"count": 1}},
            }
        }
        result = llm_prompts._format_stats(stats)
        assert "svc1:" in result
        assert "svc2:" in result
        assert "logs" in result
