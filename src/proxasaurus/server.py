"""Proxasaurus MCP Server — FastMCP entry point with SSE transport."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP(
    "Proxasaurus",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "5010")),
    instructions=(
        "You are Proxasaurus — a full-stack infrastructure management assistant. "
        "You can manage Proxmox VE clusters (VMs, containers, nodes, storage, backups, HA), "
        "Kubernetes workloads (clusters, deployments, pods, nodes), "
        "and network infrastructure (Tailscale). "
        "You have deep visibility across the entire stack.\n\n"
        "IMPORTANT: Before performing any destructive or irreversible action "
        "(stopping/deleting a VM, rolling back a snapshot, stopping a node, purging disks, "
        "draining a Kubernetes node, deleting a namespace), "
        "always confirm with the user first. Describe exactly what will happen and ask "
        "for explicit approval before proceeding."
    ),
)


def _register_tools() -> None:
    from proxasaurus.tools import clusters, nodes, vms, snapshots, alerts, schedules, audit
    from proxasaurus.tools import backups, storage, provisioning
    from proxasaurus.tools import k8s_clusters, k8s_nodes, k8s_workloads

    # Proxmox / PegaProx
    clusters.register(mcp)
    nodes.register(mcp)
    vms.register(mcp)
    snapshots.register(mcp)
    alerts.register(mcp)
    schedules.register(mcp)
    audit.register(mcp)
    backups.register(mcp)
    storage.register(mcp)
    provisioning.register(mcp)

    # Kubernetes
    k8s_clusters.register(mcp)
    k8s_nodes.register(mcp)
    k8s_workloads.register(mcp)


def main() -> None:
    _register_tools()
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
