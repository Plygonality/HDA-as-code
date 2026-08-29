from __future__ import annotations

from hda_as_code import Network, ParmType, validate
from hda_as_code.samples import build_column, build_scatter, build_terrain


def test_grid_to_mountain_wires_input() -> None:
    n = Network("Terrain")
    grid = n.grid(rows=40, sizex=8, id="grid")
    n.mountain(grid, height=2.0, id="mountain")
    data = n.to_data()
    assert data.name == "Terrain"
    assert {node.id for node in data.nodes} >= {"grid", "mountain"}
    links = {(ln.from_node, ln.from_output, ln.to_node, ln.to_input) for ln in data.links}
    assert ("grid", 0, "mountain", 0) in links
    node = data.node_map()["grid"]
    assert node.parms["rows"] == 40
    assert node.parms["sizex"] == 8
    assert "cols" not in node.parms
    assert data.display == "mountain"
    assert validate(data) == []


def test_parm_ref_is_channel_binding() -> None:
    n = Network("Sized")
    height = n.parm_float("Height", 2.0)
    box = n.box(size=[1, height, 1], id="box")
    data = n.to_data()
    assert data.interface[0].name == "Height"
    assert data.interface[0].type == ParmType.FLOAT
    assert data.node_map()["box"].parms["sizey"] == {"ref": "Height"}
    assert box.id == "box"


def test_merge_multi_input() -> None:
    n = Network("Join")
    a = n.box(id="a")
    b = n.grid(id="b")
    n.merge(a, b, id="join")
    data = n.to_data()
    to_join = [ln for ln in data.links if ln.to_node == "join"]
    assert len(to_join) == 2
    assert {ln.to_input for ln in to_join} == {0, 1}


def test_duplicate_ids_get_suffix() -> None:
    n = Network("Dup")
    n.box(id="box")
    second = n.box(id="box")
    assert second.id == "box_2"


def test_handle_output_index() -> None:
    n = Network("Out")
    box = n.box(id="box")
    assert box.out(0).node == "box"
    assert box[0].output == 0
    n.null(box, id="out")
    data = n.to_data()
    assert data.links[0].from_output == 0


def test_samples_validate() -> None:
    for build in (build_column, build_scatter, build_terrain):
        errors = validate(build().to_data())
        assert errors == [], errors
