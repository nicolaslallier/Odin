"""LLM prompts for log analysis.

This module contains prompt templates for various types of log analysis
using Large Language Models.
"""

from __future__ import annotations

from typing import Any


def get_root_cause_analysis_prompt(logs: list[dict[str, Any]]) -> str:
    """Generate prompt for root cause analysis.

    Args:
        logs: List of log entries to analyze

    Returns:
        Formatted prompt string
    """
    log_text = _format_logs_for_prompt(logs)

    return f"""You are an expert system administrator and software engineer analyzing application logs to identify root causes of errors and issues.

Given the following log entries, perform a root cause analysis:

{log_text}

Please provide:
1. **Summary**: A brief overview of what happened
2. **Root Cause**: The underlying cause of the issue(s)
3. **Error Chain**: How the error propagated through the system
4. **Affected Services**: Which services were impacted
5. **Recommendations**: Specific steps to resolve and prevent recurrence

Focus on ERROR and CRITICAL level logs, but consider INFO and WARNING logs for context.
"""


def get_pattern_detection_prompt(logs: list[dict[str, Any]]) -> str:
    """Generate prompt for pattern detection.

    Args:
        logs: List of log entries to analyze

    Returns:
        Formatted prompt string
    """
    log_text = _format_logs_for_prompt(logs)

    return f"""You are an expert system administrator analyzing application logs to identify patterns and recurring issues.

Given the following log entries, identify patterns:

{log_text}

Please provide:
1. **Recurring Patterns**: What messages or errors repeat frequently?
2. **Temporal Patterns**: Are there time-based patterns (e.g., hourly spikes)?
3. **Service Patterns**: Do certain services have characteristic log patterns?
4. **Correlation Patterns**: What events tend to occur together?
5. **Anomalies**: What stands out as unusual or unexpected?

Be specific and cite log IDs when referencing patterns.
"""


def get_anomaly_detection_prompt(logs: list[dict[str, Any]], baseline_stats: dict[str, Any]) -> str:
    """Generate prompt for anomaly detection.

    Args:
        logs: List of log entries to analyze
        baseline_stats: Baseline statistics for comparison

    Returns:
        Formatted prompt string
    """
    log_text = _format_logs_for_prompt(logs)
    stats_text = _format_stats(baseline_stats)

    return f"""You are an expert system administrator analyzing application logs to detect anomalies.

Baseline statistics for comparison:
{stats_text}

Current log entries:
{log_text}

Please provide:
1. **Anomalies Detected**: What is abnormal compared to baseline?
2. **Severity**: How severe are the anomalies (High/Medium/Low)?
3. **Potential Impact**: What could be the consequences?
4. **Similar Patterns**: Have similar anomalies occurred before?
5. **Investigation Steps**: What should be checked next?

Consider frequency, timing, error rates, and unusual message patterns.
"""


def get_event_correlation_prompt(logs: list[dict[str, Any]]) -> str:
    """Generate prompt for event correlation.

    Args:
        logs: List of log entries to analyze

    Returns:
        Formatted prompt string
    """
    log_text = _format_logs_for_prompt(logs)

    return f"""You are an expert system administrator analyzing application logs to correlate related events.

Given the following log entries (ordered by timestamp):

{log_text}

Please provide:
1. **Event Chains**: Sequences of related events (use request_id/task_id when available)
2. **Causal Relationships**: Which events triggered other events?
3. **Timeline**: A timeline of key events
4. **Cross-Service Interactions**: How services interacted during this period
5. **Missing Events**: Are there expected events that didn't occur?

Focus on understanding the flow of operations across services.
"""


def get_error_summarization_prompt(logs: list[dict[str, Any]]) -> str:
    """Generate prompt for error summarization.

    Args:
        logs: List of error log entries

    Returns:
        Formatted prompt string
    """
    log_text = _format_logs_for_prompt(logs)

    return f"""You are an expert system administrator summarizing errors from application logs.

Given the following error and critical log entries:

{log_text}

Please provide:
1. **Error Summary**: Group similar errors together
2. **Error Counts**: How many times each error type occurred
3. **Most Critical**: Which errors require immediate attention?
4. **Services Affected**: Which services had errors?
5. **Quick Fixes**: Any obvious quick fixes or workarounds?

Be concise but specific. Group related errors together.
"""


def _format_logs_for_prompt(logs: list[dict[str, Any]], max_logs: int = 50) -> str:
    """Format logs for inclusion in prompt.

    Args:
        logs: List of log entries
        max_logs: Maximum number of logs to include

    Returns:
        Formatted log text
    """
    if not logs:
        return "(No logs provided)"

    # Limit number of logs
    logs = logs[:max_logs]

    formatted_lines = []
    for log in logs:
        # Basic log line
        line = f"[{log.get('id')}] {log.get('timestamp')} | {log.get('level')} | {log.get('service')} | {log.get('message')}"

        # Add correlation IDs if present
        if log.get('request_id'):
            line += f" | request_id={log['request_id']}"
        if log.get('task_id'):
            line += f" | task_id={log['task_id']}"

        # Add exception if present
        if log.get('exception'):
            line += f"\n  Exception: {log['exception'][:200]}..."  # Truncate long exceptions

        formatted_lines.append(line)

    return "\n".join(formatted_lines)


def _format_stats(stats: dict[str, Any]) -> str:
    """Format statistics for inclusion in prompt.

    Args:
        stats: Statistics dictionary

    Returns:
        Formatted statistics text
    """
    lines = []

    if "total_logs" in stats:
        lines.append(f"Total logs: {stats['total_logs']}")

    if "by_level" in stats:
        lines.append("\nLogs by level:")
        for level, count in stats["by_level"].items():
            lines.append(f"  {level}: {count}")

    if "by_service" in stats:
        lines.append("\nLogs by service:")
        for service, data in stats["by_service"].items():
            total = sum(level_data.get("count", 0) for level_data in data.values())
            lines.append(f"  {service}: {total} logs")

    return "\n".join(lines) if lines else "(No statistics available)"

