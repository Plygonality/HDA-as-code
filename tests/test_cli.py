from __future__ import annotations

import json
from pathlib import Path

from hda_as_code.cli import main
from hda_as_code.samples import build_column, build_terrain


def test_cli_dump_diff_validate(tmp_path: Path, capsys) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(build_column().dumps(), encoding="utf-8")
    b.write_text(build_terrain().dumps(), encoding="utf-8")

    assert main(["validate", str(a)]) == 0
    assert capsys.readouterr().out.strip() == "ok"

    out = tmp_path / "canonical.json"
    assert main(["dump", str(a), "-o", str(out)]) == 0
    assert json.loads(out.read_text())["name"] == "Column"

    assert main(["diff", str(a), str(a)]) == 0
    assert main(["diff", str(a), str(b)]) == 1
    captured = capsys.readouterr().out
    assert "+ node" in captured or "- node" in captured

    assert main(["mermaid", str(a)]) == 0
    assert "flowchart LR" in capsys.readouterr().out

    assert main(["apply-script", str(a)]) == 0
    script = capsys.readouterr().out
    assert "apply_network_dict" in script
