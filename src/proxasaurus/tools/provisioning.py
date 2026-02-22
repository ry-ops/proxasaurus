"""VM and LXC container provisioning tools."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from proxasaurus.client import client


def _format(data: object) -> str:
    return json.dumps(data, indent=2)


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def create_vm(
        cluster_name: str,
        node_name: str,
        vmid: int,
        name: str,
        memory_mb: int = 2048,
        cores: int = 2,
        sockets: int = 1,
        disk_size_gb: int = 32,
        storage: str = "local-lvm",
        iso: str = "",
        os_type: str = "l26",
        net_bridge: str = "vmbr0",
        start_on_create: bool = False,
    ) -> str:
        """Create a new QEMU virtual machine.

        Args:
            cluster_name: Name of the cluster.
            node_name: Node to create the VM on.
            vmid: VM ID (must be unique in the cluster).
            name: VM name.
            memory_mb: RAM in megabytes (default: 2048).
            cores: Number of CPU cores per socket (default: 2).
            sockets: Number of CPU sockets (default: 1).
            disk_size_gb: Primary disk size in GB (default: 32).
            storage: Storage pool for the disk (default: 'local-lvm').
            iso: Optional ISO path to mount as CDROM (e.g. 'local:iso/ubuntu-24.04.iso').
            os_type: OS type hint — 'l26' for Linux, 'win11' for Windows, etc (default: 'l26').
            net_bridge: Network bridge to attach to (default: 'vmbr0').
            start_on_create: Whether to start the VM immediately after creation (default: False).
        """
        payload: dict[str, Any] = {
            "vmid": vmid,
            "name": name,
            "memory": memory_mb,
            "cores": cores,
            "sockets": sockets,
            "ostype": os_type,
            "scsi0": f"{storage}:{disk_size_gb}",
            "scsihw": "virtio-scsi-pci",
            "net0": f"virtio,bridge={net_bridge}",
            "boot": "order=scsi0;ide2;net0",
        }
        if iso:
            payload["ide2"] = f"{iso},media=cdrom"
        if start_on_create:
            payload["start"] = 1

        data, err = client.post(
            f"/api/clusters/{cluster_name}/nodes/{node_name}/qemu",
            json=payload,
        )
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def create_container(
        cluster_name: str,
        node_name: str,
        vmid: int,
        name: str,
        template: str,
        memory_mb: int = 512,
        swap_mb: int = 512,
        cores: int = 1,
        disk_size_gb: int = 8,
        storage: str = "local-lvm",
        net_bridge: str = "vmbr0",
        ip_config: str = "dhcp",
        password: str = "",
        ssh_public_key: str = "",
        start_on_create: bool = False,
        unprivileged: bool = True,
    ) -> str:
        """Create a new LXC container.

        Args:
            cluster_name: Name of the cluster.
            node_name: Node to create the container on.
            vmid: Container ID (must be unique in the cluster).
            name: Container hostname.
            template: Container template (e.g. 'local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst').
            memory_mb: RAM in megabytes (default: 512).
            swap_mb: Swap in megabytes (default: 512).
            cores: Number of CPU cores (default: 1).
            disk_size_gb: Root disk size in GB (default: 8).
            storage: Storage pool for the disk (default: 'local-lvm').
            net_bridge: Network bridge to attach to (default: 'vmbr0').
            ip_config: IP config string — 'dhcp' or 'ip=192.168.1.100/24,gw=192.168.1.1' (default: 'dhcp').
            password: Root password for the container.
            ssh_public_key: Optional SSH public key to inject.
            start_on_create: Whether to start the container after creation (default: False).
            unprivileged: Run as unprivileged container (default: True, recommended).
        """
        payload: dict[str, Any] = {
            "vmid": vmid,
            "hostname": name,
            "ostemplate": template,
            "memory": memory_mb,
            "swap": swap_mb,
            "cores": cores,
            "rootfs": f"{storage}:{disk_size_gb}",
            "net0": f"name=eth0,bridge={net_bridge},ip={ip_config}",
            "unprivileged": 1 if unprivileged else 0,
        }
        if password:
            payload["password"] = password
        if ssh_public_key:
            payload["ssh-public-keys"] = ssh_public_key
        if start_on_create:
            payload["start"] = 1

        data, err = client.post(
            f"/api/clusters/{cluster_name}/nodes/{node_name}/lxc",
            json=payload,
        )
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def list_available_templates(cluster_name: str) -> str:
        """List VM and container templates available for deployment.

        Args:
            cluster_name: Name of the cluster.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/templates/available")
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def list_isos(cluster_name: str, node_name: str) -> str:
        """List ISO images available on a node for VM installation.

        Args:
            cluster_name: Name of the cluster.
            node_name: Name of the node.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/nodes/{node_name}/isos")
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def list_node_templates(cluster_name: str, node_name: str) -> str:
        """List container templates available on a node.

        Args:
            cluster_name: Name of the cluster.
            node_name: Name of the node.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/nodes/{node_name}/templates")
        if err:
            return f"Error: {err}"
        return _format(data)
