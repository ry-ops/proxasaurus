"""Backup management tools for Proxmox VMs and containers."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP
from proxasaurus.client import client


def _format(data: object) -> str:
    return json.dumps(data, indent=2)


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_backups(cluster_name: str, node_name: str, vm_type: str, vmid: int) -> str:
        """List all backups for a specific VM or container.

        Args:
            cluster_name: Name of the cluster.
            node_name: Name of the node the VM resides on.
            vm_type: VM type — 'qemu' for VMs, 'lxc' for containers.
            vmid: The VM/container ID.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/vms/{node_name}/{vm_type}/{vmid}/backups")
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def create_backup(
        cluster_name: str,
        node_name: str,
        vm_type: str,
        vmid: int,
        storage: str,
        mode: str = "snapshot",
        compress: str = "zstd",
        notes: str = "",
    ) -> str:
        """Create a backup of a VM or container.

        Args:
            cluster_name: Name of the cluster.
            node_name: Name of the node the VM resides on.
            vm_type: VM type — 'qemu' for VMs, 'lxc' for containers.
            vmid: The VM/container ID.
            storage: Storage pool to save the backup to (e.g. 'local', 'nfs-backups').
            mode: Backup mode — 'snapshot' (default, no downtime), 'suspend', or 'stop'.
            compress: Compression algorithm — 'zstd' (default), 'lzo', 'gzip', or 'none'.
            notes: Optional notes to attach to the backup.
        """
        payload: dict = {"storage": storage, "mode": mode, "compress": compress}
        if notes:
            payload["notes"] = notes
        data, err = client.post(
            f"/api/clusters/{cluster_name}/vms/{node_name}/{vm_type}/{vmid}/backups/create",
            json=payload,
        )
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def restore_backup(
        cluster_name: str,
        node_name: str,
        vm_type: str,
        vmid: int,
        volid: str,
        target_storage: str = "",
    ) -> str:
        """Restore a VM or container from a backup.

        WARNING: This will overwrite the current VM state. Confirm with the user before proceeding.

        Args:
            cluster_name: Name of the cluster.
            node_name: Name of the node.
            vm_type: VM type — 'qemu' or 'lxc'.
            vmid: The VM/container ID to restore to.
            volid: The backup volume ID to restore from (e.g. 'local:backup/vzdump-qemu-100-...').
            target_storage: Optional storage pool to restore disks to. Defaults to original.
        """
        payload: dict = {"volid": volid}
        if target_storage:
            payload["storage"] = target_storage
        data, err = client.post(
            f"/api/clusters/{cluster_name}/vms/{node_name}/{vm_type}/{vmid}/backups/restore",
            json=payload,
        )
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def delete_backup(
        cluster_name: str,
        node_name: str,
        vm_type: str,
        vmid: int,
        volid: str,
    ) -> str:
        """Delete a backup.

        WARNING: This is irreversible. Confirm with the user before proceeding.

        Args:
            cluster_name: Name of the cluster.
            node_name: Name of the node.
            vm_type: VM type — 'qemu' or 'lxc'.
            vmid: The VM/container ID.
            volid: The backup volume ID to delete (e.g. 'local:backup/vzdump-qemu-100-...').
        """
        import urllib.parse
        encoded = urllib.parse.quote(volid, safe="")
        data, err = client.delete(
            f"/api/clusters/{cluster_name}/vms/{node_name}/{vm_type}/{vmid}/backups/{encoded}",
        )
        if err:
            return f"Error: {err}"
        return _format(data)
