"""Shared asyncpg SSL options for Supabase (pooler + direct)."""

from __future__ import annotations

import os
import ssl


def asyncpg_connect_args(
    database_url: str,
    *,
    ssl_insecure: bool = False,
) -> dict:
    u = database_url.lower()
    if "supabase" not in u:
        return {}
    if ssl_insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return {"ssl": ctx}
    return {"ssl": True}


def asyncpg_connect_args_from_env() -> dict:
    url = os.environ.get("DATABASE_URL", "")
    insecure = os.environ.get("DATABASE_SSL_INSECURE", "").lower() in (
        "1",
        "true",
        "yes",
    )
    return asyncpg_connect_args(url, ssl_insecure=insecure)
