"""Self-contained hou apply/dump runtime.

This module has no hda-as-code imports so it can be exec'd inside Houdini via
Plygon-mcp ``execute_houdini_code``. The network JSON is the source of truth;
the .hip is the cache.
"""

from __future__ import annotations

FORMAT = "hda-as-code"
FORMAT_VERSION = 1

_SKIP_PARMS = {
    "folder0",
    "folder1",
    "standardfolder",
    "stdswitcher",
}


def apply_network_dict(
    data,
    hou,
    *,
    parent_path=None,
    replace=True,
):
    """Rebuild a SOP network from an hda-as-code dump.

    Returns the parent geo or subnet. GEO networks land at ``/obj/<name>``.
    SUBNET networks are created under ``parent_path`` (default ``/obj``).
    """
    _validate_payload(data)
    name = data["name"]
    kind = data.get("kind", "GEO")
    parent = _resolve_parent(hou, kind, name, parent_path, replace)
    _apply_interface(hou, parent, data.get("interface") or {})
    created = _build_nodes(parent, data.get("nodes") or [])
    _build_links(created, data.get("links") or [])
    display = data.get("display")
    if display and display in created:
        created[display].setDisplayFlag(True)
        if hasattr(created[display], "setRenderFlag"):
            created[display].setRenderFlag(True)
    return parent


def dump_network(node, *, houdini="20.5"):
    """Serialize a live geo or SOP subnet into an hda-as-code dict."""
    kind = "GEO"
    host = node
    children = _sop_children(node)
    type_name = _type_name(node)
    if type_name == "subnet":
        kind = "SUBNET"
    elif type_name not in ("geo", "objnet") and children == [] and node.parent() is not None:
        # Dumping a SOP: use its parent as the host.
        host = node.parent()
        children = _sop_children(host)
        type_name = _type_name(host)
        kind = "SUBNET" if type_name == "subnet" else "GEO"

    nodes = [_dump_node(child) for child in children]
    links = []
    for child in children:
        links.extend(_dump_links(child))
    display = None
    for child in children:
        if _is_display(child):
            display = child.name()
            break
    nodes_sorted = sorted(nodes, key=lambda n: n["id"])
    links_sorted = sorted(
        links,
        key=lambda ln: (ln["from"][0], ln["from"][1], ln["to"][0], ln["to"][1]),
    )
    payload = {
        "format": FORMAT,
        "version": FORMAT_VERSION,
        "name": host.name(),
        "kind": kind,
        "houdini": houdini,
        "interface": {"parms": _dump_interface(host)},
        "nodes": nodes_sorted,
        "links": links_sorted,
    }
    if display:
        payload["display"] = display
    return payload


def dump_network_by_path(hou, path, *, houdini="20.5"):
    node = hou.node(path)
    if node is None:
        raise KeyError(f"No node at {path!r}")
    return dump_network(node, houdini=houdini)


def _validate_payload(data):
    if data.get("format") not in (None, FORMAT):
        raise ValueError(f"Unsupported network format: {data.get('format')!r}")
    version = data.get("version", FORMAT_VERSION)
    if int(version) != FORMAT_VERSION:
        raise ValueError(f"Unsupported hda-as-code version: {version}")
    if "name" not in data:
        raise ValueError("Network dump is missing 'name'")


def _resolve_parent(hou, kind, name, parent_path, replace):
    if kind == "SUBNET":
        root = hou.node(parent_path or "/obj")
        if root is None:
            raise KeyError(f"Parent path not found: {parent_path or '/obj'}")
        existing = root.node(name)
        if existing is not None:
            if not replace:
                raise ValueError(f"Node {existing.path()!r} already exists")
            _clear_children(existing)
            return existing
        return root.createNode("subnet", node_name=name)
    obj = hou.node("/obj")
    if obj is None:
        raise RuntimeError("/obj context not found")
    existing = obj.node(name)
    if existing is not None:
        if not replace:
            raise ValueError(f"Node {existing.path()!r} already exists")
        _clear_children(existing)
        return existing
    return obj.createNode("geo", node_name=name)


def _clear_children(parent):
    for child in list(parent.children()):
        try:
            child.destroy()
        except Exception:
            pass


def _apply_interface(hou, parent, interface):
    items = interface.get("parms") or interface.get("inputs") or []
    if not items:
        return
    templates = []
    for item in items:
        template = _make_template(hou, item)
        if template is not None:
            templates.append(template)
    if not templates:
        return
    group = parent.parmTemplateGroup()
    for template in templates:
        try:
            group.append(template)
        except Exception:
            pass
    try:
        parent.setParmTemplateGroup(group)
    except Exception:
        pass
    if hasattr(parent, "mark_spare"):
        for item in items:
            parent.mark_spare(item["name"])
    for item in items:
        if item.get("default") is None:
            continue
        _set_parm_value(parent, item["name"], item["default"])


def _make_template(hou, item):
    name = item["name"]
    label = item.get("label") or name
    ptype = item.get("type", "FLOAT")
    default = item.get("default")
    min_v = item.get("min")
    max_v = item.get("max")
    kwargs = {}
    if min_v is not None:
        kwargs["min"] = min_v
        kwargs["min_is_strict"] = False
    if max_v is not None:
        kwargs["max"] = max_v
        kwargs["max_is_strict"] = False
    try:
        if ptype == "FLOAT":
            return hou.FloatParmTemplate(name, label, 1, default_value=(_as_tuple(default, 0.0, 1)))
        if ptype == "INT":
            return hou.IntParmTemplate(name, label, 1, default_value=(_as_tuple(default, 0, 1)))
        if ptype == "TOGGLE":
            return hou.ToggleParmTemplate(name, label, default_value=bool(default))
        if ptype == "STRING":
            return hou.StringParmTemplate(name, label, 1, default_value=(_as_tuple(default, "", 1)))
        if ptype == "VECTOR":
            return hou.FloatParmTemplate(
                name,
                label,
                3,
                default_value=_as_tuple(default, 0.0, 3),
                naming_scheme=getattr(hou.parmNamingScheme, "XYZ", None) or 0,
            )
        if ptype == "INT3":
            return hou.IntParmTemplate(name, label, 3, default_value=_as_tuple(default, 0, 3))
        if ptype == "COLOR":
            return hou.FloatParmTemplate(
                name,
                label,
                3,
                default_value=_as_tuple(default, 1.0, 3),
                look=getattr(hou.parmLook, "ColorSquare", None) or 0,
            )
        if ptype == "MENU":
            menu = list(item.get("menu") or ())
            return hou.MenuParmTemplate(name, label, menu_items=menu, default_value=0)
    except TypeError:
        # Fake hou / slim hou stubs may not accept every kwarg.
        try:
            if ptype in ("FLOAT", "VECTOR", "COLOR"):
                num = 3 if ptype in ("VECTOR", "COLOR") else 1
                return hou.FloatParmTemplate(name, label, num)
            if ptype in ("INT", "INT3"):
                return hou.IntParmTemplate(name, label, 3 if ptype == "INT3" else 1)
            if ptype == "TOGGLE":
                return hou.ToggleParmTemplate(name, label)
            if ptype == "STRING":
                return hou.StringParmTemplate(name, label, 1)
            if ptype == "MENU":
                return hou.MenuParmTemplate(name, label, menu_items=list(item.get("menu") or ()))
        except Exception:
            return None
    return None


def _as_tuple(value, fill, size):
    if value is None:
        return tuple(fill for _ in range(size))
    if isinstance(value, (list, tuple)):
        values = list(value)[:size]
        while len(values) < size:
            values.append(fill)
        return tuple(values)
    return (value,) + tuple(fill for _ in range(size - 1))


def _build_nodes(parent, nodes):
    created = {}
    for spec in nodes:
        node = parent.createNode(spec["type"], node_name=spec["id"])
        if spec.get("label"):
            comment = spec.get("comment") or ""
            try:
                node.setComment(spec["label"] if not comment else f"{spec['label']}\n{comment}")
            except Exception:
                pass
        elif spec.get("comment"):
            try:
                node.setComment(spec["comment"])
            except Exception:
                pass
        if spec.get("bypass"):
            try:
                node.bypass(True)
            except Exception:
                pass
        if spec.get("location") is not None:
            try:
                node.setPosition([float(spec["location"][0]), float(spec["location"][1])])
            except Exception:
                pass
        if spec.get("color") is not None:
            try:
                color = spec["color"]
                node.setColor(parent.__class__ and __import__("hou").Color(color))
            except Exception:
                try:
                    node.setColor(spec["color"])
                except Exception:
                    pass
        for key, value in (spec.get("parms") or {}).items():
            _set_recorded_parm(node, key, value)
        created[spec["id"]] = node
    return created


def _build_links(created, links):
    for spec in links:
        src_id, src_out = spec["from"]
        dst_id, dst_in = spec["to"]
        src = created.get(src_id)
        dst = created.get(dst_id)
        if src is None or dst is None:
            raise KeyError(f"Link references missing node: {src_id!r} -> {dst_id!r}")
        dst.setInput(int(dst_in), src, int(src_out))


def _set_recorded_parm(node, name, value):
    if isinstance(value, dict) and "ref" in value:
        _set_channel_ref(node, name, value["ref"])
        return
    if isinstance(value, dict) and "expr" in value:
        _set_expression(node, name, value["expr"])
        return
    _set_parm_value(node, name, value)


def _set_parm_value(node, name, value):
    if isinstance(value, (list, tuple)):
        ptuple = node.parmTuple(name)
        if ptuple is not None:
            try:
                ptuple.set(list(value))
                return
            except Exception:
                pass
    parm = node.parm(name)
    if parm is not None:
        try:
            parm.set(value)
            return
        except Exception:
            pass
    if hasattr(node, "ensure_parm"):
        node.ensure_parm(name, value)


def _set_channel_ref(node, name, ref):
    ptuple = node.parmTuple(name)
    if ptuple is not None and len(list(ptuple)) > 1:
        suffixes = "xyzw"
        for i, parm in enumerate(ptuple):
            suffix = suffixes[i] if i < len(suffixes) else str(i + 1)
            _set_expression(node, parm.name() if callable(getattr(parm, "name", None)) else name + suffix, f'ch("../{ref}{suffix}")')
        return
    _set_expression(node, name, f'ch("../{ref}")')


def _set_expression(node, name, expr):
    parm = node.parm(name)
    if parm is None and hasattr(node, "ensure_parm"):
        node.ensure_parm(name, 0)
        parm = node.parm(name)
    if parm is None:
        return
    try:
        parm.setExpression(expr)
    except TypeError:
        parm.setExpression(expr, language=None)
    except Exception:
        try:
            parm.set(expr)
        except Exception:
            pass


def _sop_children(node):
    children = []
    for child in node.children():
        category = _category_name(child)
        if category in ("Sop", "sop", ""):
            children.append(child)
        elif not category:
            children.append(child)
    return children or list(node.children())


def _dump_node(node):
    payload = {
        "id": node.name(),
        "type": _type_name(node),
    }
    comment = ""
    try:
        comment = node.comment() or ""
    except Exception:
        pass
    if comment:
        payload["comment"] = comment
    try:
        if node.isBypassed():
            payload["bypass"] = True
    except Exception:
        pass
    try:
        pos = node.position()
        payload["location"] = [_jsonify(pos[0]), _jsonify(pos[1])]
    except Exception:
        pass
    try:
        color = node.color()
        rgb = color.rgb() if hasattr(color, "rgb") else color
        payload["color"] = [_jsonify(rgb[0]), _jsonify(rgb[1]), _jsonify(rgb[2])]
    except Exception:
        pass
    parms = _dump_parms(node)
    if parms:
        payload["parms"] = parms
    return payload


def _dump_parms(node):
    parms = {}
    tuples = []
    try:
        tuples = list(node.parmTuples())
    except Exception:
        tuples = []
    if tuples:
        for ptuple in tuples:
            name = _call(ptuple, "name")
            if not name or name in _SKIP_PARMS:
                continue
            dumped = _dump_parm_tuple(ptuple)
            if isinstance(dumped, dict) and dumped.get("__components__"):
                for key, value in dumped["__components__"].items():
                    parms[key] = value
            elif dumped is not None:
                parms[name] = dumped
        return parms
    try:
        raw = node.parms()
    except Exception:
        raw = []
    for parm in raw:
        name = _call(parm, "name")
        if not name:
            continue
        dumped = _dump_one_parm(parm)
        if dumped is not None:
            parms[name] = dumped
    return parms


def _dump_parm_tuple(ptuple):
    components = list(ptuple)
    if not components:
        return None
    if any(_has_expression(p) for p in components):
        if len(components) == 1:
            return _dump_one_parm(components[0])
        refs = [_parse_channel_ref(_expression(p)) if _has_expression(p) else None for p in components]
        if all(refs) and _same_vector_ref(refs):
            return {"ref": _same_vector_ref(refs)}
        result = {}
        for parm in components:
            dumped = _dump_one_parm(parm)
            if dumped is not None:
                result[_call(parm, "name")] = dumped
        if not result:
            return None
        return {"__components__": result}
    if all(_is_at_default(p) for p in components):
        return None
    if len(components) == 1:
        return _jsonify(_eval(components[0]))
    return [_jsonify(_eval(p)) for p in components]


def _same_vector_ref(refs):
    suffixes = "xyzw"
    bases = []
    for i, ref in enumerate(refs):
        suffix = suffixes[i] if i < len(suffixes) else str(i + 1)
        if ref.endswith(suffix):
            bases.append(ref[: -len(suffix)])
        else:
            return None
    if bases and all(b == bases[0] and b for b in bases):
        return bases[0]
    return None


def _dump_one_parm(parm):
    if _has_expression(parm):
        expr = _expression(parm)
        ref = _parse_channel_ref(expr)
        if ref:
            return {"ref": ref}
        return {"expr": expr}
    if _is_at_default(parm):
        return None
    return _jsonify(_eval(parm))


def _dump_links(node):
    links = []
    try:
        connections = node.inputConnections()
    except Exception:
        connections = []
        try:
            for index, src in enumerate(node.inputs()):
                if src is not None:
                    links.append({"from": [src.name(), 0], "to": [node.name(), index]})
            return links
        except Exception:
            return links
    for conn in connections:
        try:
            src = conn.inputNode()
            if src is None:
                continue
            links.append(
                {
                    "from": [src.name(), int(conn.outputIndex())],
                    "to": [node.name(), int(conn.inputIndex())],
                }
            )
        except Exception:
            continue
    return links


def _dump_interface(node):
    items = []
    spare = []
    try:
        spare = list(node.spareParms())
    except Exception:
        spare = []
    if not spare and hasattr(node, "interface_items"):
        return list(node.interface_items())
    seen = set()
    for parm in spare:
        name = _call(parm, "name")
        ptuple = None
        try:
            ptuple = parm.tuple()
        except Exception:
            ptuple = None
        tuple_name = _call(ptuple, "name") if ptuple is not None else name
        if tuple_name in seen:
            continue
        seen.add(tuple_name)
        item = {"name": tuple_name, "type": _parm_kind(parm, ptuple)}
        default = _jsonify(_eval(ptuple if ptuple is not None and len(list(ptuple)) > 1 else parm))
        if default is not None:
            item["default"] = default
        items.append(item)
    return items


def _parm_kind(parm, ptuple):
    size = 1
    if ptuple is not None:
        try:
            size = len(list(ptuple))
        except Exception:
            size = 1
    name = _call(parm, "name") or ""
    if size == 3 and name[:1].lower() in "rgb":
        return "COLOR"
    if size == 3:
        return "VECTOR"
    try:
        value = _eval(parm)
    except Exception:
        value = None
    if isinstance(value, bool):
        return "TOGGLE"
    if isinstance(value, int) and not isinstance(value, bool):
        return "INT"
    if isinstance(value, str):
        return "STRING"
    return "FLOAT"


def _type_name(node):
    try:
        return node.type().name()
    except Exception:
        return getattr(node, "type_name", node.name())


def _category_name(node):
    try:
        return node.type().category().name()
    except Exception:
        return getattr(node, "category", "Sop")


def _is_display(node):
    try:
        return bool(node.isDisplayFlagSet())
    except Exception:
        return False


def _has_expression(parm):
    try:
        return bool(parm.expression())
    except Exception:
        return False


def _expression(parm):
    try:
        return parm.expression()
    except Exception:
        return ""


def _is_at_default(parm):
    try:
        return bool(parm.isAtDefault())
    except Exception:
        return False


def _eval(parm):
    try:
        return parm.eval()
    except Exception:
        return None


def _call(obj, method):
    if obj is None:
        return None
    attr = getattr(obj, method, None)
    if callable(attr):
        try:
            return attr()
        except Exception:
            return None
    return attr


def _parse_channel_ref(expr):
    text = (expr or "").strip()
    if text.startswith('ch("../') and text.endswith('")') and "/" not in text[7:-2]:
        return text[7:-2]
    return None


def _jsonify(value):
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        rounded = round(float(value), 6)
        return int(rounded) if rounded == int(rounded) else rounded
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if hasattr(value, "x") and hasattr(value, "y"):
        parts = [value.x, value.y]
        if hasattr(value, "z"):
            parts.append(value.z)
        return _jsonify(parts)
    name = getattr(value, "name", None)
    if callable(name):
        try:
            named = name()
        except Exception:
            named = None
        if isinstance(named, str):
            return named
    if isinstance(name, str):
        return name
    return None
