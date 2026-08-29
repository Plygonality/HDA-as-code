"""Minimal in-memory hou stand-in for apply/dump tests."""

from __future__ import annotations

from typing import Any


class FakeColor:
    def __init__(self, rgb: Any = (0.8, 0.8, 0.8)) -> None:
        if hasattr(rgb, "rgb"):
            rgb = rgb.rgb()
        self._rgb = tuple(float(c) for c in rgb[:3])

    def rgb(self) -> tuple[float, float, float]:
        return self._rgb


class FakeParm:
    def __init__(self, name: str, value: Any = None, owner: FakeNode | None = None) -> None:
        self._name = name
        self._value = value
        self._default = value
        self._expr: str | None = None
        self._owner = owner
        self._tuple: FakeParmTuple | None = None
        self._spare = False

    def name(self) -> str:
        return self._name

    def set(self, value: Any) -> None:
        self._value = value
        self._expr = None

    def eval(self) -> Any:
        return self._value

    def setExpression(self, expr: str, language: Any = None) -> None:
        self._expr = expr

    def expression(self) -> str:
        return self._expr or ""

    def isAtDefault(self) -> bool:
        return self._expr is None and self._value == self._default

    def tuple(self) -> FakeParmTuple | None:
        return self._tuple


class FakeParmTuple:
    def __init__(self, name: str, values: list[Any], owner: FakeNode | None = None) -> None:
        self._name = name
        suffixes = "xyzw" if len(values) <= 4 else [str(i + 1) for i in range(len(values))]
        self._parms = [FakeParm(f"{name}{suffixes[i]}", values[i], owner) for i in range(len(values))]
        for parm in self._parms:
            parm._tuple = self
        self._owner = owner

    def name(self) -> str:
        return self._name

    def set(self, values: Any) -> None:
        for parm, value in zip(self._parms, list(values), strict=False):
            parm.set(value)

    def eval(self) -> tuple[Any, ...]:
        return tuple(p.eval() for p in self._parms)

    def __iter__(self):
        return iter(self._parms)

    def __len__(self) -> int:
        return len(self._parms)


class FakeType:
    def __init__(self, name: str, category: str = "Sop") -> None:
        self._name = name
        self._category = category

    def name(self) -> str:
        return self._name

    def category(self) -> FakeCategory:
        return FakeCategory(self._category)


class FakeCategory:
    def __init__(self, name: str) -> None:
        self._name = name

    def name(self) -> str:
        return self._name


class FakeParmTemplate:
    def __init__(self, name: str, label: str, num: int = 1, **kwargs: Any) -> None:
        self.name = name
        self.label = label
        self.num = num
        self.kwargs = kwargs


class FakeParmTemplateGroup:
    def __init__(self) -> None:
        self.templates: list[FakeParmTemplate] = []

    def append(self, template: FakeParmTemplate) -> None:
        self.templates.append(template)


class FakeConnection:
    def __init__(self, src: FakeNode, output_index: int, dst: FakeNode, input_index: int) -> None:
        self._src = src
        self._output = output_index
        self._dst = dst
        self._input = input_index

    def inputNode(self) -> FakeNode:
        return self._src

    def outputIndex(self) -> int:
        return self._output

    def inputIndex(self) -> int:
        return self._input


class FakeNode:
    def __init__(self, name: str, type_name: str, parent: FakeNode | None, hou: FakeHou) -> None:
        self._name = name
        self._type = type_name
        self._parent = parent
        self._hou = hou
        self._children: dict[str, FakeNode] = {}
        self._inputs: dict[int, tuple[FakeNode, int]] = {}
        self._parms: dict[str, FakeParm] = {}
        self._tuples: dict[str, FakeParmTuple] = {}
        self._spare_names: set[str] = set()
        self._display = False
        self._render = False
        self._bypass = False
        self._comment = ""
        self._position = [0.0, 0.0]
        self._color = FakeColor()
        self._template_group = FakeParmTemplateGroup()
        self.category = "Sop" if type_name not in {"obj", "geo", "subnet"} else (
            "Object" if type_name in {"obj", "geo"} else "Sop"
        )
        if type_name == "obj":
            self.category = "Object"
        hou._index[self.path()] = self
        self._seed_catalog_parms()

    def name(self) -> str:
        return self._name

    def path(self) -> str:
        if self._parent is None:
            return "/" if self._name in {"", "/"} else f"/{self._name}"
        parent_path = self._parent.path()
        if parent_path == "/":
            return f"/{self._name}"
        return f"{parent_path}/{self._name}"

    def parent(self) -> FakeNode | None:
        return self._parent

    def type(self) -> FakeType:
        category = "Object" if self._type in {"obj", "geo"} else "Sop"
        return FakeType(self._type, category)

    def children(self) -> list[FakeNode]:
        return list(self._children.values())

    def node(self, name: str) -> FakeNode | None:
        if name.startswith("/"):
            return self._hou.node(name)
        return self._children.get(name)

    def createNode(self, type_name: str, node_name: str = "") -> FakeNode:
        base = node_name or type_name.split("::", 1)[0]
        name = base
        n = 1
        while name in self._children:
            n += 1
            name = f"{base}{n}"
        child = FakeNode(name, type_name, self, self._hou)
        self._children[name] = child
        return child

    def destroy(self) -> None:
        self._hou._index.pop(self.path(), None)
        if self._parent is not None:
            self._parent._children.pop(self._name, None)

    def setInput(self, index: int, src: FakeNode | None, output_index: int = 0) -> None:
        if src is None:
            self._inputs.pop(int(index), None)
            return
        self._inputs[int(index)] = (src, int(output_index))

    def inputs(self) -> list[FakeNode | None]:
        if not self._inputs:
            return []
        size = max(self._inputs) + 1
        result: list[FakeNode | None] = [None] * size
        for index, (src, _) in self._inputs.items():
            result[index] = src
        return result

    def inputConnections(self) -> list[FakeConnection]:
        return [
            FakeConnection(src, output, self, index)
            for index, (src, output) in sorted(self._inputs.items())
        ]

    def setDisplayFlag(self, value: bool) -> None:
        if value and self._parent is not None:
            for sibling in self._parent._children.values():
                sibling._display = False
        self._display = bool(value)

    def isDisplayFlagSet(self) -> bool:
        return self._display

    def setRenderFlag(self, value: bool) -> None:
        self._render = bool(value)

    def bypass(self, value: bool) -> None:
        self._bypass = bool(value)

    def isBypassed(self) -> bool:
        return self._bypass

    def setPosition(self, pos: Any) -> None:
        self._position = [float(pos[0]), float(pos[1])]

    def position(self) -> list[float]:
        return list(self._position)

    def setComment(self, text: str) -> None:
        self._comment = text

    def comment(self) -> str:
        return self._comment

    def setColor(self, color: Any) -> None:
        self._color = FakeColor(color)

    def color(self) -> FakeColor:
        return self._color

    def parm(self, name: str) -> FakeParm | None:
        if name in self._parms:
            return self._parms[name]
        for ptuple in self._tuples.values():
            for parm in ptuple:
                if parm.name() == name:
                    return parm
        return None

    def parmTuple(self, name: str) -> FakeParmTuple | None:
        if name in self._tuples:
            return self._tuples[name]
        if name in self._parms:
            return FakeParmTuple(name, [self._parms[name].eval()], self)
        return None

    def parms(self) -> list[FakeParm]:
        result = list(self._parms.values())
        for ptuple in self._tuples.values():
            result.extend(list(ptuple))
        return result

    def parmTuples(self) -> list[FakeParmTuple]:
        result = list(self._tuples.values())
        for parm in self._parms.values():
            wrapper = FakeParmTuple(parm.name(), [parm.eval()], self)
            wrapper._parms = [parm]
            parm._tuple = wrapper
            result.append(wrapper)
        return result

    def spareParms(self) -> list[FakeParm]:
        result = []
        for name in self._spare_names:
            if name in self._tuples:
                result.extend(list(self._tuples[name]))
            elif name in self._parms:
                result.append(self._parms[name])
        return result

    def parmTemplateGroup(self) -> FakeParmTemplateGroup:
        return self._template_group

    def setParmTemplateGroup(self, group: FakeParmTemplateGroup) -> None:
        self._template_group = group
        for template in group.templates:
            self._install_template(template)

    def mark_spare(self, name: str) -> None:
        self._spare_names.add(name)

    def ensure_parm(self, name: str, value: Any) -> FakeParm:
        if name not in self._parms:
            self._parms[name] = FakeParm(name, value, self)
        return self._parms[name]

    def interface_items(self) -> list[dict[str, Any]]:
        items = []
        for name in sorted(self._spare_names):
            if name in self._tuples:
                values = list(self._tuples[name].eval())
                items.append(
                    {
                        "name": name,
                        "type": "VECTOR" if len(values) == 3 else "FLOAT",
                        "default": values if len(values) > 1 else values[0],
                    }
                )
            elif name in self._parms:
                value = self._parms[name].eval()
                kind = "TOGGLE" if isinstance(value, bool) else (
                    "INT" if isinstance(value, int) and not isinstance(value, bool) else (
                        "STRING" if isinstance(value, str) else "FLOAT"
                    )
                )
                items.append({"name": name, "type": kind, "default": value})
        return items

    def _install_template(self, template: FakeParmTemplate) -> None:
        num = getattr(template, "num", 1)
        default = (template.kwargs or {}).get("default_value")
        if num > 1:
            values = list(default) if default is not None else [0] * num
            self._tuples[template.name] = FakeParmTuple(template.name, values, self)
        else:
            value = default[0] if isinstance(default, (list, tuple)) and default else (
                default if default is not None else 0
            )
            self._parms[template.name] = FakeParm(template.name, value, self)
        self._spare_names.add(template.name)

    def _seed_catalog_parms(self) -> None:
        from hda_as_code.catalog import get_spec
        from hda_as_code.types import ParmType

        spec = get_spec(self._type)
        if spec is None:
            return
        for parm in spec.parms:
            default = parm.default
            if parm.parm_type in (ParmType.VECTOR, ParmType.INT3, ParmType.COLOR):
                values = list(default) if isinstance(default, (list, tuple)) else [0, 0, 0]
                self._tuples[parm.name] = FakeParmTuple(parm.name, values, self)
            else:
                self._parms[parm.name] = FakeParm(parm.name, default, self)


class FakeHou:
    def __init__(self) -> None:
        self._index: dict[str, FakeNode] = {}
        self.root = FakeNode("", "root", None, self)
        self._index["/"] = self.root
        self.obj = self.root.createNode("obj", node_name="obj")
        self.parmNamingScheme = type("NS", (), {"XYZ": "xyz"})()
        self.parmLook = type("PL", (), {"ColorSquare": "color"})()
        self.Color = FakeColor
        self.FloatParmTemplate = FakeParmTemplate
        self.IntParmTemplate = FakeParmTemplate
        self.ToggleParmTemplate = FakeParmTemplate
        self.StringParmTemplate = FakeParmTemplate
        self.MenuParmTemplate = FakeParmTemplate

    def node(self, path: str) -> FakeNode | None:
        if not path:
            return None
        if path == "/":
            return self.root
        return self._index.get(path.rstrip("/") or "/")
