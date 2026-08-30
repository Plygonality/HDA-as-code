from __future__ import annotations

from hda_as_code import Network, diff_networks, format_diff
from hda_as_code.samples import build_column


def test_identical_networks_empty_diff() -> None:
    a = build_column().to_data()
    b = build_column().to_data()
    diff = diff_networks(a, b)
    assert diff.is_empty()
    assert format_diff(diff) == "No differences.\n"


def test_added_and_removed_nodes() -> None:
    old = Network("G")
    old.box(id="box")
    new = Network("G")
    new.grid(id="grid")
    diff = diff_networks(old.to_data(), new.to_data())
    assert [n["id"] for n in diff.nodes_added] == ["grid"]
    assert [n["id"] for n in diff.nodes_removed] == ["box"]
    assert "+ node grid" in format_diff(diff)


def test_changed_parm_and_link() -> None:
    old = Network("G")
    old.box(size=(2, 3, 4), id="box")
    new = Network("G")
    height = new.parm_float("Height", 2.0)
    new.box(size=[1, height, 1], id="box")
    diff = diff_networks(old.to_data(), new.to_data())
    assert diff.interface is not None
    changed_ids = [c.id for c in diff.nodes_changed]
    assert "box" in changed_ids


def test_layout_ignored_by_default() -> None:
    a = Network("G")
    a.box(id="box", location=(0, 0))
    b = Network("G")
    b.box(id="box", location=(4, 1))
    assert diff_networks(a.to_data(autolayout=False), b.to_data(autolayout=False)).is_empty()
    diff = diff_networks(
        a.to_data(autolayout=False),
        b.to_data(autolayout=False),
        include_layout=True,
    )
    assert not diff.is_empty()
    assert any(c.id == "box" for c in diff.nodes_changed)
