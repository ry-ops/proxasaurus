"""MCP tools for virtual machine operations."""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from proxasaurus.client import client

_VALID_VM_ACTIONS = {"start", "stop", "shutdown", "reboot", "suspend", "resume", "reset"}


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_vms(cluster_name: str, node_name: Optional[str] = None) -> str:
        """List virtual machines in a cluster, optionally filtered by node.

        Args:
            cluster_name: The cluster to query.
            node_name: If provided, only return VMs on this specific node.

        Returns each VM's VMID, name, status, CPU/memory allocation, and node.
        """
        path = f"/api/clusters/{cluster_name}/vms"
        params = {}
        if node_name:
            params["node"] = node_name
        data, err = client.get(path, params=params if params else None)
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def get_vm_config(cluster_name: str, vmid: int) -> str:
        """Get the full configuration for a specific VM.

        Args:
            cluster_name: The cluster the VM belongs to.
            vmid: The numeric VM ID.

        Returns the VM's hardware configuration including CPU, memory, disks,
        network interfaces, and current runtime status.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/vms/{vmid}")
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def vm_action(cluster_name: str, vmid: int, action: str) -> str:
        """Perform a power/lifecycle action on a VM.

        IMPORTANT: Confirm with the user before stopping, rebooting, or resetting
        a running VM to avoid data loss.

        Args:
            cluster_name: The cluster the VM belongs to.
            vmid: The numeric VM ID.
            action: One of 'start', 'stop', 'shutdown', 'reboot', 'suspend',
                    'resume', or 'reset'.

        Returns the result of the action or an error message.
        """
        if action not in _VALID_VM_ACTIONS:
            return (
                f"Error: Invalid action '{action}'. "
                f"Must be one of: {', '.join(sorted(_VALID_VM_ACTIONS))}"
            )
        data, err = client.post(
            f"/api/clusters/{cluster_name}/vms/{vmid}/action",
            json={"action": action},
        )
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def migrate_vm(
        cluster_name: str,
        vmid: int,
        target_node: str,
        online: bool = True,
    ) -> str:
        """Migrate a VM to a different node within the same cluster.

        Args:
            cluster_name: The cluster containing the VM.
            vmid: The numeric VM ID to migrate.
            target_node: The destination node name.
            online: If True, perform a live migration (default). If False,
                    the VM must be stopped first.

        Returns migration task status or an error message.
        """
        data, err = client.post(
            f"/api/clusters/{cluster_name}/vms/{vmid}/migrate",
            json={"target_node": target_node, "online": online},
        )
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def clone_vm(
        cluster_name: str,
        vmid: int,
        new_vmid: int,
        name: Optional[str] = None,
        target_node: Optional[str] = None,
        full_clone: bool = True,
    ) -> str:
        """Clone a VM or template into a new VM.

        Args:
            cluster_name: The cluster containing the source VM.
            vmid: The source VM ID to clone from.
            new_vmid: The VMID to assign to the new VM.
            name: Optional name for the new VM.
            target_node: Node to place the clone on. Defaults to same node as source.
            full_clone: If True (default), create an independent full clone.
                        If False, create a linked clone (requires template).

        Returns clone task status or an error message.
        """
        payload: dict = {"new_vmid": new_vmid, "full": full_clone}
        if name:
            payload["name"] = name
        if target_node:
            payload["target"] = target_node
        data, err = client.post(
            f"/api/clusters/{cluster_name}/vms/{vmid}/clone",
            json=payload,
        )
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def delete_vm(cluster_name: str, vmid: int, purge: bool = False) -> str:
        """Permanently delete a VM and optionally purge its disk images.

        IMPORTANT: This is irreversible. Always confirm with the user before
        deleting a VM. Ensure the VM is stopped before deletion.

        Args:
            cluster_name: The cluster containing the VM.
            vmid: The numeric VM ID to delete.
            purge: If True, also delete associated disk images from storage.
                   Defaults to False (disk images retained).

        Returns deletion result or an error message.
        """
        params = {"purge": "1"} if purge else {}
        data, err = client.delete(
            f"/api/clusters/{cluster_name}/vms/{vmid}",
            params=params if params else None,
        )
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)
