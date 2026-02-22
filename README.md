# Proxasaurus 🦕

A full-stack infrastructure MCP server for [Claude](https://claude.ai). Manage Proxmox VE clusters, Kubernetes workloads, and network infrastructure through natural language.

Built on top of [PegaProx](https://github.com/PegaProx/project-pegaprox) — the multi-cluster Proxmox management platform.

## Topology

```
[Claude] ---(MCP/SSE:5010)---> [Proxasaurus] ---(HTTP:5000)---> [PegaProx] ---> [Proxmox Clusters]
```

## Setup

### 1. Generate a PegaProx API token

In the PegaProx UI, create a dedicated API token for Proxasaurus. Copy the `pgx_...` value.

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set PEGAPROX_API_TOKEN and PEGAPROX_BASE_URL
```

### 3. Install and run (development)

```bash
uv sync
uv run proxasaurus
```

Verify:

```bash
curl -N http://localhost:5010/sse
```

### 4. Deploy with systemd

```bash
rsync -av . user@server:/app/proxasaurus/
# On the server:
cp /app/proxasaurus/.env.example /app/proxasaurus/.env
# Edit .env, then:
sudo cp /app/proxasaurus/deploy/proxasaurus.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now proxasaurus
```

## Tools

| Module | Count | Tools |
|--------|-------|-------|
| clusters | 3 | `list_clusters`, `get_global_summary`, `get_cluster_metrics` |
| nodes | 3 | `list_nodes`, `get_node_summary`, `node_action` |
| vms | 6 | `list_vms`, `get_vm_config`, `vm_action`, `migrate_vm`, `clone_vm`, `delete_vm` |
| snapshots | 5 | `list_snapshots`, `create_snapshot`, `rollback_snapshot`, `delete_snapshot`, `list_all_snapshots` |
| backups | 4 | `list_backups`, `create_backup`, `restore_backup`, `delete_backup` |
| storage | 6 | `list_datastores`, `list_datastore_content`, `delete_datastore_content`, `download_iso`, `list_storage_clusters`, `get_storage_cluster_status` |
| provisioning | 5 | `create_vm`, `create_container`, `list_available_templates`, `list_isos`, `list_node_templates` |
| alerts | 3 | `list_alerts`, `create_alert`, `delete_alert` |
| schedules | 4 | `list_scheduled_tasks`, `create_scheduled_task`, `delete_scheduled_task`, `run_scheduled_task` |
| audit | 3 | `get_audit_log`, `get_cluster_audit`, `get_migration_history` |
| **Total** | **42** | |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PEGAPROX_BASE_URL` | `http://localhost:5000` | PegaProx API base URL |
| `PEGAPROX_API_TOKEN` | *(required)* | Bearer token (`pgx_...`) |
| `MCP_HOST` | `0.0.0.0` | Interface to bind MCP server to |
| `MCP_PORT` | `5010` | Port for SSE transport |
