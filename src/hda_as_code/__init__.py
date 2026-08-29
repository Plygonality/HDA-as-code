"""SOP network fragments as data.

This library is the network. Plygon-mcp applies it and checks the viewport.
"""

from hda_as_code.diff import NetworkDiff, diff_networks, format_diff
from hda_as_code.dump import dumps, from_dict, loads, to_dict
from hda_as_code.ir import FORMAT, FORMAT_VERSION, Link, NetworkData, Node, ParmItem
from hda_as_code.network import Expr, Network, NodeHandle, OutputRef, ParmRef
from hda_as_code.types import NetworkKind, ParmType
from hda_as_code.validate import NetworkError, validate

__all__ = [
    "FORMAT",
    "FORMAT_VERSION",
    "Expr",
    "Link",
    "Network",
    "NetworkData",
    "NetworkDiff",
    "NetworkError",
    "NetworkKind",
    "Node",
    "NodeHandle",
    "OutputRef",
    "ParmItem",
    "ParmRef",
    "ParmType",
    "diff_networks",
    "dumps",
    "format_diff",
    "from_dict",
    "loads",
    "to_dict",
    "validate",
]

__version__ = "0.1.0"
