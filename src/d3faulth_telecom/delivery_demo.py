"""Isolated end-to-end delivery exercise over a real localhost socket.

This deliberately tests receipt verification, NOT SS7/SCCP routing through
OsmoSTP. The results are labelled TRANSPORT-DEMO and must not be presented
as an OsmoSTP routing success.
"""
import json
import socket
import threading
import uuid
from .delivery import issue_receipt, verify_delivery

def run_delivery_demo(timeout=2):
    transaction = uuid.uuid4().hex
    payload = b"D3FAULTH-LOCAL-DELIVERY-PROBE"
    destination = "localhost-demo-destination"
    ready = threading.Event()
    listener_port = []
    error = []
    receipt = []

    def destination_worker():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
                srv.bind(("127.0.0.1", 0))
                srv.listen(1)
                srv.settimeout(timeout)
                listener_port.append(srv.getsockname()[1])
                ready.set()
                with srv.accept()[0] as incoming:
                    incoming.settimeout(timeout)
                    data = incoming.recv(4096)
                    if data == payload:
                        receipt.append(issue_receipt(transaction, destination, data))
        except OSError as exc:
            error.append(str(exc))
            ready.set()

    worker = threading.Thread(target=destination_worker, daemon=True)
    worker.start()
    if ready.wait(timeout) and listener_port and not error:
        try:
            with socket.create_connection(("127.0.0.1", listener_port[0]), timeout=timeout) as client:
                client.sendall(payload)
        except OSError as exc:
            error.append(str(exc))
    worker.join(timeout + .5)
    proof = verify_delivery(receipt[0] if receipt else None, transaction, destination, payload)
    return {"mode": "TRANSPORT-DEMO", "scope": "localhost", "protocol": "TCP",
            "not_ss7_routing": True, "transaction_id": transaction,
            "delivery": proof, "errors": error}
