"""
Origin Intelligence API.

Provides manual IP investigation using the same Origin Analysis
engine used by the .eml analysis pipeline.
"""

from __future__ import annotations

import ipaddress

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.origin.config import load_config
from app.services.origin.service import OriginAnalysisService


router = APIRouter()


class OriginIpLookupRequest(BaseModel):
    ip: str


@router.post("/origin/lookup-ip")
async def lookup_ip(payload: OriginIpLookupRequest):
    """
    Investigate a single public IP through the Origin Analysis engine.
    """

    ip = payload.ip.strip()

    try:
        address = ipaddress.ip_address(ip)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid IP address.",
        ) from exc

    if not address.is_global:
        raise HTTPException(
            status_code=400,
            detail="Only public/global IP addresses can be investigated.",
        )

    service = OriginAnalysisService(load_config())

    try:
        result = await service.analyze(
            [f"from lookup ({ip}) by analyst with ESMTP"],
        )

        origin = result.get("origin") or {}
        trace = result.get("origin_trace") or {}
        risk = result.get("risk")

        return {
            "ip": ip,
            "origin": origin,
            "origin_trace": trace,
            "risk": risk,
            "correlation": result.get("correlation"),
            "cache_stats": result.get("cache_stats"),
        }

    finally:
        await service.close()
