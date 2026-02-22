"""MCP tools for VM snapshot operations."""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from proxasaurus.client import client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_snapshots(cluster_name: str, vmid: int) -> str:
        """List all snapshots for a specific VM.

        Args:
            cluster_name: The cluster containing the VM.
            vmid: The numeric VM ID.

        Returns each snapshot's name, creation time, description, and whether
        it includes RAM state.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/vms/{vmid}/snapshots")
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def list_all_snapshots(cluster_name: str) -> str:
        """List all snapshots across every VM in a cluster.

        Args:
            cluster_name: The cluster to query.

        Returns a consolidated list of all snapshots grouped by VM, useful for
        identifying old or unused snapshots across the cluster.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/snapshots")
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def create_snapshot(
        cluster_name: str,
        vmid: int,
        snapshot_name: str,
        description: Optional[str] = None,
        include_ram: bool = False,
    ) -> str:
        """Create a snapshot of a VM.

        Args:
            cluster_name: The cluster containing the VM.
            vmid: The numeric VM ID.
            snapshot_name: Name for the snapshot (alphanumeric and hyphens only).
            description: Optional human-readable description of the snapshot.
            include_ram: If True, include RAM state in the snapshot (requires
                         more time and storage). Defaults to False.

        Returns snapshot creation task status or an error message.
        """
        payload: dict = {"snapname": snapshot_name, "vmstate": include_ram}
        if description:
            payload["description"] = description
        data, err = client.post(
            f"/api/clusters/{cluster_name}/vms/{vmid}/snapshots",
            json=payload,
        )
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def rollback_snapshot(cluster_name: str, vmid: int, snapshot_name: str) -> str:
        """Roll back a VM to a previously created snapshot.

        IMPORTANT: This is destructive — all changes made after the snapshot
        was taken will be permanently lost. Confirm with the user before
        proceeding. The VM must be stopped for rollback.

        Args:
            cluster_name: The cluster containing the VM.
            vmid: The numeric VM ID.
            snapshot_name: The name of the snapshot to roll back to.

        Returns rollback task status or an error message.
        """
        data, err = client.post(
            f"/api/clusters/{cluster_name}/vms/{vmid}/snapshots/{snapshot_name}/rollback",
        )
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def delete_snapshot(cluster_name: str, vmid: int, snapshot_name: str) -> str:
        """Delete a snapshot from a VM.

        IMPORTANT: Snapshot deletion is irreversible. Confirm with the user
        before deleting, especially for snapshots that may be the only recovery
        point before a risky change.

        Args:
            cluster_name: The cluster containing the VM.
            vmid: The numeric VM ID.
            snapshot_name: The name of the snapshot to delete.

        Returns deletion result or an error message.
        """
        data, err = client.delete(
            f"/api/clusters/{cluster_name}/vms/{vmid}/snapshots/{snapshot_name}",
        )
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)
