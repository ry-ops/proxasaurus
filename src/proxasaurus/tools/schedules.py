"""MCP tools for scheduled task management."""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from proxasaurus.client import client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def list_scheduled_tasks(cluster_name: Optional[str] = None) -> str:
        """List all scheduled tasks, optionally filtered by cluster.

        Args:
            cluster_name: If provided, only return tasks for this cluster.
                          If omitted, returns tasks across all clusters.

        Returns each task's name, schedule (cron expression), action, target,
        last run time, and next scheduled run time.
        """
        params = {"cluster": cluster_name} if cluster_name else {}
        data, err = client.get("/api/schedules", params=params if params else None)
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def create_scheduled_task(
        name: str,
        cluster_name: str,
        action: str,
        schedule: str,
        target_type: str,
        target_id: Optional[str] = None,
        enabled: bool = True,
        description: Optional[str] = None,
    ) -> str:
        """Create a new scheduled task.

        Args:
            name: Unique name for this scheduled task.
            cluster_name: The cluster this task applies to.
            action: The action to perform (e.g. 'snapshot', 'start', 'stop',
                    'backup', 'reboot').
            schedule: Cron expression for the schedule (e.g. '0 2 * * *' for
                      daily at 2am).
            target_type: What the action targets: 'vm', 'node', or 'cluster'.
            target_id: The VMID or node name, if target_type is 'vm' or 'node'.
                       Not required when target_type is 'cluster'.
            enabled: Whether to enable the task immediately. Defaults to True.
            description: Optional description of what this task does.

        Returns the created task object or an error message.
        """
        valid_target_types = {"vm", "node", "cluster"}
        if target_type not in valid_target_types:
            return (
                f"Error: Invalid target_type '{target_type}'. "
                f"Must be one of: {', '.join(sorted(valid_target_types))}"
            )

        payload: dict = {
            "name": name,
            "cluster": cluster_name,
            "action": action,
            "schedule": schedule,
            "target_type": target_type,
            "enabled": enabled,
        }
        if target_id is not None:
            payload["target_id"] = target_id
        if description:
            payload["description"] = description

        data, err = client.post("/api/schedules", json=payload)
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def delete_scheduled_task(task_id: str) -> str:
        """Delete a scheduled task by its ID.

        Args:
            task_id: The ID of the scheduled task to delete
                     (as returned by list_scheduled_tasks).

        Returns deletion confirmation or an error message.
        """
        data, err = client.delete(f"/api/schedules/{task_id}")
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)

    @mcp.tool()
    def run_scheduled_task(task_id: str) -> str:
        """Immediately trigger a scheduled task to run now, outside its schedule.

        Args:
            task_id: The ID of the scheduled task to run
                     (as returned by list_scheduled_tasks).

        Returns the task execution result or an error message.
        """
        data, err = client.post(f"/api/schedules/{task_id}/run")
        if err:
            return f"Error: {err}"
        return json.dumps(data, indent=2)
