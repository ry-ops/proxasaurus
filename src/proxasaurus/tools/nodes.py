"""MCP tools for node-level operations."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from proxasaurus.client import client

_VALID_NODE_ACTIONS = {"start", "stop", "reboot"}


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_nodes(cluster_name: str) -> str:
        """List all nodes in a given Proxmox cluster.

        Args:
            cluster_name: The cluster to query (as returned by list_clusters).

        Returns each node's name, online status, CPU/memory usage, and uptime.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/nodes")
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_node_summary(cluster_name: str, node_name: str) -> str:
        """Get a detailed summary for a specific node.

        Args:
            cluster_name: The cluster the node belongs to.
            node_name: The name of the node (e.g. 'pve1').

        Returns CPU, memory, storage, network stats, and running VM list for
        the specified node.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/nodes/{node_name}")
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def node_action(cluster_name: str, node_name: str, action: str) -> str:
        """Perform a power action on a Proxmox node.

        IMPORTANT: This is a destructive operation. Confirm with the user before
        stopping or rebooting a node, as it will affect all VMs running on it.

        Args:
            cluster_name: The cluster the node belongs to.
            node_name: The name of the node (e.g. 'pve1').
            action: One of 'start', 'stop', or 'reboot'.

        Returns the result of the action or an error message.
        """
        if action not in _VALID_NODE_ACTIONS:
            return f"Error: Invalid action '{action}'. Must be one of: {', '.join(sorted(_VALID_NODE_ACTIONS))}"
        data, err = client.post(
            f"/api/clusters/{cluster_name}/nodes/{node_name}/action",
            json={"action": action},
        )
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)
