"""CLI: dump, diff, validate, mermaid, apply-script."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hda_as_code.apply import to_apply_script, to_dump_script
from hda_as_code.diff import diff_networks, format_diff
from hda_as_code.dump import dump as dump_file
from hda_as_code.dump import load, to_mermaid
from hda_as_code.validate import validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hda-as-code",
        description="Build, dump, and diff Houdini SOP network fragments as data.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_dump = sub.add_parser("dump", help="Rewrite a network JSON into canonical form")
    p_dump.add_argument("path")
    p_dump.add_argument("-o", "--output")

    p_diff = sub.add_parser("diff", help="Structural diff of two network dumps")
    p_diff.add_argument("old")
    p_diff.add_argument("new")
    p_diff.add_argument("--layout", action="store_true", help="Include node locations")
    p_diff.add_argument("--json", action="store_true", help="Emit JSON instead of text")

    p_val = sub.add_parser("validate", help="Validate a network dump")
    p_val.add_argument("path")

    p_mmd = sub.add_parser("mermaid", help="Render a network dump as mermaid")
    p_mmd.add_argument("path")

    p_apply = sub.add_parser("apply-script", help="Emit a hou script Plygon-mcp can run")
    p_apply.add_argument("path")
    p_apply.add_argument("--parent", dest="parent_path")
    p_apply.add_argument("-o", "--output")

    p_from = sub.add_parser("dump-script", help="Emit a hou script that prints a live network as JSON")
    p_from.add_argument("node_path")
    p_from.add_argument("-o", "--output")

    args = parser.parse_args(argv)
    if args.cmd == "dump":
        data = load(args.path)
        if args.output:
            dump_file(data, args.output)
        else:
            sys.stdout.write(json.dumps(data.to_dict(), indent=2) + "\n")
        return 0
    if args.cmd == "diff":
        diff = diff_networks(load(args.old), load(args.new), include_layout=args.layout)
        if args.json:
            sys.stdout.write(json.dumps(diff.to_dict(), indent=2) + "\n")
        else:
            sys.stdout.write(format_diff(diff))
        return 0 if diff.is_empty() else 1
    if args.cmd == "validate":
        errors = validate(load(args.path))
        if not errors:
            sys.stdout.write("ok\n")
            return 0
        for err in errors:
            sys.stderr.write(str(err) + "\n")
        return 2
    if args.cmd == "mermaid":
        sys.stdout.write(to_mermaid(load(args.path)))
        return 0
    if args.cmd == "apply-script":
        script = to_apply_script(load(args.path), parent_path=args.parent_path)
        if args.output:
            Path(args.output).write_text(script, encoding="utf-8")
        else:
            sys.stdout.write(script)
        return 0
    if args.cmd == "dump-script":
        script = to_dump_script(args.node_path)
        if args.output:
            Path(args.output).write_text(script, encoding="utf-8")
        else:
            sys.stdout.write(script)
        return 0
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
