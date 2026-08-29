"""Example SOP networks shipped with the library.

These are the golden fixtures: Python is how you author, JSON is what git diffs.
"""

from __future__ import annotations

from hda_as_code.network import Network


def build_terrain() -> Network:
    """Grid displaced by Mountain, then normals — the chain MCP demos use."""
    n = Network("Terrain")
    height = n.parm_float("Height", 1.0, min=0.0, max=10.0)
    element = n.parm_float("elementsize", 2.0, min=0.01, max=50.0, label="Element Size")
    grid = n.grid(rows=80, cols=80, sizex=10, sizey=10, id="grid")
    displace = n.mountain(grid, height=height, elementsize=element, id="mountain")
    n.normal(displace, id="normals")
    return n


def build_scatter() -> Network:
    """Scatter small spheres across a ground grid."""
    n = Network("Scatter")
    count = n.parm_int("Count", 200, min=1, max=5000)
    radius = n.parm_float("Radius", 0.08, min=0.001, max=1.0)
    ground = n.grid(rows=20, cols=20, sizex=4, sizey=4, id="ground")
    points = n.scatter(ground, npts=count, seed=7, id="points")
    pebble = n.sphere(radx=radius, rady=radius, radz=radius, type="poly", rows=6, cols=8, id="pebble")
    n.copytopoints(pebble, points, id="copies")
    return n


def build_column() -> Network:
    """Parametric column: plinth + shaft, both driven by Width / Height."""
    n = Network("Column")
    height = n.parm_float("Height", 2.0, min=0.1, max=20.0)
    width = n.parm_float("Width", 0.4, min=0.05, max=5.0)
    plinth_h = n.parm_float("Plinth", 0.15, min=0.0, max=2.0)

    shaft = n.box(
        size=[width, height, width],
        ty=n.expr('ch("../Height") / 2'),
        id="shaft",
    )
    plinth = n.box(
        sizex=n.expr('ch("../Width") + 0.1'),
        sizey=plinth_h,
        sizez=n.expr('ch("../Width") + 0.1'),
        ty=n.expr('ch("../Plinth") / 2'),
        id="plinth",
    )
    n.merge(plinth, shaft, id="join")
    return n


SAMPLES = {
    "terrain": build_terrain,
    "scatter": build_scatter,
    "column": build_column,
}
