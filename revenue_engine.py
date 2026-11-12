"""Read-only network analytics and revenue-estimate reporter.

This project never signs, submits, routes, or transfers transactions. It does not
verify ownership, governance control, or entitlement to revenue.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

UA = "Mozilla/5.0 (compatible; HandasaReadOnlyMonitor/1.0)"

LOG = logging.getLogger("handasa-revenue-engine")
DEFAULT_RPC_FALLBACKS = (
    "https://ethereum-rpc.publicnode.com",
    "https://rpc.ankr.com/eth",
    "https://1rpc.io/eth",
)




def safe_urlopen(request: urllib.request.Request, timeout: int = 15):
    if urlparse(request.full_url).scheme.lower() not in {"http", "https"}:
        raise ValueError("only HTTP(S) URLs are allowed")
    return urllib.request.urlopen(request, timeout=timeout)  # nosec B310: scheme allowlist above


def rpc_call(rpc_url: str, method: str, params: list) -> object:
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    request = urllib.request.Request(rpc_url, data=payload, headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    with safe_urlopen(request) as response:
        result = json.loads(response.read().decode())
    if result.get("error"):
        raise RuntimeError(f"RPC error: {result['error']}")
    return result.get("result")


def get_latest_block(rpc_url: str) -> int:
    block = rpc_call(rpc_url, "eth_blockNumber", [])
    return int(str(block), 16)


def rpc_candidates() -> tuple[str, ...]:
    urls = [item.strip() for item in os.environ.get("NETWORK_RPC_URLS", "").split(",") if item.strip()]
    primary = os.environ.get("NETWORK_RPC_URL", "").strip()
    if primary:
        urls.insert(0, primary)
    urls.extend(item for item in DEFAULT_RPC_FALLBACKS if item not in urls)
    return tuple(urls)


def estimate_share(observed_volume_usd: Decimal, fee_percentage: Decimal) -> Decimal:
    """Calculate a clearly labeled estimate; this is not a claim of entitlement."""
    return observed_volume_usd * fee_percentage


def send_discord_report(webhook: str, report: dict) -> None:
    embed = {
        "title": "Handasa network analytics report",
        "color": 3447003,
        "description": "Read-only observation. No ownership, governance control, or revenue entitlement was verified.",
        "fields": [
            {"name": "Latest block", "value": str(report["block_number"]), "inline": True},
            {"name": "Observed volume input", "value": f"${report['observed_volume_usd']:,.2f} USD", "inline": True},
            {"name": "Illustrative estimate", "value": f"${report['estimated_share_usd']:,.2f} USD", "inline": True},
            {"name": "Status", "value": "Read-only / estimate only", "inline": False},
        ],
        "footer": {"text": "Handasa Revenue Engine • no transaction execution"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    request = urllib.request.Request(webhook, data=json.dumps({"allowed_mentions": {"parse": []}, "embeds": [embed]}).encode(), headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    with safe_urlopen(request) as response:
        if response.status >= 300:
            raise RuntimeError(f"Discord returned HTTP {response.status}")


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    try:
        urls = rpc_candidates()
        if not urls:
            raise ValueError("no RPC candidates configured")
        try:
            observed_volume = Decimal(os.environ.get("OBSERVED_VOLUME_USD", "0"))
            fee_percentage = Decimal(os.environ.get("FEE_PERCENTAGE", "0.005"))
        except InvalidOperation as exc:
            raise ValueError("OBSERVED_VOLUME_USD and FEE_PERCENTAGE must be numbers") from exc
        if observed_volume < 0 or fee_percentage < 0:
            raise ValueError("estimate inputs cannot be negative")
        errors = []
        block_number = None
        for rpc_url in urls:
            try:
                block_number = get_latest_block(rpc_url)
                break
            except Exception as exc:
                errors.append(f"{urlparse(rpc_url).netloc}: {exc}")
        if block_number is None:
            LOG.warning("RPC unavailable; emitting degraded read-only report: %s", " | ".join(errors))
            return 0
        report = {"block_number": block_number, "observed_volume_usd": observed_volume,
                  "estimated_share_usd": estimate_share(observed_volume, fee_percentage),
                  "governance_status": "not_verified", "mode": "read-only"}
        LOG.info("Read-only report: %s", json.dumps({k: str(v) for k, v in report.items()}))
        webhook = os.environ.get("DISCORD_WEBHOOK", "").strip()
        if webhook:
            send_discord_report(webhook, report)
        return 0
    except Exception as exc:
        LOG.warning("Revenue engine degraded read-only health check: %s", exc)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
