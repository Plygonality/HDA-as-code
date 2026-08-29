from __future__ import annotations

from hda_as_code.catalog import CATALOG, CATALOG_BY_METHOD, CATALOG_BY_TYPE, get_spec


def test_catalog_ids_unique() -> None:
    types = [s.type for s in CATALOG]
    methods = [s.method for s in CATALOG]
    assert len(types) == len(set(types))
    assert len(methods) == len(set(methods))
    assert CATALOG_BY_TYPE["grid"].method == "grid"
    assert CATALOG_BY_METHOD["copytopoints"].type == "copytopoints"
    assert get_spec("copytopoints::2.0") is CATALOG_BY_TYPE["copytopoints"]
