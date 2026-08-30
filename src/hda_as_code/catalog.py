"""Catalog of common SOP nodes (Houdini 19.5 / 20.5).

Unknown nodes still work via ``Network.node`` — the catalog exists so builders
can name parms, skip defaults, and validate links without hou.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hda_as_code.types import ParmType

PT = ParmType


@dataclass(frozen=True)
class ParmSpec:
    name: str
    parm_type: ParmType
    default: Any = None
    items: tuple[str, ...] = ()


@dataclass(frozen=True)
class NodeSpec:
    type: str
    method: str
    label: str
    inputs: int = 0
    input_names: tuple[str, ...] = ()
    outputs: int = 1
    parms: tuple[ParmSpec, ...] = ()

    def parm_map(self) -> dict[str, ParmSpec]:
        return {p.name: p for p in self.parms}

    def known_parm_names(self) -> set[str]:
        names: set[str] = set()
        for parm in self.parms:
            names.add(parm.name)
            names.update(_component_names(parm.name, parm.parm_type, parm.default))
        return names


def _p(
    name: str,
    parm_type: ParmType,
    default: Any = None,
    *items: str,
) -> ParmSpec:
    return ParmSpec(name, parm_type, default, items)


def _component_names(name: str, parm_type: ParmType, default: Any) -> set[str]:
    if parm_type not in (ParmType.VECTOR, ParmType.INT3, ParmType.COLOR):
        return set()
    size = 3
    if isinstance(default, (list, tuple)) and default:
        size = len(default)
    suffixes = "xyzw"[:size] if size <= 4 else "".join(str(i + 1) for i in range(size))
    digits = "".join(str(i + 1) for i in range(size))
    return {f"{name}{s}" for s in suffixes} | {f"{name}{d}" for d in digits}


_SPECS: tuple[NodeSpec, ...] = (
    NodeSpec(
        "box",
        "box",
        "Box",
        inputs=1,
        parms=(
            _p("size", PT.VECTOR, (1.0, 1.0, 1.0)),
            _p("t", PT.VECTOR, (0.0, 0.0, 0.0)),
            _p("scale", PT.FLOAT, 1.0),
            _p("divrate", PT.INT3, (4, 4, 4)),
        ),
    ),
    NodeSpec(
        "sphere",
        "sphere",
        "Sphere",
        inputs=1,
        parms=(
            _p("type", PT.MENU, "prim", "prim", "poly", "nurbs", "mesh", "bezier", "points"),
            _p("radx", PT.FLOAT, 1.0),
            _p("rady", PT.FLOAT, 1.0),
            _p("radz", PT.FLOAT, 1.0),
            _p("rows", PT.INT, 10),
            _p("cols", PT.INT, 10),
            _p("t", PT.VECTOR, (0.0, 0.0, 0.0)),
        ),
    ),
    NodeSpec(
        "grid",
        "grid",
        "Grid",
        parms=(
            _p("rows", PT.INT, 10),
            _p("cols", PT.INT, 10),
            _p("sizex", PT.FLOAT, 1.0),
            _p("sizey", PT.FLOAT, 1.0),
            _p("orient", PT.MENU, "zx", "zx", "xy", "yz"),
            _p("t", PT.VECTOR, (0.0, 0.0, 0.0)),
        ),
    ),
    NodeSpec(
        "tube",
        "tube",
        "Tube",
        parms=(
            _p("type", PT.MENU, "poly", "prim", "poly", "nurbs"),
            _p("rad1", PT.FLOAT, 1.0),
            _p("rad2", PT.FLOAT, 1.0),
            _p("height", PT.FLOAT, 1.0),
            _p("cols", PT.INT, 10),
            _p("rows", PT.INT, 3),
            _p("t", PT.VECTOR, (0.0, 0.0, 0.0)),
        ),
    ),
    NodeSpec(
        "torus",
        "torus",
        "Torus",
        parms=(
            _p("radx", PT.FLOAT, 1.0),
            _p("rady", PT.FLOAT, 0.25),
            _p("rows", PT.INT, 20),
            _p("cols", PT.INT, 16),
            _p("t", PT.VECTOR, (0.0, 0.0, 0.0)),
        ),
    ),
    NodeSpec(
        "circle",
        "circle",
        "Circle",
        parms=(
            _p("type", PT.MENU, "poly", "prim", "poly", "nurbs", "bezier"),
            _p("radx", PT.FLOAT, 1.0),
            _p("rady", PT.FLOAT, 1.0),
            _p("divs", PT.INT, 10),
            _p("t", PT.VECTOR, (0.0, 0.0, 0.0)),
        ),
    ),
    NodeSpec(
        "line",
        "line",
        "Line",
        parms=(
            _p("dist", PT.FLOAT, 1.0),
            _p("points", PT.INT, 2),
            _p("dir", PT.VECTOR, (0.0, 1.0, 0.0)),
            _p("t", PT.VECTOR, (0.0, 0.0, 0.0)),
        ),
    ),
    NodeSpec(
        "mountain",
        "mountain",
        "Mountain",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("height", PT.FLOAT, 1.0),
            _p("elementsize", PT.FLOAT, 1.0),
            _p("offset", PT.VECTOR, (0.0, 0.0, 0.0)),
            _p("rough", PT.FLOAT, 0.5),
        ),
    ),
    NodeSpec(
        "attribnoise",
        "attribnoise",
        "Attribute Noise",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("attribs", PT.STRING, "P"),
            _p("offsetscale", PT.FLOAT, 1.0),
            _p("elementsize", PT.FLOAT, 1.0),
            _p("offset", PT.VECTOR, (0.0, 0.0, 0.0)),
            _p("rough", PT.FLOAT, 0.5),
        ),
    ),
    NodeSpec(
        "xform",
        "xform",
        "Transform",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("t", PT.VECTOR, (0.0, 0.0, 0.0)),
            _p("r", PT.VECTOR, (0.0, 0.0, 0.0)),
            _p("s", PT.VECTOR, (1.0, 1.0, 1.0)),
            _p("p", PT.VECTOR, (0.0, 0.0, 0.0)),
            _p("scale", PT.FLOAT, 1.0),
            _p("group", PT.STRING, ""),
        ),
    ),
    NodeSpec(
        "normal",
        "normal",
        "Normal",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("type", PT.MENU, "typepoint", "typepoint", "typevertex", "typeprim"),
            _p("cuspnangle", PT.FLOAT, 60.0),
        ),
    ),
    NodeSpec(
        "subdivide",
        "subdivide",
        "Subdivide",
        inputs=1,
        input_names=("geometry",),
        parms=(_p("iterations", PT.INT, 1),),
    ),
    NodeSpec(
        "polyextrude",
        "polyextrude",
        "Poly Extrude",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("group", PT.STRING, ""),
            _p("dist", PT.FLOAT, 0.0),
            _p("inset", PT.FLOAT, 0.0),
        ),
    ),
    NodeSpec(
        "blast",
        "blast",
        "Blast",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("group", PT.STRING, ""),
            _p("negate", PT.TOGGLE, False),
        ),
    ),
    NodeSpec(
        "null",
        "null",
        "Null",
        inputs=1,
        input_names=("geometry",),
    ),
    NodeSpec(
        "color",
        "color",
        "Color",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("color", PT.COLOR, (1.0, 1.0, 1.0)),
            _p("group", PT.STRING, ""),
        ),
    ),
    NodeSpec(
        "peak",
        "peak",
        "Peak",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("dist", PT.FLOAT, 0.0),
            _p("group", PT.STRING, ""),
        ),
    ),
    NodeSpec(
        "fuse",
        "fuse",
        "Fuse",
        inputs=1,
        input_names=("geometry",),
        parms=(_p("dist3d", PT.FLOAT, 0.001),),
    ),
    NodeSpec(
        "resample",
        "resample",
        "Resample",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("length", PT.FLOAT, 0.1),
            _p("dolength", PT.TOGGLE, True),
        ),
    ),
    NodeSpec(
        "bend",
        "bend",
        "Bend",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("bendangle", PT.FLOAT, 90.0),
            _p("length", PT.FLOAT, 1.0),
        ),
    ),
    NodeSpec(
        "groupcreate",
        "groupcreate",
        "Group Create",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("groupname", PT.STRING, "group1"),
            _p("groupbase", PT.MENU, "point", "point", "prim", "edge", "vertex"),
        ),
    ),
    NodeSpec(
        "attribwrangle",
        "attribwrangle",
        "Attribute Wrangle",
        inputs=4,
        input_names=("geometry", "input2", "input3", "input4"),
        parms=(
            _p("snippet", PT.STRING, ""),
            _p("class", PT.MENU, "point", "detail", "prim", "point", "vertex"),
            _p("group", PT.STRING, ""),
        ),
    ),
    NodeSpec(
        "merge",
        "merge",
        "Merge",
        inputs=-1,
        parms=(),
    ),
    NodeSpec(
        "boolean",
        "boolean",
        "Boolean",
        inputs=2,
        input_names=("a", "b"),
        parms=(
            _p("booleanop", PT.MENU, "subtract", "union", "intersect", "subtract"),
        ),
    ),
    NodeSpec(
        "scatter",
        "scatter",
        "Scatter",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("npts", PT.INT, 1000),
            _p("seed", PT.INT, 0),
            _p("force", PT.TOGGLE, False),
        ),
    ),
    NodeSpec(
        "copytopoints",
        "copytopoints",
        "Copy to Points",
        inputs=2,
        input_names=("source", "points"),
        parms=(
            _p("pack", PT.TOGGLE, False),
            _p("targetgroup", PT.STRING, ""),
            _p("sourcegroup", PT.STRING, ""),
        ),
    ),
    NodeSpec(
        "copy",
        "copy",
        "Copy",
        inputs=2,
        input_names=("source", "template"),
        parms=(_p("ncy", PT.INT, 1),),
    ),
    NodeSpec(
        "switch",
        "switch",
        "Switch",
        inputs=-1,
        parms=(_p("input", PT.INT, 0),),
    ),
    NodeSpec(
        "object_merge",
        "object_merge",
        "Object Merge",
        parms=(
            _p("objpath1", PT.STRING, ""),
            _p("xformtype", PT.MENU, "local", "none", "into_this_object", "local"),
        ),
    ),
    NodeSpec(
        "sweep",
        "sweep",
        "Sweep",
        inputs=2,
        input_names=("backbone", "cross_section"),
    ),
    NodeSpec(
        "skin",
        "skin",
        "Skin",
        inputs=-1,
    ),
    NodeSpec(
        "clip",
        "clip",
        "Clip",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("dir", PT.VECTOR, (0.0, 1.0, 0.0)),
            _p("dist", PT.FLOAT, 0.0),
        ),
    ),
    NodeSpec(
        "mirror",
        "mirror",
        "Mirror",
        inputs=1,
        input_names=("geometry",),
        parms=(
            _p("dir", PT.VECTOR, (1.0, 0.0, 0.0)),
            _p("dist", PT.FLOAT, 0.0),
            _p("keeporiginal", PT.TOGGLE, True),
        ),
    ),
    NodeSpec(
        "smooth",
        "smooth",
        "Smooth",
        inputs=1,
        input_names=("geometry",),
        parms=(_p("iterations", PT.INT, 1),),
    ),
    NodeSpec(
        "file",
        "file",
        "File",
        parms=(_p("file", PT.STRING, ""),),
    ),
)

CATALOG: tuple[NodeSpec, ...] = _SPECS
CATALOG_BY_TYPE: dict[str, NodeSpec] = {spec.type: spec for spec in _SPECS}
CATALOG_BY_METHOD: dict[str, NodeSpec] = {spec.method: spec for spec in _SPECS}


def get_spec(node_type: str) -> NodeSpec | None:
    if node_type in CATALOG_BY_TYPE:
        return CATALOG_BY_TYPE[node_type]
    # Houdini versioned types: copytopoints::2.0
    base = node_type.split("::", 1)[0]
    return CATALOG_BY_TYPE.get(base)


def values_equal(left: Any, right: Any) -> bool:
    if left == right:
        return True
    if isinstance(left, dict) or isinstance(right, dict):
        return left == right
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        if len(left) != len(right):
            return False
        return all(values_equal(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) < 1e-9
    return False
