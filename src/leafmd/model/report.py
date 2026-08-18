from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from leafmd.model.issues import ConversionIssue, IssueSeverity


@dataclass
class ConversionStats:
    source_documents: int = 0
    generated_files: int = 0
    images_copied: int = 0
    unresolved_links: int = 0
    assets_skipped: int = 0
    images_analyzed: int = 0
    image_replacements: int = 0
    image_analysis_failures: int = 0
    image_analysis_enabled: bool = field(default=False, repr=False, compare=False)

    def to_dict(self) -> dict[str, int]:
        result = {
            "source_documents": self.source_documents,
            "generated_files": self.generated_files,
            "images_copied": self.images_copied,
            "unresolved_links": self.unresolved_links,
            "assets_skipped": self.assets_skipped,
        }
        if self.image_analysis_enabled:
            result.update(
                {
                    "images_analyzed": self.images_analyzed,
                    "image_replacements": self.image_replacements,
                    "image_analysis_failures": self.image_analysis_failures,
                }
            )
        return result


ReportStatus = Literal["ok", "completed_with_warnings", "completed_with_errors", "fatal"]


@dataclass
class ConversionReport:
    status: ReportStatus
    tool_version: str
    source_validation: dict[str, Any] = field(default_factory=lambda: {"epubcheck": None})
    issues: list[ConversionIssue] = field(default_factory=list)
    stats: ConversionStats = field(default_factory=ConversionStats)

    def add(
        self,
        severity: IssueSeverity,
        code: str,
        message: str,
        where: str | None = None,
    ) -> None:
        self.issues.append(ConversionIssue(severity=severity, code=code, message=message, where=where))

    def has_fatal(self) -> bool:
        return any(issue.severity is IssueSeverity.FATAL for issue in self.issues)

    def has_errors(self) -> bool:
        return any(issue.severity is IssueSeverity.ERROR for issue in self.issues)

    def has_warnings(self) -> bool:
        return any(issue.severity is IssueSeverity.WARNING for issue in self.issues)

    def finalize(self) -> None:
        if self.has_fatal():
            self.status = "fatal"
        elif self.has_errors():
            self.status = "completed_with_errors"
        elif self.has_warnings():
            self.status = "completed_with_warnings"
        else:
            self.status = "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "tool_version": self.tool_version,
            "source_validation": self.source_validation,
            "issues": [issue.to_dict() for issue in self.issues],
            "stats": self.stats.to_dict(),
        }
