"""Kubernetes client — supports multiple clusters via kubeconfig contexts."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

_KUBECONFIG = os.getenv("KUBECONFIG", os.path.expanduser("~/.kube/config"))


def _k8s():
    """Lazy import to avoid hard dependency if k8s tools aren't used."""
    from kubernetes import client, config
    return client, config


def _api_client_for(context: str | None = None):
    """Return a kubernetes ApiClient for the given context (or active context if None)."""
    client, config = _k8s()
    if context:
        return config.new_client_from_config(context=context, config_file=_KUBECONFIG)
    config.load_kube_config(config_file=_KUBECONFIG)
    return client.ApiClient()


def list_contexts() -> tuple[list[dict], str | None]:
    """Return all kubeconfig contexts as (list, error)."""
    try:
        _, config = _k8s()
        contexts, active = config.list_kube_config_contexts(config_file=_KUBECONFIG)
        result = []
        for ctx in contexts:
            result.append({
                "name": ctx["name"],
                "cluster": ctx["context"].get("cluster", ""),
                "user": ctx["context"].get("user", ""),
                "namespace": ctx["context"].get("namespace", "default"),
                "active": ctx["name"] == active["name"],
            })
        return result, None
    except Exception as exc:
        return [], str(exc)


def core_v1(context: str | None = None):
    client, _ = _k8s()
    return client.CoreV1Api(api_client=_api_client_for(context))


def apps_v1(context: str | None = None):
    client, _ = _k8s()
    return client.AppsV1Api(api_client=_api_client_for(context))


def custom_objects(context: str | None = None):
    client, _ = _k8s()
    return client.CustomObjectsApi(api_client=_api_client_for(context))


def batch_v1(context: str | None = None):
    client, _ = _k8s()
    return client.BatchV1Api(api_client=_api_client_for(context))


def networking_v1(context: str | None = None):
    client, _ = _k8s()
    return client.NetworkingV1Api(api_client=_api_client_for(context))


def _safe(fn) -> tuple[Any, str | None]:
    """Call fn(), return (result, None) on success or (None, error_str) on failure."""
    try:
        return fn(), None
    except Exception as exc:
        # Strip verbose kubernetes ApiException boilerplate down to the message
        msg = str(exc)
        if hasattr(exc, "reason"):
            msg = exc.reason  # type: ignore[attr-defined]
        if hasattr(exc, "body") and exc.body:  # type: ignore[attr-defined]
            try:
                import json
                body = json.loads(exc.body)  # type: ignore[attr-defined]
                msg = body.get("message", msg)
            except Exception:
                pass
        return None, msg
