"""Kubernetes node management tools."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP


def _format(data: object) -> str:
    return json.dumps(data, indent=2)


def _node_summary(node) -> dict:
    conditions = {c.type: c.status for c in (node.status.conditions or [])}
    info = node.status.node_info
    capacity = node.status.capacity or {}
    allocatable = node.status.allocatable or {}
    return {
        "name": node.metadata.name,
        "ready": conditions.get("Ready") == "True",
        "schedulable": not node.spec.unschedulable,
        "roles": [
            k.replace("node-role.kubernetes.io/", "")
            for k in (node.metadata.labels or {})
            if k.startswith("node-role.kubernetes.io/")
        ] or ["worker"],
        "kubelet_version": info.kubelet_version,
        "os": info.os_image,
        "arch": info.architecture,
        "capacity": {
            "cpu": capacity.get("cpu", "?"),
            "memory": capacity.get("memory", "?"),
            "pods": capacity.get("pods", "?"),
        },
        "allocatable": {
            "cpu": allocatable.get("cpu", "?"),
            "memory": allocatable.get("memory", "?"),
            "pods": allocatable.get("pods", "?"),
        },
        "conditions": conditions,
        "created": str(node.metadata.creation_timestamp),
    }


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def k8s_list_nodes(context: str = "") -> str:
        """List all nodes in a Kubernetes cluster with status, roles, and resource capacity.

        Args:
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import core_v1, _safe
        v1 = core_v1(context or None)
        result, err = _safe(lambda: v1.list_node())
        if err:
            return f"Error: {err}"
        return _format([_node_summary(n) for n in result.items])

    @mcp.tool()
    def k8s_describe_node(node_name: str, context: str = "") -> str:
        """Get detailed information about a specific Kubernetes node.

        Args:
            node_name: Name of the node.
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import core_v1, _safe
        v1 = core_v1(context or None)
        result, err = _safe(lambda: v1.read_node(name=node_name))
        if err:
            return f"Error: {err}"
        return _format(_node_summary(result))

    @mcp.tool()
    def k8s_cordon_node(node_name: str, context: str = "") -> str:
        """Cordon a node — mark it unschedulable so no new pods are placed on it.

        Existing pods continue running. Use before draining or maintenance.

        Args:
            node_name: Name of the node to cordon.
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import core_v1, _safe
        v1 = core_v1(context or None)
        body = {"spec": {"unschedulable": True}}
        result, err = _safe(lambda: v1.patch_node(name=node_name, body=body))
        if err:
            return f"Error: {err}"
        return f"Node '{node_name}' cordoned (unschedulable=True)."

    @mcp.tool()
    def k8s_uncordon_node(node_name: str, context: str = "") -> str:
        """Uncordon a node — re-enable scheduling so pods can be placed on it.

        Args:
            node_name: Name of the node to uncordon.
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import core_v1, _safe
        v1 = core_v1(context or None)
        body = {"spec": {"unschedulable": False}}
        result, err = _safe(lambda: v1.patch_node(name=node_name, body=body))
        if err:
            return f"Error: {err}"
        return f"Node '{node_name}' uncordoned (schedulable)."

    @mcp.tool()
    def k8s_drain_node(node_name: str, context: str = "", ignore_daemonsets: bool = True) -> str:
        """Drain a node — evict all pods so it can be safely taken offline.

        Cordons the node first, then deletes all evictable pods. DaemonSet pods are
        skipped by default. Always cordon first if you want a dry-run step.

        WARNING: Running pods will be disrupted. Confirm with the user before proceeding.

        Args:
            node_name: Name of the node to drain.
            context: Kubeconfig context name. Uses active context if omitted.
            ignore_daemonsets: Skip DaemonSet-managed pods (default: True).
        """
        from proxasaurus.k8s_client import core_v1, _safe

        v1 = core_v1(context or None)

        # Cordon first
        _, err = _safe(lambda: v1.patch_node(name=node_name, body={"spec": {"unschedulable": True}}))
        if err:
            return f"Error cordoning node: {err}"

        # List pods on the node
        pods_result, err = _safe(
            lambda: v1.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={node_name}"
            )
        )
        if err:
            return f"Error listing pods on node: {err}"

        evicted: list[str] = []
        skipped: list[str] = []
        errors: list[str] = []

        for pod in pods_result.items:
            ns = pod.metadata.namespace
            name = pod.metadata.name
            owners = pod.metadata.owner_references or []

            # Skip DaemonSet pods if requested
            if ignore_daemonsets and any(o.kind == "DaemonSet" for o in owners):
                skipped.append(f"{ns}/{name} (DaemonSet)")
                continue

            # Skip static pods (no owner or owned by Node)
            if not owners or all(o.kind == "Node" for o in owners):
                skipped.append(f"{ns}/{name} (static pod)")
                continue

            _, err = _safe(lambda: v1.delete_namespaced_pod(name=name, namespace=ns))
            if err:
                errors.append(f"{ns}/{name}: {err}")
            else:
                evicted.append(f"{ns}/{name}")

        return _format({
            "node": node_name,
            "cordoned": True,
            "evicted": evicted,
            "skipped": skipped,
            "errors": errors,
        })

    @mcp.tool()
    def k8s_node_metrics(context: str = "") -> str:
        """Get CPU and memory usage for all nodes (requires metrics-server).

        Args:
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import custom_objects, _safe
        api = custom_objects(context or None)
        result, err = _safe(lambda: api.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes",
        ))
        if err:
            return f"Error: {err} (is metrics-server installed?)"
        nodes = [
            {
                "name": item["metadata"]["name"],
                "cpu": item["usage"]["cpu"],
                "memory": item["usage"]["memory"],
                "timestamp": item["timestamp"],
            }
            for item in result.get("items", [])
        ]
        return _format(nodes)
