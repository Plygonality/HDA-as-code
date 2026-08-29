"""Apply / dump helpers and Plygon-mcp script generation.

The useful artifact is the network JSON plus this library. Plygon-mcp is how an
agent pushes a dump into a live Houdini session and screenshots the viewport.
"""

from __future__ import annotations

import json
from pathlib import Path

from hda_as_code.dump import to_dict
from hda_as_code.ir import NetworkData
from hda_as_code.runtime_apply import apply_network_dict, dump_network, dump_network_by_path

_RUNTIME_PATH = Path(__file__).with_name("runtime_apply.py")


def apply(network: NetworkData | dict, hou=None, **kwargs):
    """Apply a network inside Houdini. Imports ``hou`` if omitted."""
    if hou is None:
        hou = __import__("hou")
    payload = network if isinstance(network, dict) else to_dict(network)
    return apply_network_dict(payload, hou, **kwargs)


def dump_from_hou(node, *, houdini: str = "20.5") -> dict:
    return dump_network(node, houdini=houdini)


def to_apply_script(
    network: NetworkData | dict,
    *,
    parent_path: str | None = None,
    replace: bool = True,
) -> str:
    """Self-contained hou script. Paste into Plygon-mcp ``execute_houdini_code``."""
    payload = network if isinstance(network, dict) else to_dict(network)
    runtime = _RUNTIME_PATH.read_text(encoding="utf-8")
    call = (
        "parent = apply_network_dict(\n"
        f"    {json.dumps(payload, indent=2)},\n"
        "    hou,\n"
        f"    parent_path={parent_path!r},\n"
        f"    replace={replace!r},\n"
        ")\n"
        "print(parent.path())\n"
    )
    return runtime + "\n\n" + call


def to_dump_script(path: str, *, houdini: str = "20.5") -> str:
    """Self-contained hou script that prints a network dump as JSON."""
    runtime = _RUNTIME_PATH.read_text(encoding="utf-8")
    call = (
        "import json\n"
        f"result = dump_network_by_path(hou, {path!r}, houdini={houdini!r})\n"
        "print(json.dumps(result, indent=2))\n"
    )
    return runtime + "\n\n" + call


__all__ = [
    "apply",
    "apply_network_dict",
    "dump_from_hou",
    "dump_network",
    "dump_network_by_path",
    "to_apply_script",
    "to_dump_script",
]
