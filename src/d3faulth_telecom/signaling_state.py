"""Explicit M3UA management state model for isolated signaling experiments.

Transport, ASP-UP and ASP-ACTIVE are deliberately separate.
A successful ASPUP_ACK never implies routing or SCCP delivery.
"""
from dataclasses import dataclass, asdict

M3UA_ASPSM = 3
M3UA_ASPTM = 4
NAMES = {
    (3, 1): "ASPUP", (3, 4): "ASPUP_ACK",
    (3, 2): "ASPDN", (3, 5): "ASPDN_ACK",
    (3, 3): "BEAT", (3, 6): "BEAT_ACK",
    (4, 1): "ASPAC", (4, 3): "ASPAC_ACK",
    (4, 2): "ASPIA", (4, 4): "ASPIA_ACK",
}

@dataclass
class State:
    sctp: str = "UNKNOWN"
    asp: str = "DOWN"
    routing: str = "UNVERIFIED"
    last_message: str = "NONE"
    error: str | None = None

    def transport(self, connected: bool):
        self.sctp = "ESTABLISHED" if connected else "DISCONNECTED"
        if not connected:
            self.asp = "DOWN"
            self.routing = "UNVERIFIED"

    def observe(self, message_class: int, message_type: int):
        name = NAMES.get((message_class, message_type), "UNKNOWN")
        self.last_message = name
        if self.sctp != "ESTABLISHED":
            self.error = "M3UA event seen without verified SCTP"
            return
        if name == "ASPUP_ACK":
            self.asp = "UP"
        elif name == "ASPAC_ACK":
            if self.asp == "UP":
                self.asp = "ACTIVE"
            else:
                self.error = "ASPAC_ACK without prior ASPUP_ACK"
        elif name in ("ASPDN_ACK", "ASPIA_ACK"):
            self.asp = "DOWN" if name == "ASPDN_ACK" else "UP"
            self.routing = "UNVERIFIED"

    def verify_route(self, delivery_result):
        from .delivery import route_health
        self.routing = route_health(delivery_result, self.sctp, self.asp)
        return self.routing

    def snapshot(self):
        return asdict(self)
