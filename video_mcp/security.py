"""Guards for untrusted input: URLs, downloads, filenames, secrets and subprocess environments."""
from __future__ import annotations

import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

SECRET_ENV = re.compile(r"(KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL|AUTH)", re.I)
# Field names that hold credentials (stricter than SECRET_ENV so cache keys, request keys and token *counts* survive).
SECRET_FIELD = re.compile(r"(api[_-]?key|secret|passw|^token$|access[_-]?token|auth[_-]?token|bearer|credential|private[_-]?key|download_token)", re.I)
SECRET_VALUE = re.compile(r"(sk-ant-[A-Za-z0-9_\-]{8,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}"
                          r"|(?:api[_-]?key|secret|token)[\"'=: ]+[A-Za-z0-9_\-:]{12,})", re.I)


class UnsafeURL(ValueError):
    pass


def check_url(url: str, *, resolve: bool = True, allowed_schemes=("https", "http")) -> str:
    """Reject non-HTTP schemes, credentials in URLs, and hosts that resolve to private/loopback/link-local space (SSRF)."""
    parsed = urlparse(url)
    if parsed.scheme not in allowed_schemes or not parsed.hostname:
        raise UnsafeURL(f"Unsupported URL: {url[:120]}")
    if parsed.username or parsed.password:
        raise UnsafeURL("URLs with embedded credentials are not allowed")
    host = parsed.hostname.lower()
    if host in ("localhost", "metadata.google.internal") or host.endswith((".local", ".internal")):
        raise UnsafeURL(f"Blocked host: {host}")
    addresses = []
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        if resolve:
            try:
                addresses = [ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host, None)]
            except socket.gaierror:
                addresses = []  # unresolvable here (e.g. behind a proxy); the HTTP client will fail on its own
    for address in addresses:
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast:
            raise UnsafeURL(f"Blocked non-public address for {host}")
    return url


def safe_name(text: str, limit: int = 60) -> str:
    """A filename component that cannot traverse directories."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip(".-")[:limit]
    return name or "file"


def inside(base: Path, candidate: Path) -> Path:
    """Resolve candidate and require it to stay within base."""
    base, resolved = base.resolve(), candidate.resolve()
    if resolved != base and base not in resolved.parents:
        raise ValueError(f"Path escapes {base}")
    return resolved


def redact(value):
    """Recursively scrub secret-looking strings and keys from data destined for logs, reports or MCP responses."""
    if isinstance(value, dict):
        return {k: ("[redacted]" if SECRET_FIELD.search(str(k)) and isinstance(v, str) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return SECRET_VALUE.sub("[redacted]", value)
    return value


def child_env(extra: dict | None = None, keep_secrets: bool = False) -> dict:
    """Environment for subprocesses (renderer, sandboxed builds) without API credentials."""
    env = {k: v for k, v in os.environ.items() if keep_secrets or not SECRET_ENV.search(k)}
    env.update(extra or {})
    return env


INJECTION = re.compile(r"(ignore (all|any|the)? ?(previous|prior|above) instructions|system prompt|you are now|"
                       r"<\s*/?\s*(system|assistant|instructions?)\s*>|call the tool|run this command)", re.I)


def neutralize(text: str, limit: int = 6000) -> str:
    """Untrusted text is data: trim it and defang common instruction-injection phrasing before it reaches a model."""
    return INJECTION.sub("[removed]", text or "")[:limit]
