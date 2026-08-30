from __future__ import annotations

from hda_as_code.apply import apply, dump_from_hou, to_apply_script, to_dump_script
from hda_as_code.samples import build_column, build_scatter, build_terrain
from tests.fake_hou import FakeHou


def _ids(parent) -> set[str]:
    return {child.name() for child in parent.children()}


def _link_keys(parent) -> set[tuple[str, int, str, int]]:
    keys = set()
    for child in parent.children():
        for conn in child.inputConnections():
            keys.add(
                (
                    conn.inputNode().name(),
                    conn.outputIndex(),
                    child.name(),
                    conn.inputIndex(),
                )
            )
    return keys


def test_apply_terrain_creates_nodes_and_links() -> None:
    hou = FakeHou()
    network = build_terrain().to_data()
    parent = apply(network, hou=hou)
    assert parent.name() == "Terrain"
    assert parent.path() == "/obj/Terrain"
    assert "grid" in _ids(parent)
    assert "mountain" in _ids(parent)
    keys = _link_keys(parent)
    assert ("grid", 0, "mountain", 0) in keys
    assert ("mountain", 0, "normals", 0) in keys
    assert parent.node("normals").isDisplayFlagSet()


def test_apply_then_dump_preserves_topology() -> None:
    hou = FakeHou()
    original = build_scatter().to_data()
    parent = apply(original, hou=hou)
    dumped = dump_from_hou(parent)
    assert dumped["name"] == original.name
    assert dumped["format"] == "hda-as-code"
    orig_ids = {n.id for n in original.nodes}
    dump_ids = {n["id"] for n in dumped["nodes"]}
    assert orig_ids == dump_ids
    orig_links = {(ln.from_node, ln.from_output, ln.to_node, ln.to_input) for ln in original.links}
    dump_links = {(ln["from"][0], ln["from"][1], ln["to"][0], ln["to"][1]) for ln in dumped["links"]}
    assert orig_links == dump_links
    rebuilt = apply(dumped, hou=FakeHou())
    assert _link_keys(rebuilt) == _link_keys(parent)


def test_apply_column_binds_interface_refs() -> None:
    hou = FakeHou()
    parent = apply(build_column().to_data(), hou=hou)
    shaft = parent.node("shaft")
    assert shaft.parm("sizex").expression() == 'ch("../Width")'
    assert shaft.parm("sizey").expression() == 'ch("../Height")'
    dumped = dump_from_hou(parent)
    shaft_dump = next(n for n in dumped["nodes"] if n["id"] == "shaft")
    assert shaft_dump["parms"]["sizex"] == {"ref": "Width"}
    interface_names = {item["name"] for item in dumped["interface"]["parms"]}
    assert {"Height", "Width", "Plinth"} <= interface_names


def test_apply_script_is_executable_python() -> None:
    script = to_apply_script(build_terrain().to_data())
    compile(script, "<apply>", "exec")
    assert "apply_network_dict" in script
    assert '"name": "Terrain"' in script
    dump_script = to_dump_script("/obj/Terrain")
    compile(dump_script, "<dump>", "exec")
    assert "dump_network_by_path" in dump_script
