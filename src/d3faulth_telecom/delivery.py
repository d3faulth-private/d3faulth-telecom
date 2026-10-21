"""Delivery proof from an isolated destination receipt, never from ASPAC_ACK.

Accept only lab-produced transaction receipts. Unverified or expired receipts
cannot make a signaling route appear healthy.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import time

MAX_AGE_SECONDS = 10

@dataclass(frozen=True)
class DeliveryReceipt:
    transaction_id: str
    destination: str
    payload_sha256: str
    received_at: float
    delivered: bool

def issue_receipt(transaction_id, destination, payload):
    if not transaction_id or not destination or not isinstance(payload, bytes):
        raise ValueError("Invalid lab receipt")
    return DeliveryReceipt(transaction_id, destination,
                           hashlib.sha256(payload).hexdigest(), time.time(), True)

def verify_delivery(receipt, expected_id, expected_destination, expected_payload,
                    now=None):
    """Verify explicit receipt identity, destination, content and freshness."""
    if receipt is None or not isinstance(receipt, DeliveryReceipt):
        return {"status": "UNVERIFIED", "reason": "No destination receipt"}
    now = time.time() if now is None else now
    if not receipt.delivered:
        return {"status": "FAILED", "reason": "Destination rejected delivery"}
    if receipt.received_at > now + 1 or now - receipt.received_at > MAX_AGE_SECONDS:
        return {"status": "UNVERIFIED", "reason": "Receipt outside freshness window"}
    if receipt.transaction_id != expected_id or receipt.destination != expected_destination:
        return {"status": "FAILED", "reason": "Receipt does not match target"}
    expected_hash = hashlib.sha256(expected_payload).hexdigest()
    if not hmac.compare_digest(receipt.payload_sha256, expected_hash):
        return {"status": "FAILED", "reason": "Destination payload mismatch"}
    return {"status": "VERIFIED", "reason": "Destination receipt matches transaction"}

def route_health(delivery_result, transport="UNVERIFIED", asp="UNVERIFIED"):
    if delivery_result.get("status") == "VERIFIED" and transport == "ESTABLISHED" and asp == "ACTIVE":
        return "HEALTHY"
    if delivery_result.get("status") == "FAILED":
        return "FAILED"
    return "UNVERIFIED"
