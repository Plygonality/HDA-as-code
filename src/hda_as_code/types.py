"""Parm kinds, network kinds, and JSON-safe value helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any

Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]
JsonValue = None | bool | int | float | str | list[Any] | dict[str, Any]


class NetworkKind(str, Enum):
    """How Houdini should host the SOP fragment."""

    GEO = "GEO"
    SUBNET = "SUBNET"


class ParmType(str, Enum):
    """Stable parameter kinds used in the dump format.

    These map to hou parm templates in apply/dump.
    """

    FLOAT = "FLOAT"
    INT = "INT"
    TOGGLE = "TOGGLE"
    STRING = "STRING"
    VECTOR = "VECTOR"
    INT3 = "INT3"
    COLOR = "COLOR"
    MENU = "MENU"

    def hou_template(self) -> str:
        return _HOU_TEMPLATE[self]


_HOU_TEMPLATE: dict[ParmType, str] = {
    ParmType.FLOAT: "FloatParmTemplate",
    ParmType.INT: "IntParmTemplate",
    ParmType.TOGGLE: "ToggleParmTemplate",
    ParmType.STRING: "StringParmTemplate",
    ParmType.VECTOR: "FloatParmTemplate",
    ParmType.INT3: "IntParmTemplate",
    ParmType.COLOR: "FloatParmTemplate",
    ParmType.MENU: "MenuParmTemplate",
}


def parse_parm_type(value: str) -> ParmType:
    key = value.strip().upper().replace("PARMTYPE", "")
    aliases = {
        "BOOL": ParmType.TOGGLE,
        "BOOLEAN": ParmType.TOGGLE,
        "INTEGER": ParmType.INT,
        "STR": ParmType.STRING,
        "VEC": ParmType.VECTOR,
        "VEC3": ParmType.VECTOR,
        "RGB": ParmType.COLOR,
        "RGBA": ParmType.COLOR,
    }
    if key in aliases:
        return aliases[key]
    return ParmType[key]


def round_number(value: float, digits: int = 6) -> float:
    rounded = round(float(value), digits)
    if rounded == int(rounded):
        return int(rounded)
    return rounded


def jsonify(value: Any) -> JsonValue:
    """Convert Houdini/Python values into JSON-safe, git-stable data."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return round_number(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): jsonify(v) for k, v in value.items()}
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [jsonify(v) for v in value]
    to_list = getattr(value, "to_list", None)
    if callable(to_list):
        return jsonify(to_list())
    if hasattr(value, "x") and hasattr(value, "y"):
        parts = [value.x, value.y]
        if hasattr(value, "z"):
            parts.append(value.z)
        if hasattr(value, "w"):
            parts.append(value.w)
        return jsonify(parts)
    name = getattr(value, "name", None)
    if callable(name):
        try:
            named = name()
        except TypeError:
            named = None
        if isinstance(named, str):
            return named
    if isinstance(name, str):
        return name
    return value


def is_parm_ref(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"ref"} and isinstance(value.get("ref"), str)


def is_parm_expr(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"expr"} and isinstance(value.get("expr"), str)
