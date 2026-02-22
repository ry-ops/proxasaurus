"""MCP tools for cluster-level operations."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from proxasaurus.client import client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_clusters() -> str:
        """List all Proxmox clusters managed by PegaProx.

        Returns each cluster's name, status (online/offline), node count, and
        basic resource summary. Use this as a starting point to discover what
        clusters are available before querying nodes or VMs.
        """
        data, err = client.get("/api/clusters")
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def get_global_summary() -> str:
        """Get a global resource summary across all clusters.

        Returns aggregated totals for CPU usage, memory usage, storage, and
        VM counts across every cluster managed by PegaProx. Useful for a
        high-level overview of overall infrastructure health.
        """
        data, err = client.get("/api/summary")
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def get_cluster_metrics(cluster_name: str) -> str:
        """Get detailed metrics for a specific cluster.

        Args:
            cluster_name: The name of the cluster as returned by list_clusters.

        Returns CPU, memory, storage usage over time, and current node/VM
        statistics for the specified cluster.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/metrics")
        if err:
            return f"Error: {err}"
        return _format(data)


def _format(data: object) -> str:
    import json
    return json.dumps(data, indent=2)
