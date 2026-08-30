"""Canonical JSON dump / load and mermaid rendering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO

from hda_as_code.catalog import get_spec
from hda_as_code.ir import FORMAT, FORMAT_VERSION, NetworkData
from hda_as_code.types import jsonify

PathLike = str | Path


def to_dict(network: NetworkData | dict[str, Any]) -> dict[str, Any]:
    if isinstance(network, dict):
        return NetworkData.from_dict(network).to_dict()
    return network.canonical().to_dict()


def from_dict(data: dict[str, Any]) -> NetworkData:
    return NetworkData.from_dict(data)


def dumps(network: NetworkData | dict[str, Any], *, indent: int = 2) -> str:
    payload = to_dict(network)
    return json.dumps(payload, indent=indent, sort_keys=False, ensure_ascii=False) + "\n"


def loads(text: str) -> NetworkData:
    return from_dict(json.loads(text))


def dump(network: NetworkData | dict[str, Any], path: PathLike, *, indent: int = 2) -> None:
    Path(path).write_text(dumps(network, indent=indent), encoding="utf-8")


def load(path: PathLike) -> NetworkData:
    return loads(Path(path).read_text(encoding="utf-8"))


def dump_fp(network: NetworkData | dict[str, Any], fp: TextIO, *, indent: int = 2) -> None:
    fp.write(dumps(network, indent=indent))


def to_mermaid(network: NetworkData | dict[str, Any]) -> str:
    data = network if isinstance(network, NetworkData) else NetworkData.from_dict(network)
    data = data.canonical()
    lines = ["flowchart LR"]
    for node in data.nodes:
        spec = get_spec(node.type)
        title = node.label or (spec.label if spec else node.type)
        extra = " *" if data.display == node.id else ""
        label = f"{node.id}{extra}<br/>{title}".replace('"', "'")
        lines.append(f'  {_mid(node.id)}["{label}"]')
    for link in data.links:
        sock = f"in{link.to_input}" if link.to_input else ""
        arrow = f"|{sock}|" if sock else ""
        lines.append(f"  {_mid(link.from_node)} -->{arrow} {_mid(link.to_node)}")
    return "\n".join(lines) + "\n"


def _mid(node_id: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in node_id)
    if not safe or safe[0].isdigit():
        safe = "n_" + safe
    return safe


def fingerprint(network: NetworkData | dict[str, Any], *, include_layout: bool = False) -> dict[str, Any]:
    """Identity of a network for equality tests. Layout is ignored by default."""
    data = to_dict(network)
    if not include_layout:
        for node in data.get("nodes", []):
            node.pop("location", None)
    return jsonify(data)  # type: ignore[return-value]


__all__ = [
    "FORMAT",
    "FORMAT_VERSION",
    "dump",
    "dump_fp",
    "dumps",
    "fingerprint",
    "from_dict",
    "load",
    "loads",
    "to_dict",
    "to_mermaid",
]
