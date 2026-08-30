"""Structural validation of a network dump. No hou required."""

from __future__ import annotations

from dataclasses import dataclass

from hda_as_code.catalog import get_spec
from hda_as_code.ir import Link, NetworkData, Node
from hda_as_code.types import is_parm_expr, is_parm_ref


@dataclass
class NetworkError:
    code: str
    message: str
    node: str | None = None

    def __str__(self) -> str:
        if self.node:
            return f"{self.code}: {self.node}: {self.message}"
        return f"{self.code}: {self.message}"


def validate(network: NetworkData) -> list[NetworkError]:
    errors: list[NetworkError] = []
    ids = [node.id for node in network.nodes]
    if len(ids) != len(set(ids)):
        seen: set[str] = set()
        for node_id in ids:
            if node_id in seen:
                errors.append(
                    NetworkError("duplicate_id", f"Node id {node_id!r} is used twice", node_id)
                )
            seen.add(node_id)
    nodes = network.node_map()

    if not network.nodes:
        errors.append(NetworkError("empty_network", "Network has no SOP nodes"))

    parm_names = [item.name for item in network.interface]
    if len(parm_names) != len(set(parm_names)):
        errors.append(NetworkError("duplicate_interface", "Duplicate interface parm names"))

    if network.display:
        if network.display not in nodes:
            errors.append(
                NetworkError(
                    "unknown_display",
                    f"Display node {network.display!r} does not exist",
                )
            )
    elif network.nodes:
        errors.append(NetworkError("missing_display", "Network has no display node"))

    for node in network.nodes:
        errors.extend(_validate_node(node, parm_names))

    for link in network.links:
        errors.extend(_validate_link(link, nodes))

    return errors


def _validate_node(node: Node, interface_names: list[str]) -> list[NetworkError]:
    errors: list[NetworkError] = []
    spec = get_spec(node.type)
    known = spec.known_parm_names() if spec is not None else set()
    for key, value in node.parms.items():
        if spec is not None and known and key not in known:
            errors.append(
                NetworkError(
                    "unknown_parm",
                    f"Parm {key!r} is not a catalog parm on {node.type}",
                    node.id,
                )
            )
        if is_parm_ref(value) and value["ref"] not in interface_names:
            errors.append(
                NetworkError(
                    "unknown_ref",
                    f"Parm {key!r} references missing interface parm {value['ref']!r}",
                    node.id,
                )
            )
        if spec is None:
            continue
        catalog = spec.parm_map().get(key)
        if catalog is not None and catalog.items and not (is_parm_ref(value) or is_parm_expr(value)):
            if value not in catalog.items:
                errors.append(
                    NetworkError(
                        "invalid_parm",
                        f"Parm {key!r}={value!r} not in {catalog.items}",
                        node.id,
                    )
                )
    return errors


def _validate_link(link: Link, nodes: dict[str, Node]) -> list[NetworkError]:
    errors: list[NetworkError] = []
    if link.from_node not in nodes:
        errors.append(NetworkError("dangling_link", f"from_node {link.from_node!r} does not exist"))
        return errors
    if link.to_node not in nodes:
        errors.append(NetworkError("dangling_link", f"to_node {link.to_node!r} does not exist"))
        return errors
    src = nodes[link.from_node]
    dst = nodes[link.to_node]
    src_spec = get_spec(src.type)
    if src_spec is not None and src_spec.outputs >= 0 and link.from_output >= src_spec.outputs:
        errors.append(
            NetworkError(
                "unknown_output",
                f"Node {src.type} has no output {link.from_output}",
                src.id,
            )
        )
    dst_spec = get_spec(dst.type)
    if (
        dst_spec is not None
        and dst_spec.inputs >= 0
        and link.to_input >= dst_spec.inputs
        and dst_spec.inputs > 0
    ):
        errors.append(
            NetworkError(
                "unknown_input",
                f"Node {dst.type} has no input {link.to_input}",
                dst.id,
            )
        )
    return errors
