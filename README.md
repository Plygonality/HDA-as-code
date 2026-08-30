# HDA-as-code

SOP network fragments as data. Git is the source of truth. The `.hip` is a cache.

Build chains in Python. Dump them to JSON. Diff them like code.
[Plygon-mcp](https://github.com/Plygonality/Plygon-mcp) applies a network and screenshots the viewport.

This is the Houdini sibling of [gn-as-code](https://github.com/Plygonality/gn-as-code). Smaller surface than full HDA binary management — start with the SOP chains you actually use.

This is a library you import, not another `execute_houdini_code` wrapper.

```python
from pathlib import Path

from hda_as_code import Network

n = Network("Terrain")
height = n.parm_float("Height", 1.0)
grid = n.grid(rows=80, cols=80, sizex=10, sizey=10)
n.mountain(grid, height=height, elementsize=2.0)

Path("networks/terrain.json").write_text(n.dumps())
```

## Why this repo exists

An HDA is a binary blob. A SOP chain inside a `.hip` is not reviewable either. You cannot diff it, or let an agent iterate on it, without opening Houdini.

| Role | Job |
|---|---|
| **This library** | Typed builders, canonical JSON, structural diffs, golden tests |
| **Plygon-mcp** | Apply the JSON in a live Houdini session and check the viewport |
| **The `.hip`** | Working cache, never the source of truth |

Spare parms on the parent geo are the HDA-lite interface. Channel references (`ch("../Height")`) bind them to node parms. Full `.hda` packaging can come later.

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. No Houdini required to build, dump, or diff.

## Quick demo

```bash
pip install -e ".[dev]"
python -c "from hda_as_code.samples import build_terrain; print(build_terrain().dumps())"
pytest -q
```

That prints one shipped sample as canonical JSON, then runs the suite.

## Network JSON

Dumps are stable: nodes sorted by id, links sorted, defaults omitted, locations rounded.

```json
{
  "format": "hda-as-code",
  "version": 1,
  "name": "Terrain",
  "kind": "GEO",
  "houdini": "20.5",
  "interface": {
    "parms": [{"name": "Height", "type": "FLOAT", "default": 1.0}]
  },
  "nodes": [
    {"id": "grid", "type": "grid", "parms": {"rows": 80, "cols": 80, "sizex": 10, "sizey": 10}},
    {"id": "mountain", "type": "mountain", "parms": {"height": {"ref": "Height"}, "elementsize": 2}}
  ],
  "links": [
    {"from": ["grid", 0], "to": ["mountain", 0]}
  ],
  "display": "mountain"
}
```

`id` is the stable node name. Rename nodes in the builder, not in Houdini, so diffs stay readable.

`kind` is `GEO` (`/obj/<name>`) or `SUBNET` (a SOP subnet — the step toward an HDA).

A parm value is a literal, `{"ref": "Height"}` (spare-parm channel reference), or `{"expr": "$F * 0.1"}`.

## Diff

```python
from hda_as_code import diff_networks, format_diff, loads

diff = diff_networks(loads(old_json), loads(new_json))
print(format_diff(diff))
```

Locations are ignored unless you pass `include_layout=True`.

```bash
hda-as-code dump network.json
hda-as-code diff old.json new.json
hda-as-code validate network.json
hda-as-code mermaid network.json
hda-as-code apply-script network.json
hda-as-code dump-script /obj/Terrain
```

## Apply in Houdini (via Plygon-mcp)

The agent authors a network here, then asks Plygon-mcp to run a self-contained hou script. Houdini does not need this package installed.

```python
from hda_as_code.apply import to_apply_script
from hda_as_code.samples import build_terrain

script = to_apply_script(build_terrain().to_data())
# Plygon-mcp: execute_houdini_code(script) → get_viewport_screenshot()
```

Dump a live network the other way:

```python
from hda_as_code.apply import to_dump_script

script = to_dump_script("/obj/Terrain")
```

If you are already inside Houdini:

```python
from hda_as_code.apply import apply, dump_from_hou
apply(network.to_data())
```

## Typed builders

Common SOPs are methods on `Network` (`grid`, `box`, `sphere`, `mountain`, `xform`, `merge`, `scatter`, `copytopoints`, `attribwrangle`, …). Pass a node handle to wire an input; pass a literal, `ParmRef`, or `Expr` to set a parm.

Anything not wrapped is still valid:

```python
n.node("isooffset", id="volume", inputs=[mesh], parms={"samplediv": 40})
```

Unknown node types are allowed. The catalog is how builders name parms and skip defaults without hou.

## Tests

```bash
pytest -q
UPDATE_GOLDENS=1 pytest tests/test_golden.py   # rewrite fixtures after an intentional dump change
```

Goldens live in `tests/goldens/`. If a builder change is intentional, update them. If it is not, the test failed for a reason.

## Layout

```
src/hda_as_code/    library
examples/           sample networks as Python
tests/goldens/      canonical JSON fixtures
```
