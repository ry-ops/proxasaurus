"""Storage and datastore management tools."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP
from proxasaurus.client import client


def _format(data: object) -> str:
    return json.dumps(data, indent=2)


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_datastores(cluster_name: str) -> str:
        """List all storage pools/datastores in a cluster with usage stats.

        Args:
            cluster_name: Name of the cluster.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/datastores")
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def list_datastore_content(
        cluster_name: str,
        storage_name: str,
        content_type: str = "",
    ) -> str:
        """List contents of a storage pool (backups, ISOs, templates, disk images).

        Args:
            cluster_name: Name of the cluster.
            storage_name: Name of the storage pool (e.g. 'local', 'nfs-backups').
            content_type: Optional filter — 'backup', 'iso', 'vztmpl', 'images', or '' for all.
        """
        params = {}
        if content_type:
            params["content"] = content_type
        data, err = client.get(
            f"/api/clusters/{cluster_name}/datastores/{storage_name}/content",
            params=params,
        )
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def delete_datastore_content(
        cluster_name: str,
        storage_name: str,
        volid: str,
    ) -> str:
        """Delete a file from a storage pool (ISO, template, backup, etc).

        WARNING: This is irreversible. Confirm with the user before proceeding.

        Args:
            cluster_name: Name of the cluster.
            storage_name: Name of the storage pool.
            volid: Volume ID to delete.
        """
        import urllib.parse
        encoded = urllib.parse.quote(volid, safe="")
        data, err = client.delete(
            f"/api/clusters/{cluster_name}/datastores/{storage_name}/content/{encoded}",
        )
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def download_iso(
        cluster_name: str,
        storage_name: str,
        url: str,
        filename: str,
    ) -> str:
        """Download an ISO or container template from a URL into a storage pool.

        Args:
            cluster_name: Name of the cluster.
            storage_name: Storage pool to download into (e.g. 'local').
            url: Direct download URL for the ISO or template.
            filename: Filename to save as (e.g. 'ubuntu-24.04.iso').
        """
        data, err = client.post(
            f"/api/clusters/{cluster_name}/datastores/{storage_name}/download-url",
            json={"url": url, "filename": filename},
        )
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def list_storage_clusters(cluster_name: str) -> str:
        """List storage clusters (Ceph, ZFS, etc) and their status.

        Args:
            cluster_name: Name of the Proxmox cluster.
        """
        data, err = client.get(f"/api/clusters/{cluster_name}/storage-clusters")
        if err:
            return f"Error: {err}"
        return _format(data)

    @mcp.tool()
    def get_storage_cluster_status(cluster_name: str, storage_cluster_id: str) -> str:
        """Get detailed status and health of a storage cluster (e.g. Ceph health, OSD status).

        Args:
            cluster_name: Name of the Proxmox cluster.
            storage_cluster_id: ID of the storage cluster.
        """
        data, err = client.get(
            f"/api/clusters/{cluster_name}/storage-clusters/{storage_cluster_id}/status"
        )
        if err:
            return f"Error: {err}"
        return _format(data)
