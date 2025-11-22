"""LLM-powered log analysis service.

This module provides LLM-powered analysis capabilities for application logs,
including root cause analysis, pattern detection, and event correlation.
"""

from __future__ import annotations

from typing import Any

from src.api.services.llm_prompts import (
    get_root_cause_analysis_prompt,
    get_pattern_detection_prompt,
    get_anomaly_detection_prompt,
    get_event_correlation_prompt,
    get_error_summarization_prompt,
)
from src.api.services.ollama import OllamaService
from src.api.exceptions import ValidationError


class LLMLogAnalyzer:
    """LLM-powered log analyzer.

    This class uses Large Language Models to analyze logs and provide
    insights, root cause analysis, and pattern detection.
    """

    def __init__(self, ollama_service: OllamaService) -> None:
        """Initialize LLM log analyzer.

        Args:
            ollama_service: Ollama service instance for LLM operations
        """
        self.ollama_service = ollama_service
        self.default_model = "llama2"  # Can be configured

    async def analyze_logs(
        self,
        logs: list[dict[str, Any]],
        analysis_type: str = "root_cause",
        baseline_stats: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze logs using LLM.

        Args:
            logs: List of log entries to analyze
            analysis_type: Type of analysis (root_cause, pattern, anomaly, correlation, summary)
            baseline_stats: Optional baseline statistics for anomaly detection

        Returns:
            Analysis results dictionary

        Raises:
            ValidationError: If analysis_type is invalid or logs are empty
        """
        if not logs:
            raise ValidationError("No logs provided for analysis")

        if analysis_type not in ("root_cause", "pattern", "anomaly", "correlation", "summary"):
            raise ValidationError(f"Invalid analysis type: {analysis_type}")

        # Generate appropriate prompt
        if analysis_type == "root_cause":
            prompt = get_root_cause_analysis_prompt(logs)
        elif analysis_type == "pattern":
            prompt = get_pattern_detection_prompt(logs)
        elif analysis_type == "anomaly":
            if not baseline_stats:
                raise ValidationError("Baseline statistics required for anomaly detection")
            prompt = get_anomaly_detection_prompt(logs, baseline_stats)
        elif analysis_type == "correlation":
            prompt = get_event_correlation_prompt(logs)
        else:  # summary
            prompt = get_error_summarization_prompt(logs)

        # Call LLM
        try:
            response = await self.ollama_service.generate(
                model=self.default_model,
                prompt=prompt,
                system="You are an expert system administrator and software engineer specializing in log analysis and troubleshooting.",
            )

            # Parse response into structured format
            analysis_result = self._parse_llm_response(
                response=response,
                analysis_type=analysis_type,
                logs_analyzed=len(logs),
            )

            return analysis_result

        except Exception as e:
            # Return error but don't fail completely
            return {
                "analysis_type": analysis_type,
                "logs_analyzed": len(logs),
                "summary": f"Analysis failed: {str(e)}",
                "findings": [],
                "recommendations": [],
                "patterns": [],
                "related_logs": [],
                "error": str(e),
            }

    async def find_patterns(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """Identify recurring patterns in logs.

        Args:
            logs: List of log entries

        Returns:
            Pattern analysis results
        """
        return await self.analyze_logs(logs, analysis_type="pattern")

    async def detect_anomalies(
        self,
        logs: list[dict[str, Any]],
        baseline_stats: dict[str, Any],
    ) -> dict[str, Any]:
        """Detect anomalies in logs compared to baseline.

        Args:
            logs: List of log entries
            baseline_stats: Baseline statistics for comparison

        Returns:
            Anomaly detection results
        """
        return await self.analyze_logs(
            logs,
            analysis_type="anomaly",
            baseline_stats=baseline_stats,
        )

    async def suggest_root_cause(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze error chains and suggest root cause.

        Args:
            logs: List of log entries (should include errors)

        Returns:
            Root cause analysis results
        """
        return await self.analyze_logs(logs, analysis_type="root_cause")

    async def correlate_events(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """Link related log events and build event timeline.

        Args:
            logs: List of log entries

        Returns:
            Event correlation results
        """
        return await self.analyze_logs(logs, analysis_type="correlation")

    def _parse_llm_response(
        self,
        response: str,
        analysis_type: str,
        logs_analyzed: int,
    ) -> dict[str, Any]:
        """Parse LLM response into structured format.

        Args:
            response: Raw LLM response text
            analysis_type: Type of analysis performed
            logs_analyzed: Number of logs analyzed

        Returns:
            Structured analysis results
        """
        # Extract sections from response
        findings = self._extract_list_items(response, ["findings", "issues", "problems", "observations"])
        recommendations = self._extract_list_items(response, ["recommendations", "suggestions", "fixes", "actions"])
        patterns = self._extract_patterns(response)

        # Extract summary (first paragraph or first few lines)
        summary_lines = []
        for line in response.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("*"):
                summary_lines.append(line)
                if len(summary_lines) >= 3:
                    break

        summary = " ".join(summary_lines) if summary_lines else response[:500]

        return {
            "analysis_type": analysis_type,
            "logs_analyzed": logs_analyzed,
            "summary": summary,
            "findings": findings,
            "recommendations": recommendations,
            "patterns": patterns,
            "related_logs": [],  # Could be enhanced to extract log IDs from response
            "full_analysis": response,  # Include full LLM response
        }

    def _extract_list_items(self, text: str, section_headers: list[str]) -> list[str]:
        """Extract list items from sections in LLM response.

        Args:
            text: Response text
            section_headers: Possible section header names

        Returns:
            List of extracted items
        """
        items = []
        lines = text.split("\n")
        in_section = False

        for line in lines:
            line_lower = line.lower().strip()

            # Check if we're entering a relevant section
            if any(header in line_lower for header in section_headers):
                in_section = True
                continue

            # Check if we're leaving the section (new header or empty line after items)
            if in_section and (line.startswith("#") or (line_lower.startswith("**") and ":" in line)):
                if items:  # Only stop if we've collected items
                    break

            # Extract list items
            if in_section:
                # Handle numbered lists: "1. Item"
                if line.strip() and (
                    line.strip()[0].isdigit() or
                    line.strip().startswith("-") or
                    line.strip().startswith("*") or
                    line.strip().startswith("•")
                ):
                    # Remove list markers
                    item = line.strip()
                    for marker in ["1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "-", "*", "•"]:
                        if item.startswith(marker):
                            item = item[len(marker):].strip()
                            break

                    if item:
                        # Remove bold markers
                        item = item.replace("**", "").replace("__", "")
                        items.append(item)

        return items[:10]  # Limit to top 10 items

    def _extract_patterns(self, text: str) -> list[dict[str, Any]]:
        """Extract pattern information from LLM response.

        Args:
            text: Response text

        Returns:
            List of pattern dictionaries
        """
        patterns = []

        # Look for pattern-related sections
        lines = text.split("\n")
        current_pattern = None

        for line in lines:
            line = line.strip()

            # Detect pattern descriptions (usually start with numbers or bullets)
            if line and (
                (line[0].isdigit() and ". " in line) or
                line.startswith("-") or
                line.startswith("*")
            ):
                # Extract pattern description
                description = line
                for marker in ["1.", "2.", "3.", "4.", "5.", "- ", "* "]:
                    if description.startswith(marker):
                        description = description[len(marker):].strip()

                if description and len(description) > 10:
                    patterns.append({
                        "description": description,
                        "frequency": "unknown",  # Could be enhanced to extract frequency
                        "severity": "unknown",  # Could be enhanced to extract severity
                    })

        return patterns[:5]  # Limit to top 5 patterns

