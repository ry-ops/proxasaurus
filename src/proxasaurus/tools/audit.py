"""MCP tools for audit log and history queries."""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from proxasaurus.client import client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_audit_log(
        limit: int = 50,
        offset: int = 0,
        user: Optional[str] = None,
        action: Optional[str] = None,
    ) -> str:
        """Get the global audit log of all actions performed through PegaProx.

        Args:
            limit: Maximum number of entries to return. Defaults to 50.
            offset: Number of entries to skip for pagination. Defaults to 0.
            user: If provided, filter to actions performed by this username.
            action: If provided, filter to this specific action type
                    (e.g. 'vm.start', 'snapshot.create').

        Returns a list of audit log entries with timestamp, user, action,
        target, and result for each entry.
        """
        params: dict = {"limit": limit, "offset": offset}
        if user:
            params["user"] = user
        if action:
            params["action"] = action
        data, err = client.get("/api/audit", params=params)
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_cluster_audit(
        cluster_name: str,
        limit: int = 50,
        offset: int = 0,
    ) -> str:
        """Get the audit log filtered to a specific cluster.

        Args:
            cluster_name: The cluster to retrieve audit logs for.
            limit: Maximum number of entries to return. Defaults to 50.
            offset: Number of entries to skip for pagination. Defaults to 0.

        Returns audit log entries scoped to the specified cluster, including
        VM operations, node actions, snapshot events, and configuration changes.
        """
        params: dict = {"limit": limit, "offset": offset}
        data, err = client.get(f"/api/clusters/{cluster_name}/audit", params=params)
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_migration_history(
        cluster_name: Optional[str] = None,
        vmid: Optional[int] = None,
        limit: int = 50,
    ) -> str:
        """Get the history of VM migrations.

        Args:
            cluster_name: If provided, filter migrations to this cluster.
            vmid: If provided, filter migrations to this specific VM ID.
            limit: Maximum number of entries to return. Defaults to 50.

        Returns a list of migration events with source node, target node,
        VM ID, timestamp, duration, and whether the migration succeeded.
        """
        params: dict = {"limit": limit}
        if cluster_name:
            params["cluster"] = cluster_name
        if vmid is not None:
            params["vmid"] = vmid
        data, err = client.get("/api/migrations", params=params)
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)
