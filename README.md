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

## v0.6 experimental signaling-state groundwork

The first v0.6 increment introduces an explicit protocol state model with three separate concepts: **SCTP established**, **M3UA ASP UP**, and **M3UA ASP ACTIVE**. An ASPUP_ACK proves ASP UP only; it does not establish ASP ACTIVE or routing.

```bash
git fetch origin
git switch feature/v0.6-signaling-core
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
telecom signaling-state
```

`telecom signaling-state` checks the managed localhost OsmoSTP adapter. It reports observed ASPUP_ACK as `UP`, and always leaves routing `UNVERIFIED`. Actual ASPAC/ACK exchange, routing contexts, SCCP and TCAP decoding, multiple real Osmocom nodes and packet rate metrics are **not yet implemented**. Do not equate this state-model groundwork with a complete v0.6 network.

### v0.6 Phase 2: one-shot ASP activation verification

With the managed, localhost-only OsmoSTP running:

```bash
git pull origin feature/v0.6-signaling-core
source .venv/bin/activate
python -m unittest discover -s tests -v
telecom asp-activate-test
telecom
```

Press **A** in the TUI to run the same isolated protocol-state test. It sends ASPUP and (after receiving ASPUP_ACK) ASPAC on **one SCTP association**, using M3UA PPID 3. It reports ASP ACTIVE only on receipt of a genuine ASPAC_ACK; failures and unexpected messages remain unverified. The transaction ends after the check. No packet DATA, routing verification, subscriber lookup or MAP procedures are implemented. Dynamic OsmoSTP associations may require additional AS/routing-context configuration before activation is accepted. Do not expose signaling interfaces or change the loopback binding.

This increment is awaiting Kali integration verification; it is not merged into main.

### v0.6 Phase 3 (first increment): destination proof gate

An ASPUP_ACK or ASPAC_ACK **cannot** mark an SS7 route HEALTHY. The new delivery proof gate requires matching transaction ID, destination identity, payload hash, receipt freshness, SCTP ESTABLISHED, and ASP ACTIVE.

`telecom delivery-demo` demonstrates a **real localhost TCP transfer** to an independently running local receiver and validates the resulting receipt. It is deliberately labelled `TRANSPORT-DEMO`, **not SS7 routing through OsmoSTP**. The dashboard displays `SS7 ROUTING: UNVERIFIED` until an actual routed M3UA DATA transfer with destination receipt is implemented and verified.

```bash
git fetch origin
git switch feature/v0.6-signaling-core
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
telecom delivery-demo
telecom
```

Phase 3 is incomplete: configuring independent ASP/AS endpoints, OsmoSTP point-code routing, a supported SS7 data transfer, capture correlation, and returned destination receipt are the next tasks. No live-carrier routes or subscriber operations are enabled.

### v0.6 Phase 3B: passive lab evidence audit

New `telecom route-audit FILE.jsonl` command correlates timestamped events from two explicitly named **synthetic lab checkpoints**, `lab-source` (sent) and `lab-destination` (received), matching transaction ID, SHA-256 payload digest and timing window.

Example lab evidence file (illustrative values, not real signaling captures):

```jsonl
{"transaction_id":"lab-01","node":"lab-source","direction":"sent","payload_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","timestamp":1.0}
{"transaction_id":"lab-01","node":"lab-destination","direction":"received","payload_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","timestamp":1.2}
```

The command reports `CORRELATED` only for a unique matching pair. It **always reports `osmostp_routing: UNVERIFIED`** because correlated checkpoint records alone cannot prove forwarding through OsmoSTP. A future stage must gather verified, packet-level M3UA DATA evidence with a destination receipt, in the isolated test network, before declaring a signaling route healthy.

To test: `python -m unittest discover -s tests -v` and `telecom route-audit path/to/lab-evidence.jsonl`. This increment does not send telecom messages, modify signaling configuration, or connect to subscribers.

### Phase 3C evidence gate (work in progress)

Run `telecom route-proof /path/to/route-observations.json` to audit a JSON array containing exactly one `source-tx`, `stp-rx`, `stp-tx` and `destination-rx` record for the same synthetic test transaction. Each record requires `transaction_id`, `stage`, `protocol: "M3UA-DATA"`, `payload_sha256` (64 lowercase hexadecimal characters) and a timestamp. STP ingress/egress records must include `capture_file` and `frame_number`; destination must include `receipt_verified: true`.

The verifier checks ordering, hashes, uniqueness and destination evidence. Its most favorable result is `EVIDENCE_COMPLETE`, with `route_healthy: false`, since references to PCAP frames can be supplied without the files and therefore cannot independently prove actual forwarding. A future capture-aware verifier must open those captures and validate packet contents and interface attribution before the dashboard can display a verified green OsmoSTP route.

No real OsmoSTP M3UA DATA forwarding is implemented by this commit. `main` is unchanged. To test locally, run `python -m unittest discover -s tests -v`.

### Phase 3D: PCAP evidence checks (development)

The `telecom pcap-proof EVIDENCE.json CAPTURES_DIRECTORY` command opens explicitly supplied lab PCAPs using tshark and verifies referenced STP M3UA DATA frame numbers and SCTP PPID 3. It requires four stage records previously defined by `route-proof`. It **does not** send M3UA messages, configure OsmoSTP routing, or independently prove the payload or capture origin. Its strongest result is `CAPTURE_CORRELATED`, with `route_healthy: false`. Real STP forwarding and independently verified destination delivery still require an isolated multi-ASP integration exercise.

For Kali testing:
```bash
git fetch origin
git switch feature/v0.6-phase3d
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
telecom pcap-proof --help
```

Capture files must remain local and are never uploaded by this feature. `main` is not modified.

## v0.6 consolidated verification branch

This branch adds a single read-only readiness command:

```bash
git fetch origin
git switch feature/v0.6-completion
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
telecom verify-lab
```

The command checks managed OsmoSTP process state, M3UA ASPUP_ACK, same-association ASPAC_ACK, and tshark/Wireshark installation. It never reports an SS7 route healthy based solely on an activation exchange. `ss7_data_routing` remains `UNVERIFIED` until real lab DATA forwarding and independently confirmed destination receipt are both observed.

**Known gap:** This increment does not itself provision a second OsmoSTP-connected ASP or run M3UA DATA through OsmoSTP. It is a consolidated diagnostic baseline for that integration, not completed Phase 3D routing. The branch is intentionally unmerged.
