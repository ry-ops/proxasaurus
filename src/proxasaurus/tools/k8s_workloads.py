"""Kubernetes workload management tools — pods, deployments, services, jobs."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP


def _format(data: object) -> str:
    return json.dumps(data, indent=2)


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    def k8s_list_pods(namespace: str = "", context: str = "", node_name: str = "") -> str:
        """List pods with status, node placement, and restart counts.

        Args:
            namespace: Namespace to filter by. Lists all namespaces if omitted.
            context: Kubeconfig context name. Uses active context if omitted.
            node_name: Optional — filter pods running on a specific node.
        """
        from proxasaurus.k8s_client import core_v1, _safe
        v1 = core_v1(context or None)

        field_selector = f"spec.nodeName={node_name}" if node_name else ""

        if namespace:
            result, err = _safe(lambda: v1.list_namespaced_pod(
                namespace=namespace, field_selector=field_selector or None
            ))
        else:
            result, err = _safe(lambda: v1.list_pod_for_all_namespaces(
                field_selector=field_selector or None
            ))
        if err:
            return f"Error: {err}"

        pods = []
        for pod in result.items:
            containers = pod.spec.containers or []
            statuses = pod.status.container_statuses or []
            restart_count = sum(s.restart_count for s in statuses)
            pods.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "phase": pod.status.phase,
                "node": pod.spec.node_name,
                "ip": pod.status.pod_ip,
                "ready": f"{sum(1 for s in statuses if s.ready)}/{len(containers)}",
                "restarts": restart_count,
                "age": str(pod.metadata.creation_timestamp),
            })
        return _format(pods)

    @mcp.tool()
    def k8s_list_deployments(namespace: str = "default", context: str = "") -> str:
        """List deployments with replica status and image info.

        Args:
            namespace: Namespace to list deployments in (default: 'default').
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import apps_v1, _safe
        api = apps_v1(context or None)
        result, err = _safe(lambda: api.list_namespaced_deployment(namespace=namespace))
        if err:
            return f"Error: {err}"

        deployments = []
        for d in result.items:
            images = [c.image for c in (d.spec.template.spec.containers or [])]
            deployments.append({
                "name": d.metadata.name,
                "namespace": d.metadata.namespace,
                "replicas": {
                    "desired": d.spec.replicas,
                    "ready": d.status.ready_replicas or 0,
                    "available": d.status.available_replicas or 0,
                    "updated": d.status.updated_replicas or 0,
                },
                "images": images,
                "age": str(d.metadata.creation_timestamp),
            })
        return _format(deployments)

    @mcp.tool()
    def k8s_restart_deployment(name: str, namespace: str = "default", context: str = "") -> str:
        """Trigger a rolling restart of a deployment (zero-downtime).

        Patches the pod template annotation with a timestamp, triggering
        a rolling update per the deployment's strategy.

        Args:
            name: Deployment name.
            namespace: Namespace (default: 'default').
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import apps_v1, _safe
        api = apps_v1(context or None)
        now = datetime.now(timezone.utc).isoformat()
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": now
                        }
                    }
                }
            }
        }
        _, err = _safe(lambda: api.patch_namespaced_deployment(
            name=name, namespace=namespace, body=body
        ))
        if err:
            return f"Error: {err}"
        return f"Rolling restart triggered for deployment '{name}' in namespace '{namespace}'."

    @mcp.tool()
    def k8s_scale_deployment(
        name: str,
        replicas: int,
        namespace: str = "default",
        context: str = "",
    ) -> str:
        """Scale a deployment to a specific number of replicas.

        Args:
            name: Deployment name.
            replicas: Desired replica count.
            namespace: Namespace (default: 'default').
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import apps_v1, _safe
        api = apps_v1(context or None)
        body = {"spec": {"replicas": replicas}}
        _, err = _safe(lambda: api.patch_namespaced_deployment(
            name=name, namespace=namespace, body=body
        ))
        if err:
            return f"Error: {err}"
        return f"Deployment '{name}' scaled to {replicas} replica(s)."

    @mcp.tool()
    def k8s_list_services(namespace: str = "default", context: str = "") -> str:
        """List services with type, cluster IP, external IP, and ports.

        Args:
            namespace: Namespace (default: 'default'). Use '' for all namespaces.
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import core_v1, _safe
        v1 = core_v1(context or None)

        if namespace:
            result, err = _safe(lambda: v1.list_namespaced_service(namespace=namespace))
        else:
            result, err = _safe(lambda: v1.list_service_for_all_namespaces())
        if err:
            return f"Error: {err}"

        services = []
        for svc in result.items:
            ingress = svc.status.load_balancer.ingress or [] if svc.status.load_balancer else []
            external_ips = [i.ip or i.hostname for i in ingress]
            ports = [
                f"{p.port}:{p.node_port or '-'}/{p.protocol}"
                for p in (svc.spec.ports or [])
            ]
            services.append({
                "name": svc.metadata.name,
                "namespace": svc.metadata.namespace,
                "type": svc.spec.type,
                "cluster_ip": svc.spec.cluster_ip,
                "external_ips": external_ips,
                "ports": ports,
                "selector": svc.spec.selector or {},
            })
        return _format(services)

    @mcp.tool()
    def k8s_get_pod_logs(
        name: str,
        namespace: str = "default",
        context: str = "",
        container: str = "",
        tail_lines: int = 100,
    ) -> str:
        """Get logs from a pod or specific container.

        Args:
            name: Pod name.
            namespace: Namespace (default: 'default').
            context: Kubeconfig context name. Uses active context if omitted.
            container: Container name (required if pod has multiple containers).
            tail_lines: Number of log lines to return from the end (default: 100).
        """
        from proxasaurus.k8s_client import core_v1, _safe
        v1 = core_v1(context or None)
        kwargs: dict = {"name": name, "namespace": namespace, "tail_lines": tail_lines}
        if container:
            kwargs["container"] = container
        result, err = _safe(lambda: v1.read_namespaced_pod_log(**kwargs))
        if err:
            return f"Error: {err}"
        return result or "(no logs)"

    @mcp.tool()
    def k8s_pod_metrics(namespace: str = "", context: str = "") -> str:
        """Get CPU and memory usage per pod (requires metrics-server).

        Args:
            namespace: Namespace to filter by. All namespaces if omitted.
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import custom_objects, _safe
        api = custom_objects(context or None)

        if namespace:
            result, err = _safe(lambda: api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods",
            ))
        else:
            result, err = _safe(lambda: api.list_cluster_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                plural="pods",
            ))
        if err:
            return f"Error: {err} (is metrics-server installed?)"

        pods = []
        for item in result.get("items", []):
            containers = [
                {
                    "name": c["name"],
                    "cpu": c["usage"]["cpu"],
                    "memory": c["usage"]["memory"],
                }
                for c in item.get("containers", [])
            ]
            pods.append({
                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "containers": containers,
                "timestamp": item.get("timestamp"),
            })
        return _format(pods)

    @mcp.tool()
    def k8s_list_statefulsets(namespace: str = "default", context: str = "") -> str:
        """List StatefulSets with replica status and images.

        Args:
            namespace: Namespace (default: 'default').
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import apps_v1, _safe
        api = apps_v1(context or None)
        result, err = _safe(lambda: api.list_namespaced_stateful_set(namespace=namespace))
        if err:
            return f"Error: {err}"

        sets = []
        for s in result.items:
            images = [c.image for c in (s.spec.template.spec.containers or [])]
            sets.append({
                "name": s.metadata.name,
                "namespace": s.metadata.namespace,
                "replicas": {
                    "desired": s.spec.replicas,
                    "ready": s.status.ready_replicas or 0,
                    "current": s.status.current_replicas or 0,
                },
                "images": images,
                "age": str(s.metadata.creation_timestamp),
            })
        return _format(sets)

    @mcp.tool()
    def k8s_list_jobs(namespace: str = "default", context: str = "") -> str:
        """List Jobs with completion status.

        Args:
            namespace: Namespace (default: 'default').
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import batch_v1, _safe
        api = batch_v1(context or None)
        result, err = _safe(lambda: api.list_namespaced_job(namespace=namespace))
        if err:
            return f"Error: {err}"

        jobs = []
        for j in result.items:
            jobs.append({
                "name": j.metadata.name,
                "namespace": j.metadata.namespace,
                "completions": f"{j.status.succeeded or 0}/{j.spec.completions or 1}",
                "active": j.status.active or 0,
                "failed": j.status.failed or 0,
                "start_time": str(j.status.start_time),
                "completion_time": str(j.status.completion_time),
            })
        return _format(jobs)

    @mcp.tool()
    def k8s_list_ingresses(namespace: str = "default", context: str = "") -> str:
        """List Ingress resources with hostnames and backend services.

        Args:
            namespace: Namespace (default: 'default'). Use '' for all namespaces.
            context: Kubeconfig context name. Uses active context if omitted.
        """
        from proxasaurus.k8s_client import networking_v1, _safe
        api = networking_v1(context or None)

        if namespace:
            result, err = _safe(lambda: api.list_namespaced_ingress(namespace=namespace))
        else:
            result, err = _safe(lambda: api.list_ingress_for_all_namespaces())
        if err:
            return f"Error: {err}"

        ingresses = []
        for ing in result.items:
            rules = []
            for rule in (ing.spec.rules or []):
                paths = []
                if rule.http:
                    for path in (rule.http.paths or []):
                        backend = path.backend
                        svc = backend.service
                        paths.append({
                            "path": path.path,
                            "service": f"{svc.name}:{svc.port.number}" if svc else "?",
                        })
                rules.append({"host": rule.host, "paths": paths})
            ingresses.append({
                "name": ing.metadata.name,
                "namespace": ing.metadata.namespace,
                "class": ing.spec.ingress_class_name,
                "rules": rules,
            })
        return _format(ingresses)
