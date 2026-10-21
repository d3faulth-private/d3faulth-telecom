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


## v0.4 persistent network core (development)

Unlike one-shot v0.3 tests, the v0.4 supervisor starts two persistent **loopback-only** SCTP endpoints (relay on 29061 and destination responder on 29062) and probes the real M3UA ASPUP/ACK path every two seconds. The dashboard displays current probe health only when fresh; if the supervisor stops or measurements are stale, the core state is OFF/STALE. This is **not** a carrier-connected STP, MSC, HLR, or MAP/TCAP service.

On Kali:

```bash
git fetch origin
git switch feature/v0.4-persistent-core
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
telecom core-start
telecom core-status
telecom
```

In the dashboard, press **S** to start the persistent lab and **Z** to stop it. Use `telecom core-stop` after testing; exiting the dashboard does not stop the persistent core. Existing `T` and `N` one-shot tests remain available. The topology colors are based on health measurements; gray denotes unverified or disconnected links.

To monitor the persistent endpoints in a separate terminal, use `sudo tshark -i lo -f 'sctp port 29061 or sctp port 29062'`; the earlier `C` shortcut still captures the v0.2 single-hop test on port 29055, not every persistent-core frame. PCAP counters only reflect the capture chosen by that shortcut, not the total core traffic. We will unify capture targets in a later version.

If the status stays DEGRADED, inspect `~/.local/state/d3faulth-telecom/persistent-stderr.log`. No SDR required. No carrier or subscriber interrogation endpoints are exposed.

## v0.5 Experimental OsmoSTP integration

This branch adds an **actual OsmoSTP** executable adapter with a loopback-only M3UA/SCTP listener on `127.0.0.1:29065`. It checks for an actual M3UA ASPUP_ACK reply, not just an open socket, and reports the OsmoSTP service independently from the custom v0.4 persistent relay. This is a first-step signaling gateway, **not** a complete telecom core: MSC, HLR, subscriber registration, SCCP routing, TCAP and MAP remain unimplemented.

### Kali test

```bash
git fetch origin
git switch feature/v0.5-osmostp
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
command -v osmo-stp || echo "Install osmo-stp from the Osmocom repository/packages"
telecom stp-start
telecom stp-status
telecom
```

In the dashboard, press **O** to start OsmoSTP and **Shift+O** to stop it. From the CLI run `telecom stp-stop` after testing. On failure check `~/.local/state/d3faulth-telecom/osmostp.log`. The M3UA configuration is written to `~/.local/state/d3faulth-telecom/osmo-stp.cfg` on start.

Do not run this service with privileges or expose Osmocom management/VTY endpoints outside loopback. If your installed Osmocom release rejects the supplied VTY syntax, stop and report the error; do not weaken the bind or remove access protections. Avoid running the older persistent relay on conflicting ports (v0.4 uses 29061/29062, this adapter uses 29065).

This development feature requires real validation on your Kali installation before merging. The current topology still depicts the custom persistent core, while the OsmoSTP health is separately displayed. No actual carrier signaling or live subscriber interrogation is included.

### v0.5 compatibility hotfix (OsmoSTP 2.1.0)

The OsmoSTP M3UA adapter now sends an explicit **SCTP PPID 3** using Linux `libsctp` instead of Python `sendall()`, which previously sent PPID 0. The custom one-shot tests use ports **29161/29162**, separate from the persistent core on **29061/29062**. The topology regression test now uses the renderer's minimum cell width.

On Kali, check `ldconfig -p | grep libsctp`; if absent install the appropriate system library package (`sudo apt install libsctp1 lksctp-tools`). To verify the new probe, ensure the *existing managed OsmoSTP* process is running, then run `telecom stp-status`. The updated Python probe is effective without restarting the OsmoSTP service. A successful `m3ua_ack` indicates **ASPUP_ACK only**, not an M3UA ACTIVE state or functioning SCCP/MAP service.

In the event of an unverified ACK, inspect `~/.local/state/d3faulth-telecom/osmostp.log`, and keep the service on 127.0.0.1. Do not forward ports to external networks. This fix is pending live validation on Kali.
