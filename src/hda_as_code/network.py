"""Typed SOP-network builder.

A ``Network`` is both the authoring API and the in-memory IR. Call ``to_dict`` /
``dumps`` when you want the version-controlled artifact.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from hda_as_code.catalog import CATALOG_BY_METHOD, NodeSpec, get_spec, values_equal
from hda_as_code.ir import Link, NetworkData, Node, ParmItem
from hda_as_code.types import JsonValue, NetworkKind, ParmType, jsonify

InputValue = Any


@dataclass(frozen=True)
class ParmRef:
    """A parent spare parm that can drive a node parm via a channel reference."""

    name: str
    parm_type: ParmType | None = None


@dataclass(frozen=True)
class Expr:
    """A raw Houdini expression (hscript by default)."""

    code: str


@dataclass(frozen=True)
class OutputRef:
    """A node's output connector, wired into another node's input index."""

    node: str
    output: int = 0

    def as_link_src(self) -> tuple[str, int]:
        return self.node, self.output


@dataclass
class NodeHandle:
    """Handle to a SOP already in the network."""

    network: Network
    id: str
    spec: NodeSpec | None = None

    def out(self, output: int = 0) -> OutputRef:
        return OutputRef(self.id, int(output))

    def as_output(self) -> OutputRef:
        return OutputRef(self.id, 0)

    def __getitem__(self, output: int) -> OutputRef:
        return self.out(int(output))


class Network:
    """Author a SOP network fragment as data."""

    def __init__(
        self,
        name: str,
        *,
        kind: NetworkKind | str = NetworkKind.GEO,
        houdini: str = "20.5",
    ) -> None:
        self.name = name
        self.kind = NetworkKind(kind)
        self.houdini = houdini
        self._interface: list[ParmItem] = []
        self._nodes: dict[str, Node] = {}
        self._links: list[Link] = []
        self._used_ids: set[str] = set()
        self._display: str | None = None

    # --- interface (spare parms on the parent geo / subnet) ----------------

    def parm(
        self,
        name: str,
        type: ParmType | str,
        default: JsonValue = None,
        *,
        min: float | None = None,
        max: float | None = None,
        menu: Sequence[str] = (),
        label: str = "",
        help: str = "",
    ) -> ParmRef:
        ptype = type if isinstance(type, ParmType) else ParmType(type)
        token = _safe_node_name(name) if " " in name else name
        item = ParmItem(
            name=token,
            type=ptype,
            default=jsonify(default) if default is not None else None,
            min=min,
            max=max,
            menu=tuple(menu),
            label=label or (name if token != name else ""),
            help=help,
        )
        existing = next((i for i in self._interface if i.name == name), None)
        if existing is not None:
            self._interface[self._interface.index(existing)] = item
        else:
            self._interface.append(item)
        return ParmRef(token, ptype)

    def parm_float(
        self,
        name: str,
        default: float = 0.0,
        *,
        min: float | None = None,
        max: float | None = None,
        label: str = "",
        help: str = "",
    ) -> ParmRef:
        return self.parm(name, ParmType.FLOAT, default, min=min, max=max, label=label, help=help)

    def parm_int(
        self,
        name: str,
        default: int = 0,
        *,
        min: float | None = None,
        max: float | None = None,
        label: str = "",
        help: str = "",
    ) -> ParmRef:
        return self.parm(name, ParmType.INT, default, min=min, max=max, label=label, help=help)

    def parm_toggle(self, name: str, default: bool = False, *, label: str = "", help: str = "") -> ParmRef:
        return self.parm(name, ParmType.TOGGLE, default, label=label, help=help)

    def parm_string(self, name: str, default: str = "", *, label: str = "", help: str = "") -> ParmRef:
        return self.parm(name, ParmType.STRING, default, label=label, help=help)

    def parm_vector(
        self,
        name: str,
        default: Sequence[float] = (0.0, 0.0, 0.0),
        *,
        label: str = "",
        help: str = "",
    ) -> ParmRef:
        return self.parm(name, ParmType.VECTOR, tuple(default), label=label, help=help)

    def expr(self, code: str) -> Expr:
        return Expr(code)

    # --- display / output --------------------------------------------------

    def display(self, node: NodeHandle | str) -> NodeHandle:
        node_id = node.id if isinstance(node, NodeHandle) else node
        self._display = node_id
        if node_id not in self._nodes:
            raise KeyError(f"Cannot display unknown node {node_id!r}")
        return NodeHandle(self, node_id, get_spec(self._nodes[node_id].type))

    # --- generic node spawn ------------------------------------------------

    def node(
        self,
        type: str,
        *,
        id: str | None = None,
        label: str = "",
        location: Sequence[float] | None = None,
        bypass: bool = False,
        comment: str = "",
        color: Sequence[float] | None = None,
        inputs: Sequence[InputValue] | dict[int, InputValue] | None = None,
        parms: dict[str, InputValue] | None = None,
        **extra_parms: InputValue,
    ) -> NodeHandle:
        spec = get_spec(type)
        node_id = self._fresh_id(id or (spec.method if spec else type.split("::", 1)[0]))
        merged = dict(parms or {})
        merged.update(extra_parms)
        recorded = self._record_parms(spec, merged)
        loc = None if location is None else (float(location[0]), float(location[1]))
        col = None if color is None else (float(color[0]), float(color[1]), float(color[2]))
        self._nodes[node_id] = Node(
            id=node_id,
            type=type,
            label=label,
            location=loc,
            bypass=bypass,
            comment=comment,
            color=col,
            parms=recorded,
        )
        self._wire_inputs(node_id, inputs)
        return NodeHandle(self, node_id, spec)

    def link(
        self,
        source: InputValue,
        target: NodeHandle | str,
        input: int = 0,
    ) -> None:
        node_id = target.id if isinstance(target, NodeHandle) else target
        self._connect(source, node_id, int(input))

    # --- typed factories: generators --------------------------------------

    def box(
        self,
        geometry: InputValue = None,
        *,
        size: InputValue = (1.0, 1.0, 1.0),
        t: InputValue = (0.0, 0.0, 0.0),
        scale: InputValue = 1.0,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "box",
            id=id,
            inputs=_optional_inputs(geometry),
            parms={"size": size, "t": t, "scale": scale},
            **node_kw,
        )

    def sphere(
        self,
        geometry: InputValue = None,
        *,
        radx: InputValue = 1.0,
        rady: InputValue = 1.0,
        radz: InputValue = 1.0,
        rows: InputValue = 10,
        cols: InputValue = 10,
        type: InputValue = "prim",
        t: InputValue = (0.0, 0.0, 0.0),
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "sphere",
            id=id,
            inputs=_optional_inputs(geometry),
            parms={
                "type": type,
                "radx": radx,
                "rady": rady,
                "radz": radz,
                "rows": rows,
                "cols": cols,
                "t": t,
            },
            **node_kw,
        )

    def grid(
        self,
        *,
        rows: InputValue = 10,
        cols: InputValue = 10,
        sizex: InputValue = 1.0,
        sizey: InputValue = 1.0,
        orient: InputValue = "zx",
        t: InputValue = (0.0, 0.0, 0.0),
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "grid",
            id=id,
            parms={
                "rows": rows,
                "cols": cols,
                "sizex": sizex,
                "sizey": sizey,
                "orient": orient,
                "t": t,
            },
            **node_kw,
        )

    def tube(
        self,
        *,
        rad1: InputValue = 1.0,
        rad2: InputValue = 1.0,
        height: InputValue = 1.0,
        cols: InputValue = 10,
        rows: InputValue = 3,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "tube",
            id=id,
            parms={"rad1": rad1, "rad2": rad2, "height": height, "cols": cols, "rows": rows},
            **node_kw,
        )

    def torus(
        self,
        *,
        radx: InputValue = 1.0,
        rady: InputValue = 0.25,
        rows: InputValue = 20,
        cols: InputValue = 16,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "torus",
            id=id,
            parms={"radx": radx, "rady": rady, "rows": rows, "cols": cols},
            **node_kw,
        )

    def circle(
        self,
        *,
        radx: InputValue = 1.0,
        rady: InputValue = 1.0,
        divs: InputValue = 10,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node("circle", id=id, parms={"radx": radx, "rady": rady, "divs": divs}, **node_kw)

    def line(
        self,
        *,
        dist: InputValue = 1.0,
        points: InputValue = 2,
        dir: InputValue = (0.0, 1.0, 0.0),
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node("line", id=id, parms={"dist": dist, "points": points, "dir": dir}, **node_kw)

    # --- typed factories: filters -----------------------------------------

    def mountain(
        self,
        geometry: InputValue,
        *,
        height: InputValue = 1.0,
        elementsize: InputValue = 1.0,
        offset: InputValue = (0.0, 0.0, 0.0),
        rough: InputValue = 0.5,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "mountain",
            id=id,
            inputs=[geometry],
            parms={
                "height": height,
                "elementsize": elementsize,
                "offset": offset,
                "rough": rough,
            },
            **node_kw,
        )

    def attribnoise(
        self,
        geometry: InputValue,
        *,
        attribs: InputValue = "P",
        offsetscale: InputValue = 1.0,
        elementsize: InputValue = 1.0,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "attribnoise",
            id=id,
            inputs=[geometry],
            parms={"attribs": attribs, "offsetscale": offsetscale, "elementsize": elementsize},
            **node_kw,
        )

    def xform(
        self,
        geometry: InputValue,
        *,
        t: InputValue = (0.0, 0.0, 0.0),
        r: InputValue = (0.0, 0.0, 0.0),
        s: InputValue = (1.0, 1.0, 1.0),
        scale: InputValue = 1.0,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "xform",
            id=id,
            inputs=[geometry],
            parms={"t": t, "r": r, "s": s, "scale": scale},
            **node_kw,
        )

    def transform(self, geometry: InputValue, **kwargs: Any) -> NodeHandle:
        return self.xform(geometry, **kwargs)

    def normal(
        self,
        geometry: InputValue,
        *,
        type: InputValue = "typepoint",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node("normal", id=id, inputs=[geometry], parms={"type": type}, **node_kw)

    def subdivide(
        self,
        geometry: InputValue,
        *,
        iterations: InputValue = 1,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "subdivide",
            id=id,
            inputs=[geometry],
            parms={"iterations": iterations},
            **node_kw,
        )

    def polyextrude(
        self,
        geometry: InputValue,
        *,
        dist: InputValue = 0.0,
        inset: InputValue = 0.0,
        group: InputValue = "",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "polyextrude",
            id=id,
            inputs=[geometry],
            parms={"dist": dist, "inset": inset, "group": group},
            **node_kw,
        )

    def blast(
        self,
        geometry: InputValue,
        *,
        group: InputValue = "",
        negate: InputValue = False,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "blast",
            id=id,
            inputs=[geometry],
            parms={"group": group, "negate": negate},
            **node_kw,
        )

    def null(self, geometry: InputValue = None, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("null", id=id, inputs=_optional_inputs(geometry), **node_kw)

    def color(
        self,
        geometry: InputValue,
        *,
        color: InputValue = (1.0, 1.0, 1.0),
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node("color", id=id, inputs=[geometry], parms={"color": color}, **node_kw)

    def attribwrangle(
        self,
        geometry: InputValue,
        snippet: InputValue,
        *,
        class_: InputValue = "point",
        group: InputValue = "",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "attribwrangle",
            id=id,
            inputs=[geometry],
            parms={"snippet": snippet, "class": class_, "group": group},
            **node_kw,
        )

    def scatter(
        self,
        geometry: InputValue,
        *,
        npts: InputValue = 1000,
        seed: InputValue = 0,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "scatter",
            id=id,
            inputs=[geometry],
            parms={"npts": npts, "seed": seed},
            **node_kw,
        )

    # --- typed factories: multi-input -------------------------------------

    def merge(self, *geometries: InputValue, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("merge", id=id, inputs=list(geometries), **node_kw)

    def boolean(
        self,
        a: InputValue,
        b: InputValue,
        *,
        booleanop: InputValue = "subtract",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "boolean",
            id=id,
            inputs=[a, b],
            parms={"booleanop": booleanop},
            **node_kw,
        )

    def copytopoints(
        self,
        source: InputValue,
        points: InputValue,
        *,
        pack: InputValue = False,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "copytopoints",
            id=id,
            inputs=[source, points],
            parms={"pack": pack},
            **node_kw,
        )

    def copy(
        self,
        source: InputValue,
        template: InputValue | None = None,
        *,
        ncy: InputValue = 1,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: list[InputValue] = [source]
        if template is not None:
            inputs.append(template)
        return self.node("copy", id=id, inputs=inputs, parms={"ncy": ncy}, **node_kw)

    def switch(self, *geometries: InputValue, input: InputValue = 0, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("switch", id=id, inputs=list(geometries), parms={"input": input}, **node_kw)

    def object_merge(
        self,
        objpath1: InputValue = "",
        *,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node("object_merge", id=id, parms={"objpath1": objpath1}, **node_kw)

    def __getattr__(self, name: str) -> Any:
        spec = CATALOG_BY_METHOD.get(name)
        if spec is None:
            raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

        def factory(*args: Any, id: str | None = None, **kwargs: Any) -> NodeHandle:
            inputs: list[InputValue] = []
            parms: dict[str, InputValue] = {}
            positional = list(args)
            max_inputs = spec.inputs if spec.inputs >= 0 else len(positional)
            for _ in range(max_inputs):
                if positional and _is_wire(positional[0]):
                    inputs.append(positional.pop(0))
                else:
                    break
            for parm in spec.parms:
                if parm.name in kwargs:
                    parms[parm.name] = kwargs.pop(parm.name)
                elif positional and not _is_wire(positional[0]):
                    parms[parm.name] = positional.pop(0)
            return self.node(spec.type, id=id, inputs=inputs, parms=parms, **kwargs)

        factory.__name__ = spec.method
        factory.__doc__ = f"Create a {spec.label} ({spec.type}) SOP."
        return factory

    # --- layout ------------------------------------------------------------

    def autolayout(self, *, x_step: float = 3.0, y_step: float = 1.0) -> None:
        """Assign stable left-to-right locations from topology. Existing locations win."""
        levels = self._levels()
        for level, ids in enumerate(levels):
            count = len(ids)
            for i, node_id in enumerate(sorted(ids)):
                node = self._nodes[node_id]
                if node.location is not None:
                    continue
                y = (count - 1) * y_step / 2.0 - i * y_step
                node.location = (level * x_step, y)

    # --- serialize ---------------------------------------------------------

    def to_data(self, *, autolayout: bool = True) -> NetworkData:
        if autolayout:
            self.autolayout()
        return NetworkData(
            name=self.name,
            kind=self.kind,
            houdini=self.houdini,
            interface=list(self._interface),
            nodes=list(self._nodes.values()),
            links=list(self._links),
            display=self._display or self._default_display(),
        ).canonical()

    def to_dict(self, *, autolayout: bool = True) -> dict[str, Any]:
        from hda_as_code.dump import to_dict

        return to_dict(self.to_data(autolayout=autolayout))

    def dumps(self, *, autolayout: bool = True) -> str:
        from hda_as_code.dump import dumps

        return dumps(self.to_data(autolayout=autolayout))

    def to_mermaid(self) -> str:
        from hda_as_code.dump import to_mermaid

        return to_mermaid(self.to_data(autolayout=False))

    @classmethod
    def from_data(cls, data: NetworkData) -> Network:
        network = cls(data.name, kind=data.kind, houdini=data.houdini)
        network._interface = list(data.interface)
        network._nodes = {node.id: node for node in data.nodes}
        network._links = list(data.links)
        network._used_ids = set(network._nodes)
        network._display = data.display
        return network

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Network:
        return cls.from_data(NetworkData.from_dict(data))

    # --- internals ---------------------------------------------------------

    def _fresh_id(self, base: str) -> str:
        candidate = _safe_node_name(base)
        n = 1
        while candidate in self._used_ids:
            n += 1
            candidate = f"{_safe_node_name(base)}_{n}"
        self._used_ids.add(candidate)
        return candidate

    def _record_parms(self, spec: NodeSpec | None, parms: dict[str, InputValue]) -> dict[str, JsonValue]:
        expanded: dict[str, InputValue] = {}
        for key, value in parms.items():
            expanded.update(_expand_parm(key, value))
        recorded: dict[str, JsonValue] = {}
        for key, value in expanded.items():
            encoded = _encode_parm(value)
            if spec is not None and _is_catalog_default(spec, key, encoded):
                continue
            recorded[key] = encoded
        return recorded

    def _wire_inputs(self, node_id: str, inputs: Sequence[InputValue] | dict[int, InputValue] | None) -> None:
        if not inputs:
            return
        if isinstance(inputs, dict):
            items = sorted(inputs.items())
        else:
            items = list(enumerate(inputs))
        for index, source in items:
            if source is None:
                continue
            self._connect(source, node_id, int(index))

    def _as_output(self, value: InputValue) -> OutputRef:
        if isinstance(value, OutputRef):
            return value
        if isinstance(value, NodeHandle):
            return value.as_output()
        raise TypeError(f"Expected a node handle or output ref, got {type(value)!r}")

    def _connect(self, source: InputValue, to_node: str, to_input: int) -> None:
        ref = self._as_output(source)
        link = Link(ref.node, ref.output, to_node, to_input)
        if any(existing.key() == link.key() for existing in self._links):
            return
        self._links.append(link)

    def _default_display(self) -> str | None:
        if not self._nodes:
            return None
        outgoing = {ln.from_node for ln in self._links}
        sinks = [nid for nid in self._nodes if nid not in outgoing]
        if len(sinks) == 1:
            return sinks[0]
        return next(reversed(self._nodes))

    def _levels(self) -> list[list[str]]:
        incoming: dict[str, set[str]] = {node_id: set() for node_id in self._nodes}
        for link in self._links:
            if link.from_node in incoming and link.to_node in incoming:
                incoming[link.to_node].add(link.from_node)
        levels: list[list[str]] = []
        remaining = set(self._nodes)
        while remaining:
            ready = [n for n in remaining if incoming[n].isdisjoint(remaining)]
            if not ready:
                ready = sorted(remaining)
            levels.append(ready)
            remaining.difference_update(ready)
        return levels


def _optional_inputs(geometry: InputValue) -> list[InputValue]:
    return [] if geometry is None else [geometry]


def _is_wire(value: Any) -> bool:
    return isinstance(value, (NodeHandle, OutputRef))


def _safe_node_name(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)
    if not cleaned or cleaned[0].isdigit():
        cleaned = "n_" + cleaned
    return cleaned


def _expand_parm(name: str, value: InputValue) -> dict[str, InputValue]:
    if isinstance(value, (list, tuple)) and any(isinstance(v, (ParmRef, Expr)) for v in value):
        suffixes = "xyzw"[: len(value)] if len(value) <= 4 else [str(i + 1) for i in range(len(value))]
        return {f"{name}{suffix}": part for suffix, part in zip(suffixes, value, strict=True)}
    return {name: value}


def _encode_parm(value: InputValue) -> JsonValue:
    if isinstance(value, ParmRef):
        return {"ref": value.name}
    if isinstance(value, Expr):
        return {"expr": value.code}
    if isinstance(value, dict) and ("ref" in value or "expr" in value):
        return dict(value)
    return jsonify(value)


def _is_catalog_default(spec: NodeSpec, key: str, encoded: JsonValue) -> bool:
    if isinstance(encoded, dict) and ("ref" in encoded or "expr" in encoded):
        return False
    parm = spec.parm_map().get(key)
    if parm is not None:
        return values_equal(encoded, jsonify(parm.default) if parm.default is not None else None)
    for parent in spec.parms:
        components = []
        if parent.parm_type in (ParmType.VECTOR, ParmType.INT3, ParmType.COLOR):
            default = parent.default
            if isinstance(default, (list, tuple)):
                for i, suffix in enumerate("xyzw"[: len(default)]):
                    if f"{parent.name}{suffix}" == key:
                        components.append((i, default))
                for i in range(len(default)):
                    if f"{parent.name}{i + 1}" == key:
                        components.append((i, default))
        if components:
            index, default = components[0]
            return values_equal(encoded, jsonify(default[index]))
    return False
