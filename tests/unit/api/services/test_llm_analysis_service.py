"""Unit tests for LLM analysis service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.exceptions import ValidationError
from src.api.services.llm_analysis_service import LLMLogAnalyzer


@pytest.fixture
def mock_ollama_service():
    """Create a mock Ollama service."""
    service = MagicMock()
    service.generate = AsyncMock(return_value="Mocked LLM response")
    return service


@pytest.fixture
def analyzer(mock_ollama_service):
    """Create an LLMLogAnalyzer instance."""
    return LLMLogAnalyzer(mock_ollama_service)


@pytest.fixture
def sample_logs():
    """Sample log entries for testing."""
    return [
        {
            "id": 1,
            "level": "ERROR",
            "message": "Database connection failed",
            "timestamp": "2025-01-01T00:00:00Z",
        },
        {
            "id": 2,
            "level": "ERROR",
            "message": "Retry connection failed",
            "timestamp": "2025-01-01T00:00:01Z",
        },
    ]


class TestLLMLogAnalyzer:
    """Tests for LLMLogAnalyzer class."""

    def test_initialization(self, mock_ollama_service):
        """Test LLMLogAnalyzer initialization."""
        analyzer = LLMLogAnalyzer(mock_ollama_service)
        assert analyzer.ollama_service == mock_ollama_service
        assert analyzer.default_model == "llama2"

    @pytest.mark.asyncio
    async def test_analyze_logs_empty_logs(self, analyzer):
        """Test analyze_logs with empty log list."""
        with pytest.raises(ValidationError, match="No logs provided for analysis"):
            await analyzer.analyze_logs([])

    @pytest.mark.asyncio
    async def test_analyze_logs_invalid_type(self, analyzer, sample_logs):
        """Test analyze_logs with invalid analysis type."""
        with pytest.raises(ValidationError, match="Invalid analysis type"):
            await analyzer.analyze_logs(sample_logs, analysis_type="invalid_type")

    @pytest.mark.asyncio
    async def test_analyze_logs_root_cause(
        self, analyzer, sample_logs, mock_ollama_service
    ):
        """Test root cause analysis."""
        mock_ollama_service.generate.return_value = (
            "# Root Cause Analysis\n\n"
            "Summary: Database connection issues detected.\n\n"
            "## Findings:\n"
            "- Connection timeout after 30s\n"
            "- Network connectivity issue\n\n"
            "## Recommendations:\n"
            "- Check database server status\n"
            "- Verify network configuration\n"
        )

        result = await analyzer.analyze_logs(sample_logs, analysis_type="root_cause")

        assert result["analysis_type"] == "root_cause"
        assert result["logs_analyzed"] == 2
        assert "summary" in result
        assert "findings" in result
        assert "recommendations" in result
        assert len(result["findings"]) > 0
        assert len(result["recommendations"]) > 0
        assert "full_analysis" in result

    @pytest.mark.asyncio
    async def test_analyze_logs_pattern(self, analyzer, sample_logs, mock_ollama_service):
        """Test pattern detection analysis."""
        mock_ollama_service.generate.return_value = (
            "Pattern detected: Repeated connection failures\n"
            "1. First failure at 00:00:00\n"
            "2. Second failure at 00:00:01\n"
        )

        result = await analyzer.analyze_logs(sample_logs, analysis_type="pattern")

        assert result["analysis_type"] == "pattern"
        assert result["logs_analyzed"] == 2
        mock_ollama_service.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_logs_anomaly_without_baseline(self, analyzer, sample_logs):
        """Test anomaly detection without baseline stats."""
        with pytest.raises(
            ValidationError, match="Baseline statistics required for anomaly detection"
        ):
            await analyzer.analyze_logs(sample_logs, analysis_type="anomaly")

    @pytest.mark.asyncio
    async def test_analyze_logs_anomaly_with_baseline(
        self, analyzer, sample_logs, mock_ollama_service
    ):
        """Test anomaly detection with baseline stats."""
        baseline_stats = {"avg_errors_per_hour": 5, "avg_warnings_per_hour": 10}

        mock_ollama_service.generate.return_value = "Anomaly detected: Error rate is 200% above baseline"

        result = await analyzer.analyze_logs(
            sample_logs, analysis_type="anomaly", baseline_stats=baseline_stats
        )

        assert result["analysis_type"] == "anomaly"
        assert result["logs_analyzed"] == 2
        mock_ollama_service.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_logs_correlation(
        self, analyzer, sample_logs, mock_ollama_service
    ):
        """Test event correlation analysis."""
        mock_ollama_service.generate.return_value = "Events correlated: Connection failure led to retry"

        result = await analyzer.analyze_logs(sample_logs, analysis_type="correlation")

        assert result["analysis_type"] == "correlation"
        assert result["logs_analyzed"] == 2

    @pytest.mark.asyncio
    async def test_analyze_logs_summary(self, analyzer, sample_logs, mock_ollama_service):
        """Test error summarization analysis."""
        mock_ollama_service.generate.return_value = "Summary: Two connection failures occurred"

        result = await analyzer.analyze_logs(sample_logs, analysis_type="summary")

        assert result["analysis_type"] == "summary"
        assert result["logs_analyzed"] == 2

    @pytest.mark.asyncio
    async def test_analyze_logs_llm_failure(
        self, analyzer, sample_logs, mock_ollama_service
    ):
        """Test analyze_logs when LLM call fails."""
        mock_ollama_service.generate.side_effect = Exception("LLM service unavailable")

        result = await analyzer.analyze_logs(sample_logs, analysis_type="root_cause")

        assert result["analysis_type"] == "root_cause"
        assert result["logs_analyzed"] == 2
        assert "error" in result
        assert "LLM service unavailable" in result["error"]
        assert result["findings"] == []
        assert result["recommendations"] == []

    @pytest.mark.asyncio
    async def test_find_patterns(self, analyzer, sample_logs, mock_ollama_service):
        """Test find_patterns convenience method."""
        mock_ollama_service.generate.return_value = "Pattern analysis result"

        result = await analyzer.find_patterns(sample_logs)

        assert result["analysis_type"] == "pattern"
        assert result["logs_analyzed"] == 2

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, analyzer, sample_logs, mock_ollama_service):
        """Test detect_anomalies convenience method."""
        baseline = {"avg_errors": 5}
        mock_ollama_service.generate.return_value = "Anomaly detected"

        result = await analyzer.detect_anomalies(sample_logs, baseline)

        assert result["analysis_type"] == "anomaly"
        assert result["logs_analyzed"] == 2

    @pytest.mark.asyncio
    async def test_suggest_root_cause(self, analyzer, sample_logs, mock_ollama_service):
        """Test suggest_root_cause convenience method."""
        mock_ollama_service.generate.return_value = "Root cause: Database timeout"

        result = await analyzer.suggest_root_cause(sample_logs)

        assert result["analysis_type"] == "root_cause"
        assert result["logs_analyzed"] == 2

    @pytest.mark.asyncio
    async def test_correlate_events(self, analyzer, sample_logs, mock_ollama_service):
        """Test correlate_events convenience method."""
        mock_ollama_service.generate.return_value = "Events correlated successfully"

        result = await analyzer.correlate_events(sample_logs)

        assert result["analysis_type"] == "correlation"
        assert result["logs_analyzed"] == 2

    def test_parse_llm_response_with_findings_and_recommendations(self, analyzer):
        """Test parsing LLM response with findings and recommendations."""
        response = """
        Summary line 1
        Summary line 2
        Summary line 3
        
        ## Findings:
        - Finding 1
        - Finding 2
        * Finding 3
        
        ## Recommendations:
        1. Recommendation 1
        2. Recommendation 2
        """

        result = analyzer._parse_llm_response(response, "root_cause", 5)

        assert result["analysis_type"] == "root_cause"
        assert result["logs_analyzed"] == 5
        # Parser may extract findings and patterns - check that both exist
        assert len(result["findings"]) >= 2  # At least recommendations extracted
        assert len(result["recommendations"]) == 2
        assert "Recommendation 1" in result["recommendations"]
        assert "full_analysis" in result

    def test_parse_llm_response_with_patterns(self, analyzer):
        """Test parsing LLM response with patterns."""
        response = """
        Pattern analysis:
        1. Pattern one with description
        2. Pattern two with description
        - Pattern three
        """

        result = analyzer._parse_llm_response(response, "pattern", 3)

        assert len(result["patterns"]) > 0

    def test_extract_list_items_with_numbered_list(self, analyzer):
        """Test extracting items from numbered list."""
        text = """
        ## Findings:
        1. First finding
        2. Second finding
        3. Third finding
        """

        items = analyzer._extract_list_items(text, ["findings"])

        assert len(items) == 3
        assert "First finding" in items
        assert "Second finding" in items
        assert "Third finding" in items

    def test_extract_list_items_with_bullet_list(self, analyzer):
        """Test extracting items from bullet list."""
        text = """
        ## Recommendations:
        - First recommendation
        * Second recommendation
        • Third recommendation
        """

        items = analyzer._extract_list_items(text, ["recommendations"])

        assert len(items) == 3
        assert "First recommendation" in items
        assert "Second recommendation" in items
        assert "Third recommendation" in items

    def test_extract_list_items_with_bold_markers(self, analyzer):
        """Test extracting items with bold markdown."""
        text = """
        ## Issues:
        1. **Critical issue** with database
        2. __Important warning__ about memory
        """

        items = analyzer._extract_list_items(text, ["issues"])

        assert len(items) == 2
        assert "Critical issue with database" in items
        assert "Important warning about memory" in items

    def test_extract_list_items_limit_to_10(self, analyzer):
        """Test that list extraction is limited to 10 items."""
        text = "## Items:\n" + "\n".join([f"- Item {i}" for i in range(20)])

        items = analyzer._extract_list_items(text, ["items"])

        assert len(items) == 10

    def test_extract_list_items_no_section_found(self, analyzer):
        """Test extracting when section is not found."""
        text = "Some random text without the expected section"

        items = analyzer._extract_list_items(text, ["findings"])

        assert items == []

    def test_extract_patterns_from_numbered_list(self, analyzer):
        """Test extracting patterns from numbered list."""
        text = """
        1. Repeated database timeouts every 5 minutes
        2. Memory usage spikes during peak hours
        3. Network latency increases after deployments
        """

        patterns = analyzer._extract_patterns(text)

        assert len(patterns) >= 3
        assert patterns[0]["description"] == "Repeated database timeouts every 5 minutes"
        assert patterns[0]["frequency"] == "unknown"
        assert patterns[0]["severity"] == "unknown"

    def test_extract_patterns_from_bullet_list(self, analyzer):
        """Test extracting patterns from bullet list."""
        text = """
        - Pattern A: High error rate
        * Pattern B: Slow response times
        """

        patterns = analyzer._extract_patterns(text)

        assert len(patterns) >= 2

    def test_extract_patterns_limit_to_5(self, analyzer):
        """Test that pattern extraction is limited to 5."""
        text = "\n".join([f"- Pattern {i}: Description that is long enough" for i in range(10)])

        patterns = analyzer._extract_patterns(text)

        assert len(patterns) == 5

    def test_extract_patterns_filters_short_descriptions(self, analyzer):
        """Test that short descriptions are filtered out."""
        text = """
        1. Short
        2. This is a proper description with enough text
        """

        patterns = analyzer._extract_patterns(text)

        assert len(patterns) == 1
        assert "proper description" in patterns[0]["description"]

