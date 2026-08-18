import subprocess
from pathlib import Path

from leafmd.images.paddle import parse_ppstructure_result
from leafmd.model.images import ImageBlockKind, ImageDecision


def test_text_only_image_is_replaceable() -> None:
    result = parse_ppstructure_result(
        "EPUB/images/scan.png",
        {"parsing_res_list": [{"block_id": 1, "block_label": "text", "block_content": "Recovered text"}]},
    )
    assert result.decision is ImageDecision.REPLACE
    assert result.blocks[0].kind is ImageBlockKind.TEXT
    assert result.blocks[0].content == "Recovered text"


def test_visual_content_preserves_original() -> None:
    result = parse_ppstructure_result(
        "EPUB/images/diagram.png",
        {
            "parsing_res_list": [
                {"block_id": 1, "block_label": "image", "block_content": ""},
                {"block_id": 2, "block_label": "text", "block_content": "label"},
            ]
        },
    )
    assert result.decision is ImageDecision.PRESERVE
    assert result.reason == "visual-content-present"


def test_formula_uses_formula_result() -> None:
    result = parse_ppstructure_result(
        "EPUB/images/equation.png",
        {
            "parsing_res_list": [{"block_id": 7, "block_label": "formula", "block_content": ""}],
            "formula_res_list": [{"formula_region_id": 7, "rec_formula": "$$x^2+y^2=z^2$$"}],
        },
    )
    assert result.decision is ImageDecision.REPLACE
    assert result.blocks == (result.blocks[0],)
    assert result.blocks[0].kind is ImageBlockKind.FORMULA
    assert result.blocks[0].content == "x^2+y^2=z^2"


def test_table_uses_pred_html() -> None:
    result = parse_ppstructure_result(
        "EPUB/images/table.png",
        {
            "parsing_res_list": [{"block_id": 3, "block_label": "table", "block_content": ""}],
            "table_res_list": [{"pred_html": "<table><tr><th>A</th></tr><tr><td>1</td></tr></table>"}],
        },
    )
    assert result.decision is ImageDecision.REPLACE
    assert result.blocks[0].kind is ImageBlockKind.TABLE
    assert result.blocks[0].content.startswith("<table>")


def test_unknown_layout_label_is_preserved() -> None:
    result = parse_ppstructure_result(
        "EPUB/images/unknown.png",
        {"parsing_res_list": [{"block_id": 1, "block_label": "algorithm", "block_content": "x"}]},
    )
    assert result.decision is ImageDecision.PRESERVE
    assert result.reason == "unsupported-labels:algorithm"


def test_cli_analyzer_uses_external_batch_command(monkeypatch, tmp_path: Path) -> None:
    image = tmp_path / "scan.png"
    image.write_bytes(b"raster")
    seen: dict[str, object] = {}

    def fake_which(executable: str) -> str:
        seen["executable"] = executable
        return "/opt/paddle/bin/paddleocr"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["command"] = command
        assert kwargs == {"capture_output": True, "text": True, "check": False}
        input_dir = Path(command[command.index("-i") + 1])
        output_dir = Path(command[command.index("--save_path") + 1])
        staged = next(input_dir.iterdir())
        (output_dir / f"{staged.stem}_res.json").write_text(
            '{"res": {"parsing_res_list": [{"block_label": "text", "block_content": "OCR"}]}}',
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("leafmd.images.paddle.shutil.which", fake_which)
    monkeypatch.setattr("leafmd.images.paddle.subprocess.run", fake_run)

    from leafmd.images.paddle import PaddleCliAnalyzer

    analyzer = PaddleCliAnalyzer()
    results = analyzer.analyze_batch({"EPUB/images/scan.png": image})

    assert seen["executable"] == "paddleocr"
    command = seen["command"]
    assert isinstance(command, list)
    assert command[:2] == ["/opt/paddle/bin/paddleocr", "pp_structurev3"]
    assert results["EPUB/images/scan.png"].decision is ImageDecision.REPLACE
