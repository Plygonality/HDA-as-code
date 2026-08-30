"""Canonical SOP-network IR.

The dump format is the source of truth. A ``.hip`` is a cache you apply into.
This is not full HDA binary management — just the SOP chains you actually use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hda_as_code.types import NetworkKind, ParmType, jsonify

FORMAT = "hda-as-code"
FORMAT_VERSION = 1


@dataclass
class ParmItem:
    """An exposed spare parm on the parent geo/subnet (the HDA-lite interface)."""

    name: str
    type: ParmType
    default: Any = None
    min: float | None = None
    max: float | None = None
    menu: tuple[str, ...] = ()
    label: str = ""
    help: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "type": self.type.value,
        }
        if self.default is not None:
            data["default"] = jsonify(self.default)
        if self.min is not None:
            data["min"] = jsonify(self.min)
        if self.max is not None:
            data["max"] = jsonify(self.max)
        if self.menu:
            data["menu"] = list(self.menu)
        if self.label:
            data["label"] = self.label
        if self.help:
            data["help"] = self.help
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParmItem:
        menu = data.get("menu") or ()
        return cls(
            name=data["name"],
            type=ParmType(data["type"]),
            default=data.get("default"),
            min=data.get("min"),
            max=data.get("max"),
            menu=tuple(menu),
            label=data.get("label", ""),
            help=data.get("help", ""),
        )


@dataclass
class Node:
    id: str
    type: str
    label: str = ""
    location: tuple[float, float] | None = None
    bypass: bool = False
    comment: str = ""
    color: tuple[float, float, float] | None = None
    parms: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
        }
        if self.label:
            data["label"] = self.label
        if self.location is not None:
            data["location"] = [jsonify(self.location[0]), jsonify(self.location[1])]
        if self.bypass:
            data["bypass"] = True
        if self.comment:
            data["comment"] = self.comment
        if self.color is not None:
            data["color"] = [jsonify(c) for c in self.color]
        if self.parms:
            data["parms"] = {k: _jsonify_parm(v) for k, v in sorted(self.parms.items())}
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        location = data.get("location")
        loc = None
        if location is not None:
            loc = (float(location[0]), float(location[1]))
        color = data.get("color")
        col = None
        if color is not None:
            col = (float(color[0]), float(color[1]), float(color[2]))
        return cls(
            id=data["id"],
            type=data["type"],
            label=data.get("label", ""),
            location=loc,
            bypass=bool(data.get("bypass", False)),
            comment=data.get("comment", ""),
            color=col,
            parms=dict(data.get("parms") or {}),
        )


@dataclass
class Link:
    from_node: str
    from_output: int
    to_node: str
    to_input: int

    def key(self) -> tuple[str, int, str, int]:
        return (self.from_node, int(self.from_output), self.to_node, int(self.to_input))

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": [self.from_node, int(self.from_output)],
            "to": [self.to_node, int(self.to_input)],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Link:
        if "from" in data:
            src, dst = data["from"], data["to"]
            return cls(str(src[0]), int(src[1]), str(dst[0]), int(dst[1]))
        return cls(
            data["from_node"],
            int(data.get("from_output", data.get("from_socket", 0))),
            data["to_node"],
            int(data.get("to_input", data.get("to_socket", 0))),
        )


@dataclass
class NetworkData:
    name: str
    kind: NetworkKind = NetworkKind.GEO
    houdini: str = "20.5"
    interface: list[ParmItem] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    display: str | None = None

    def node_map(self) -> dict[str, Node]:
        return {node.id: node for node in self.nodes}

    def canonical(self) -> NetworkData:
        """Return a copy sorted for stable dumps and diffs."""
        return NetworkData(
            name=self.name,
            kind=self.kind,
            houdini=self.houdini,
            interface=list(self.interface),
            nodes=sorted(self.nodes, key=lambda n: n.id),
            links=sorted(self.links, key=lambda ln: ln.key()),
            display=self.display,
        )

    def to_dict(self) -> dict[str, Any]:
        network = self.canonical()
        payload: dict[str, Any] = {
            "format": FORMAT,
            "version": FORMAT_VERSION,
            "name": network.name,
            "kind": network.kind.value,
            "houdini": network.houdini,
            "interface": {
                "parms": [item.to_dict() for item in network.interface],
            },
            "nodes": [node.to_dict() for node in network.nodes],
            "links": [link.to_dict() for link in network.links],
        }
        if network.display:
            payload["display"] = network.display
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NetworkData:
        fmt = data.get("format")
        if fmt not in (None, FORMAT):
            raise ValueError(f"Unsupported network format: {fmt!r}")
        version = data.get("version", FORMAT_VERSION)
        if int(version) != FORMAT_VERSION:
            raise ValueError(f"Unsupported hda-as-code version: {version}")
        interface = data.get("interface") or {}
        parms = interface.get("parms", interface.get("inputs", []))
        kind_raw = data.get("kind", NetworkKind.GEO.value)
        return cls(
            name=data["name"],
            kind=NetworkKind(kind_raw),
            houdini=str(data.get("houdini", "20.5")),
            interface=[ParmItem.from_dict(x) for x in parms],
            nodes=[Node.from_dict(x) for x in data.get("nodes", [])],
            links=[Link.from_dict(x) for x in data.get("links", [])],
            display=data.get("display"),
        ).canonical()


def _jsonify_parm(value: Any) -> Any:
    if isinstance(value, dict) and ("ref" in value or "expr" in value):
        if set(value) <= {"ref", "expr"}:
            return dict(value)
    return jsonify(value)
