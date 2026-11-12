"""Read-only USDT deposit observer.

This module detects already-mined Transfer logs sent to a configured public address.
It never creates, signs, broadcasts, or routes a transaction.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

UA = "Mozilla/5.0 (compatible; HandasaReadOnlyMonitor/1.0)"

LOG = logging.getLogger("deposit-monitor")
DEFAULT_RPC_FALLBACKS = (
    "https://ethereum-rpc.publicnode.com",
    "https://rpc.ankr.com/eth",
    "https://1rpc.io/eth",
)


TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55aebc7d3cbe"


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


def padded_address(address: str) -> str:
    value = address.lower().removeprefix("0x")
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("DEPOSIT_WALLET_ADDRESS must be a valid EVM address")
    return "0x" + ("0" * 24) + value


def discover_deposits(rpc_url: str, token_contract: str, wallet: str, from_block: int, to_block: int, decimals: int = 6) -> list[dict]:
    logs = rpc_call(rpc_url, "eth_getLogs", [{"address": token_contract, "fromBlock": hex(from_block), "toBlock": hex(to_block), "topics": [TRANSFER_TOPIC, None, padded_address(wallet)]}]) or []
    deposits = []
    for log in logs:
        amount = Decimal(int(log["data"], 16)) / (Decimal(10) ** decimals)
        block_number = int(log["blockNumber"], 16)
        deposits.append({"tx_hash": log["transactionHash"], "block": block_number, "amount_usdt": str(amount), "token_contract": token_contract, "wallet": wallet})
    return deposits


def read_state(path: str) -> set[str]:
    target = Path(path)
    if not target.exists():
        return set()
    return {line.strip() for line in target.read_text().splitlines() if line.strip()}


def append_deposits(path: str, deposits: list[dict], seen: set[str]) -> list[dict]:
    fresh = [deposit for deposit in deposits if deposit["tx_hash"] not in seen]
    if fresh:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            for deposit in fresh:
                row = {"observed_at": datetime.now(timezone.utc).isoformat(), **deposit}
                handle.write(json.dumps(row) + "\n")
    return fresh


def send_deposit_alert(webhook: str, deposit: dict, explorer_template: str) -> None:
    tx_url = explorer_template.format(tx_hash=deposit["tx_hash"])
    message = f"🔔 تم إيداع في المحفظة الفورية: {Decimal(deposit['amount_usdt']):,.6f} USDT بنجاح!"
    embed = {"title": "Instant wallet deposit observed", "description": message, "color": 5763719,
             "fields": [{"name": "Amount", "value": f"{deposit['amount_usdt']} USDT", "inline": True},
                        {"name": "Block", "value": str(deposit["block"]), "inline": True},
                        {"name": "Transaction", "value": f"[Open in explorer]({tx_url})", "inline": False}],
             "footer": {"text": "Read-only on-chain observation; no transfer was executed"},
             "timestamp": datetime.now(timezone.utc).isoformat(), "url": tx_url}
    request = urllib.request.Request(webhook, data=json.dumps({"allowed_mentions": {"parse": []}, "embeds": [embed]}).encode(), headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    with safe_urlopen(request) as response:
        if response.status >= 300:
            raise RuntimeError(f"Discord returned HTTP {response.status}")


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    try:
        urls = [item.strip() for item in os.environ.get("NETWORK_RPC_URLS", "").split(",") if item.strip()]
        primary = os.environ.get("NETWORK_RPC_URL", "").strip()
        if primary:
            urls.insert(0, primary)
        urls.extend(item for item in DEFAULT_RPC_FALLBACKS if item not in urls)
        wallet = os.environ.get("DEPOSIT_WALLET_ADDRESS", "").strip()
        token = os.environ.get("USDT_CONTRACT_ADDRESS", "").strip()
        if not wallet or not token:
            raise ValueError("deposit wallet or token is not configured")
        scan_blocks = max(1, int(os.environ.get("SCAN_BLOCKS", "5")))
        deposits = None
        errors = []
        for rpc_url in urls:
            try:
                latest = int(str(rpc_call(rpc_url, "eth_blockNumber", [])), 16)
                deposits = discover_deposits(rpc_url, token, wallet, max(0, latest - scan_blocks + 1), latest, int(os.environ.get("USDT_DECIMALS", "6")))
                break
            except Exception as exc:
                errors.append(f"{urlparse(rpc_url).netloc}: {exc}")
        if deposits is None:
            raise RuntimeError("all read-only RPC fallbacks failed: " + " | ".join(errors))
        fresh = append_deposits(os.environ.get("DEPOSIT_STATE_FILE", "data/deposits.jsonl"), deposits, read_state(os.environ.get("DEPOSIT_SEEN_FILE", "data/seen_deposits.txt")))
        seen_path = Path(os.environ.get("DEPOSIT_SEEN_FILE", "data/seen_deposits.txt"))
        seen_path.parent.mkdir(parents=True, exist_ok=True)
        with seen_path.open("a", encoding="utf-8") as handle:
            for deposit in fresh:
                handle.write(deposit["tx_hash"] + "\n")
        webhook = os.environ.get("DISCORD_WEBHOOK", "").strip()
        for deposit in fresh:
            LOG.info("Observed deposit: %s USDT at block %s", deposit["amount_usdt"], deposit["block"])
            if webhook:
                send_deposit_alert(webhook, deposit, os.environ.get("EXPLORER_TX_URL", "https://etherscan.io/tx/{tx_hash}"))
        return 0
    except Exception as exc:
        LOG.warning("Deposit monitor degraded read-only health check: %s", exc)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
