from __future__ import annotations

from hda_as_code import Link, Network, NetworkData, Node, validate


def test_valid_network_has_no_errors() -> None:
    n = Network("Ok")
    n.box(id="box")
    assert validate(n.to_data()) == []


def test_dangling_link() -> None:
    n = Network("Bad")
    n.box(id="box")
    data = n.to_data()
    data.links.append(Link("missing", 0, "box", 0))
    codes = {e.code for e in validate(data)}
    assert "dangling_link" in codes


def test_unknown_display() -> None:
    n = Network("Bad")
    n.box(id="box")
    data = n.to_data()
    data.display = "nope"
    codes = {e.code for e in validate(data)}
    assert "unknown_display" in codes


def test_unknown_parm_on_catalog_node() -> None:
    data = NetworkData(
        name="Bad",
        nodes=[Node(id="box", type="box", parms={"not_a_parm": 1})],
        display="box",
    )
    codes = {e.code for e in validate(data)}
    assert "unknown_parm" in codes


def test_unknown_ref() -> None:
    n = Network("Bad")
    n.node("mountain", id="mountain", parms={"height": {"ref": "Missing"}})
    codes = {e.code for e in validate(n.to_data())}
    assert "unknown_ref" in codes


def test_invalid_menu_parm() -> None:
    n = Network("Bad")
    n.boolean(n.box(id="a"), n.box(id="b"), booleanop="not-an-op", id="bool")
    codes = {e.code for e in validate(n.to_data())}
    assert "invalid_parm" in codes
