"""Singleton HTTP client for the PegaProx REST API."""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = os.getenv("PEGAPROX_BASE_URL", "http://localhost:5000")
_API_TOKEN = os.getenv("PEGAPROX_API_TOKEN", "")


class PegaProxClient:
    _instance: "PegaProxClient | None" = None

    def __new__(cls) -> "PegaProxClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self.base_url = _BASE_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> tuple[Any, str | None]:
        """Make an HTTP request. Returns (data, None) on success or (None, error) on failure."""
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(method, url, timeout=30, **kwargs)
        except requests.ConnectionError:
            return None, f"Cannot connect to PegaProx at {self.base_url}"
        except requests.Timeout:
            return None, f"Request to PegaProx timed out ({url})"
        except requests.RequestException as exc:
            return None, f"Request error: {exc}"

        # Check for offline cluster in 503 responses
        if resp.status_code == 503:
            try:
                body = resp.json()
                if body.get("offline"):
                    cluster = body.get("cluster", "unknown")
                    return None, f"Cluster '{cluster}' is offline or unreachable"
            except Exception:
                pass
            return None, f"PegaProx API returned 503: Service Unavailable"

        if not resp.ok:
            try:
                detail = resp.json().get("message") or resp.json().get("error") or resp.text
            except Exception:
                detail = resp.text or resp.reason
            return None, f"PegaProx API error {resp.status_code}: {detail}"

        if resp.status_code == 204 or not resp.content:
            return {}, None

        try:
            return resp.json(), None
        except Exception:
            return resp.text, None

    # Convenience helpers
    def get(self, path: str, **kwargs: Any) -> tuple[Any, str | None]:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> tuple[Any, str | None]:
        return self._request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> tuple[Any, str | None]:
        return self._request("DELETE", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> tuple[Any, str | None]:
        return self._request("PUT", path, **kwargs)


# Module-level singleton
client = PegaProxClient()
