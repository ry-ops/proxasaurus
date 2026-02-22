"""Kubernetes cluster and namespace management tools."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP


def _format(data: object) -> str:
    return json.dumps(data, indent=2)


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def k8s_list_contexts() -> str:
        """List all Kubernetes clusters (kubeconfig contexts) available to Proxasaurus.

        Shows cluster name, server, current active context, and default namespace.
        """
        from proxasaurus.k8s_client import list_contexts
        contexts, err = list_contexts()
        if err:
            return f"Error: {err}"
        return _format(contexts)

    @mcp.tool()
    def k8s_list_namespaces(context: str = "") -> str:
        """List all namespaces in a Kubernetes cluster.

        Args:
            context: Kubeconfig context name (cluster). Uses active context if omitted.
        """
        from proxasaurus.k8s_client import core_v1, _safe
        v1 = core_v1(context or None)
        result, err = _safe(lambda: v1.list_namespace())
        if err:
            return f"Error: {err}"
        namespaces = [
            {
                "name": ns.metadata.name,
                "status": ns.status.phase,
                "age": str(ns.metadata.creation_timestamp),
                "labels": ns.metadata.labels or {},
            }
            for ns in result.items
        ]
        return _format(namespaces)

    @mcp.tool()
    def k8s_create_namespace(name: str, context: str = "", labels: str = "") -> str:
        """Create a new Kubernetes namespace.

        Args:
            name: Namespace name to create.
            context: Kubeconfig context name. Uses active context if omitted.
            labels: Optional comma-separated key=value labels (e.g. 'env=prod,team=ops').
        """
        from kubernetes.client.models import V1Namespace, V1ObjectMeta
        from proxasaurus.k8s_client import core_v1, _safe

        label_dict: dict = {}
        if labels:
            for pair in labels.split(","):
                if "=" in pair:
                    k, v = pair.strip().split("=", 1)
                    label_dict[k] = v

        ns = V1Namespace(metadata=V1ObjectMeta(name=name, labels=label_dict or None))
        v1 = core_v1(context or None)
        result, err = _safe(lambda: v1.create_namespace(ns))
        if err:
            return f"Error: {err}"
        return f"Namespace '{name}' created successfully."

    @mcp.tool()
    def k8s_delete_namespace(name: str, context: str = "") -> str:
        """Delete a Kubernetes namespace and all resources within it.

        WARNING: This deletes all pods, services, deployments, and data in the namespace.
        Confirm with the user before proceeding.

        Args:
            name: Namespace to delete.
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import core_v1, _safe
        v1 = core_v1(context or None)
        result, err = _safe(lambda: v1.delete_namespace(name=name))
        if err:
            return f"Error: {err}"
        return f"Namespace '{name}' deletion initiated."

    @mcp.tool()
    def k8s_cluster_info(context: str = "") -> str:
        """Get high-level cluster summary: node count, pod count, namespace count, k8s version.

        Args:
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import core_v1, _safe
        v1 = core_v1(context or None)

        nodes_result, err = _safe(lambda: v1.list_node())
        if err:
            return f"Error listing nodes: {err}"

        pods_result, err = _safe(lambda: v1.list_pod_for_all_namespaces())
        if err:
            return f"Error listing pods: {err}"

        ns_result, err = _safe(lambda: v1.list_namespace())
        if err:
            return f"Error listing namespaces: {err}"

        nodes = nodes_result.items
        version = nodes[0].status.node_info.kubelet_version if nodes else "unknown"

        pod_phases: dict[str, int] = {}
        for pod in pods_result.items:
            phase = pod.status.phase or "Unknown"
            pod_phases[phase] = pod_phases.get(phase, 0) + 1

        summary = {
            "context": context or "active",
            "kubernetes_version": version,
            "nodes": {
                "total": len(nodes),
                "ready": sum(
                    1 for n in nodes
                    if any(c.type == "Ready" and c.status == "True" for c in (n.status.conditions or []))
                ),
            },
            "namespaces": len(ns_result.items),
            "pods": pod_phases,
        }
        return _format(summary)
