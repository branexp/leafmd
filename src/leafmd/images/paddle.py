"""PaddleOCR PP-StructureV3 CLI adapter with no Paddle Python dependency."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from leafmd.errors import UsageError
from leafmd.images import ImageAnalyzerError
from leafmd.model.images import ImageAnalysis, ImageBlock, ImageBlockKind, ImageDecision

_BACKEND = "paddleocr-ppstructurev3"
_VISUAL_LABELS = frozenset({"image", "figure", "chart", "seal", "header_image", "footer_image"})
_IGNORE_LABELS = frozenset({"number", "header", "footer", "aside_text"})
_TEXT_LABELS = frozenset(
    {
        "text",
        "content",
        "paragraph_title",
        "doc_title",
        "abstract",
        "reference",
        "references",
        "footnote",
        "figure_title",
        "figure_caption",
        "table_title",
        "table_caption",
        "figure_table_title",
        "formula_number",
    }
)


class PaddleCliAnalyzer:
    """Run one PP-StructureV3 process for all eligible images in a book."""

    backend = _BACKEND

    def __init__(self, executable: str = "paddleocr") -> None:
        resolved = shutil.which(executable)
        if resolved is None:
            raise UsageError(
                "PaddleOCR is required for --convert-images. Install PP-StructureV3 in a separate environment "
                "and ensure the 'paddleocr' executable is on PATH."
            )
        self.executable = resolved

    def analyze_batch(self, images: Mapping[str, Path]) -> dict[str, ImageAnalysis]:
        if not images:
            return {}
        with TemporaryDirectory(prefix="leafmd-paddle-") as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            result_paths: dict[str, Path] = {}
            for index, (source_href, source_path) in enumerate(sorted(images.items()), start=1):
                suffix = source_path.suffix.lower() or ".png"
                staged = input_dir / f"{index:05d}-{source_path.stem}{suffix}"
                shutil.copyfile(source_path, staged)
                result_paths[source_href] = output_dir / f"{staged.stem}_res.json"

            command = [
                self.executable,
                "pp_structurev3",
                "-i",
                str(input_dir),
                "--save_path",
                str(output_dir),
                "--use_doc_orientation_classify",
                "False",
                "--use_doc_unwarping",
                "False",
                "--use_textline_orientation",
                "False",
                "--use_table_recognition",
                "True",
                "--use_formula_recognition",
                "True",
                "--use_chart_recognition",
                "False",
            ]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "unknown PaddleOCR failure").strip()
                raise ImageAnalyzerError(
                    f"PP-StructureV3 failed with exit code {completed.returncode}: {detail[-1200:]}"
                )

            results: dict[str, ImageAnalysis] = {}
            for source_href, result_path in result_paths.items():
                if not result_path.is_file():
                    continue
                try:
                    payload = json.loads(result_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise ImageAnalyzerError(f"Invalid PP-StructureV3 JSON for {source_href}: {exc}") from exc
                if not isinstance(payload, dict):
                    raise ImageAnalyzerError(f"Invalid PP-StructureV3 result object for {source_href}")
                results[source_href] = parse_ppstructure_result(source_href, payload)
            return results


def parse_ppstructure_result(source_href: str, payload: dict[str, Any]) -> ImageAnalysis:
    """Normalize one saved PP-StructureV3 JSON result into leafmd's small IR."""

    raw_result = payload.get("res")
    result: dict[str, Any] = raw_result if isinstance(raw_result, dict) else payload
    parsing = result.get("parsing_res_list")
    if not isinstance(parsing, list):
        return ImageAnalysis(source_href, ImageDecision.PRESERVE, (), (), "missing-parsing-results", _BACKEND)

    labels = tuple(
        label for item in parsing if isinstance(item, dict) and (label := _normalize_label(item.get("block_label")))
    )
    label_set = set(labels)
    if label_set & _VISUAL_LABELS:
        return ImageAnalysis(source_href, ImageDecision.PRESERVE, (), labels, "visual-content-present", _BACKEND)

    formula_results = result.get("formula_res_list")
    formula_rows = (
        [item for item in formula_results if isinstance(item, dict)] if isinstance(formula_results, list) else []
    )
    formula_by_region = {
        str(item.get("formula_region_id")): str(item.get("rec_formula") or "").strip()
        for item in formula_rows
        if item.get("formula_region_id") is not None and str(item.get("rec_formula") or "").strip()
    }
    formula_fallback = [str(item.get("rec_formula") or "").strip() for item in formula_rows]
    formula_fallback = [item for item in formula_fallback if item]
    formula_index = 0

    table_results = result.get("table_res_list")
    table_rows = [item for item in table_results if isinstance(item, dict)] if isinstance(table_results, list) else []
    table_index = 0

    blocks: list[ImageBlock] = []
    unknown: set[str] = set()
    for item in parsing:
        if not isinstance(item, dict):
            continue
        label = _normalize_label(item.get("block_label"))
        if not label:
            unknown.add("missing-label")
            continue
        if label in _IGNORE_LABELS:
            continue
        content = str(item.get("block_content") or "").strip()
        if label in _TEXT_LABELS:
            if content:
                blocks.append(ImageBlock(ImageBlockKind.TEXT, content, label))
            continue
        if label == "table":
            table_html = ""
            if table_index < len(table_rows):
                table_html = str(table_rows[table_index].get("pred_html") or "").strip()
                table_index += 1
            if not table_html and content.lstrip().lower().startswith("<table"):
                table_html = content
            if not table_html:
                unknown.add("table-without-html")
            else:
                blocks.append(ImageBlock(ImageBlockKind.TABLE, table_html, label))
            continue
        if label == "formula":
            block_id = item.get("block_id")
            fallback = (
                formula_fallback[formula_index] if block_id is None and formula_index < len(formula_fallback) else ""
            )
            formula_index += 1
            formula = formula_by_region.get(str(block_id), "") or fallback or content
            formula = _strip_math_delimiters(formula)
            if formula:
                blocks.append(ImageBlock(ImageBlockKind.FORMULA, formula, label))
            else:
                unknown.add("formula-without-content")
            continue
        unknown.add(label)

    if unknown:
        reason = "unsupported-labels:" + ",".join(sorted(unknown))
        return ImageAnalysis(source_href, ImageDecision.PRESERVE, (), labels, reason, _BACKEND)
    if not blocks:
        return ImageAnalysis(source_href, ImageDecision.PRESERVE, (), labels, "no-convertible-content", _BACKEND)
    return ImageAnalysis(source_href, ImageDecision.REPLACE, tuple(blocks), labels, "markdown-representable", _BACKEND)


def _normalize_label(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _strip_math_delimiters(value: str) -> str:
    formula = value.strip()
    pairs = (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$"))
    for left, right in pairs:
        if formula.startswith(left) and formula.endswith(right) and len(formula) > len(left) + len(right):
            return formula[len(left) : -len(right)].strip()
    return formula
