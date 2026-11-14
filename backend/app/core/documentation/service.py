"""Runs the documentation completeness check for a stored document and
keeps its DocumentationIssue rows up to date."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.documentation.completeness import check_documentation
from app.models.document import Document
from app.models.documentation_issue import DocumentationIssue


def refresh_documentation_issues(db: Session, document: Document) -> None:
    """Re-check the file and replace the document's issues. A file that
    can't be read records no issues (processing reports the read error)."""
    try:
        found = check_documentation(document.file_ref)
    except Exception:  # noqa: BLE001 - unreadable file: nothing to report here
        found = []
    document.documentation_issues.clear()
    for position, issue in enumerate(found):
        document.documentation_issues.append(
            DocumentationIssue(
                position=position,
                kind=issue.kind,
                field=issue.field[:255],
                context=issue.context,
                location=issue.location,
                confidence=issue.confidence,
            )
        )
    document.documentation_checked_at = datetime.now(timezone.utc)


def ensure_documentation_checked(db: Session, document: Document) -> None:
    """Check documents uploaded before this check existed, on first use."""
    if document.documentation_checked_at is None:
        refresh_documentation_issues(db, document)
