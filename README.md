# D3FAULTH // TELECOM LAB

A **terminal-first**, locally scoped telecom signaling observability prototype for Kali Linux.

> **v0.1 implements a loopback SCTP connection and M3UA ASPUP/ASPUP_ACK management exchange.** It does not implement a carrier interconnect, SS7 subscriber queries, MAP/TCAP transactions, SMS interception or RF signal decoding.

## Features

- Dark cyan retro terminal topology and route-status highlighting using Textual.
- Press **T** for SCTP/M3UA lab exchange; **F** to inject an acknowledgment failure (red route); **R** refresh events; **W** launch Wireshark separately; **Q** exit.
- JSONL event logs in `~/.local/state/d3faulth-telecom/`.
- `telecom doctor` checks dependencies. Works without SDR hardware.

## Install on Kali Linux

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip lksctp-tools wireshark
sudo modprobe sctp
git clone https://github.com/d3faulth-private/d3faulth-telecom.git
cd d3faulth-telecom
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[tui]'
telecom doctor
telecom
```

Commands: `telecom test`, `telecom fail`, `telecom events`, `telecom doctor`, `telecom wireshark`.

To inspect local SCTP packets in another terminal, run `sudo tshark -i lo -f 'sctp port 29055'` while running `telecom test`. Wireshark is a separate GUI process; its launch does not automatically start a capture.

## Scope

Network listeners bind exclusively to 127.0.0.1. No arbitrary-target scanning, carrier gateway connection, IMSI lookup, live subscriber tracking, or interception is implemented. Topology includes planned nodes marked unimplemented; health reflects actual localhost exchange outcomes.

## Roadmap

- Containerized STP lab with node-level metrics
- Packet capture ingestion and signaling diagnostics
- Synthetic MAP/TCAP and test subscriber flows
- Optional receive-only RF adapters for gr-gsm/Kalibrate and map data
- Optional 4G/5G core lab nodes

This is a separate repository and does not modify `pwntelecommunication`.
