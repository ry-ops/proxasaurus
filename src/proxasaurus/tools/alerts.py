"""MCP tools for alert management."""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from proxasaurus.client import client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_alerts(
        cluster_name: Optional[str] = None,
        active_only: bool = False,
    ) -> str:
        """List configured alerts, optionally filtered by cluster.

        Args:
            cluster_name: If provided, only return alerts for this cluster.
                          If omitted, returns alerts across all clusters.
            active_only: If True, return only currently firing alerts.

        Returns each alert's name, condition, threshold, severity, and status.
        """
        params: dict = {}
        if cluster_name:
            params["cluster"] = cluster_name
        if active_only:
            params["active"] = "true"
        data, err = client.get("/api/alerts", params=params if params else None)
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def create_alert(
        name: str,
        cluster_name: str,
        metric: str,
        threshold: float,
        condition: str,
        severity: str = "warning",
        description: Optional[str] = None,
    ) -> str:
        """Create a new alert rule for a cluster metric.

        Args:
            name: Unique name for this alert rule.
            cluster_name: The cluster to monitor.
            metric: The metric to watch (e.g. 'cpu_usage', 'memory_usage',
                    'storage_usage').
            threshold: The numeric threshold value that triggers the alert.
            condition: Comparison operator: 'gt' (greater than), 'lt' (less than),
                       'gte' (>=), or 'lte' (<=).
            severity: Alert severity level: 'info', 'warning', or 'critical'.
                      Defaults to 'warning'.
            description: Optional human-readable description of what this alert means.

        Returns the created alert object or an error message.
        """
        valid_conditions = {"gt", "lt", "gte", "lte"}
        if condition not in valid_conditions:
            return f"Error: Invalid condition '{condition}'. Must be one of: {', '.join(sorted(valid_conditions))}"
        valid_severities = {"info", "warning", "critical"}
        if severity not in valid_severities:
            return f"Error: Invalid severity '{severity}'. Must be one of: {', '.join(sorted(valid_severities))}"

        payload: dict = {
            "name": name,
            "cluster": cluster_name,
            "metric": metric,
            "threshold": threshold,
            "condition": condition,
            "severity": severity,
        }
        if description:
            payload["description"] = description

        data, err = client.post("/api/alerts", json=payload)
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def delete_alert(alert_id: str) -> str:
        """Delete an alert rule by its ID.

        Args:
            alert_id: The ID of the alert to delete (as returned by list_alerts).

        Returns deletion confirmation or an error message.
        """
        data, err = client.delete(f"/api/alerts/{alert_id}")
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)
