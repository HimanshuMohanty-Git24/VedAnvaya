"""Machine and human-readable QA reporting."""

from pathlib import Path

import orjson
from rich.console import Console
from rich.table import Table

from vedagraph.models import QAIssue
from vedagraph.models.enums import QASeverity, QAStatus


def qa_status(issues: list[QAIssue]) -> QAStatus:
    if any(issue.severity == QASeverity.ERROR for issue in issues):
        return QAStatus.FAILED
    if any(issue.severity == QASeverity.WARNING for issue in issues):
        return QAStatus.PASSED_WITH_WARNINGS
    return QAStatus.PASSED


def write_qa_json(path: Path, issues: list[QAIssue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": qa_status(issues),
        "issue_count": len(issues),
        "issues": [issue.model_dump(mode="json", exclude_none=True) for issue in issues],
    }
    path.write_bytes(
        orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )


def print_qa_report(issues: list[QAIssue], console: Console | None = None) -> None:
    output = console or Console()
    output.print(f"QA status: [bold]{qa_status(issues)}[/bold] ({len(issues)} issues)")
    if not issues:
        return
    table = Table("Severity", "Check", "Entity", "Message")
    for issue in issues:
        table.add_row(issue.severity, issue.check_id, issue.entity_id or "-", issue.message)
    output.print(table)
