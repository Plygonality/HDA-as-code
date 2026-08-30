from __future__ import annotations

import json

from hda_as_code import Network, dumps, from_dict, loads, to_dict
from hda_as_code.dump import fingerprint, to_mermaid
from hda_as_code.samples import build_column


def test_roundtrip_dict() -> None:
    network = build_column()
    payload = network.to_dict()
    restored = from_dict(payload)
    assert to_dict(restored) == payload


def test_dumps_is_stable() -> None:
    a = dumps(build_column().to_data())
    b = dumps(build_column().to_data())
    assert a == b
    json.loads(a)


def test_loads_roundtrip_text() -> None:
    text = build_column().dumps()
    assert dumps(loads(text)) == text


def test_fingerprint_ignores_layout() -> None:
    g = Network("A")
    g.box(id="box", location=(10, 20))
    other = Network("A")
    other.box(id="box", location=(99, -4))
    assert fingerprint(g.to_data()) == fingerprint(other.to_data())
    assert fingerprint(g.to_data(), include_layout=True) != fingerprint(
        other.to_data(), include_layout=True
    )


def test_canonical_node_order() -> None:
    n = Network("Order")
    b = n.grid(id="b")
    a = n.box(id="a")
    n.merge(a, b, id="join")
    ids = [node["id"] for node in n.to_dict()["nodes"]]
    assert ids == sorted(ids)


def test_mermaid_contains_nodes_and_edges() -> None:
    text = to_mermaid(build_column().to_data())
    assert text.startswith("flowchart LR")
    assert "shaft" in text
    assert "-->" in text
