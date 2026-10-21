# D3FAULTH // TELECOM LAB

**v0.2 development branch** — dense retro-terminal dashboard, original pixel equipment art, signaling status, event timelines, packet capture controls, and direct Wireshark launcher.

This is an **isolated loopback SCTP/M3UA lab**. It does not offer SS7 MAP interrogation, access to telecom carriers, subscriber location lookup, call/SMS interception, or radio decoding. Planned nodes are labeled accordingly.

## Install / upgrade on Kali

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip lksctp-tools wireshark tshark
sudo modprobe sctp
git clone -b feature/v0.2-dashboard https://github.com/d3faulth-private/d3faulth-telecom.git
cd d3faulth-telecom
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[tui,dev]'
telecom doctor
telecom
```

If already cloned: `git fetch origin && git switch feature/v0.2-dashboard && pip install -e '.[tui,dev]'`.

## Keys

| Key | Action |
| --- | --- |
| T | Run localhost SCTP/M3UA ASPUP/ACK exchange |
| F | Inject ACK failure in loopback test |
| C | Start recording SCTP packets on `lo`, port 29055 |
| X | Stop capture |
| W | Launch Wireshark GUI directly, loading selected PCAP if available |
| L | Toggle event log |
| D | Toggle diagnostics |
| R | Refresh data |
| Q | Quit and stop recording |

The capture requires permission to read loopback traffic. Configure normal Wireshark/dumpcap group permissions on Kali rather than running the whole TUI with sudo. Running `telecom capture` in a standalone terminal also works.

## Technical behavior

The existing M3UA v0.1 protocol codec and local transport test are preserved. The route color shows the most recent test outcome, **not a continuously established carrier signaling route**. Data from the tiny local test appears in the log and event visualization. The event graphs update from observed lab events per refresh and are not simulated carrier packet rates. PCAPs and event logs are stored under `~/.local/state/d3faulth-telecom`. Wireshark opens as a normal GUI process, with no unnecessary terminal window.

No standalone HLR/MSC/SMSC instances run in this version. Full per-service topology, continuously monitored links, and actual packet rate analysis remain future milestones.

## Check

```bash
python -m unittest discover -s tests -v
telecom doctor
telecom test
```

Repository: `d3faulth-private/d3faulth-telecom` (private). This branch is not yet merged into main.

## v0.3 experimental network-core branch

This development branch adds a **real three-process, two-hop SCTP/M3UA management-path test**. The processes are a loopback ASP client, an SCTP forwarding relay, and an ASPUP/ACK responder. All endpoints bind to 127.0.0.1. This proves two local signaling transport associations and forwarding, **not** a full STP/MSC/HLR service or MAP routing.

Install the branch on Kali:

```bash
git fetch origin
git switch feature/v0.3-network-core
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
telecom network-test
telecom network-fail
telecom
```

In the TUI press **N** to run the two-hop path test. Green or red route markers reflect the last test result; they are not continuous operational probes. For the local loopback v0.2 handshake, continue using **T**.

Traffic graphs remain **event-log-derived, not actual per-second packet rates**. The v0.3 next milestone is PCAP-derived metrics plus real OsmoSTP services; neither is claimed complete. No external carrier gateways or subscribers are connected.

