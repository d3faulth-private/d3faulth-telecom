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

## v0.7 experimental signaling integration

This branch introduces the first **packet-backed OsmoSTP management test**. It is not yet a routed SS7 DATA integration.

```bash
git fetch origin
git switch feature/v0.7-signaling-integration
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
telecom stp-status
telecom verify-stp-capture
```

`verify-stp-capture` launches a short tshark recording of **loopback SCTP port 29065**, executes the existing M3UA ASPUP / ASPAC activation probe against the managed OsmoSTP service, and reads its recorded M3UA management acknowledgments. It requires tshark/dumpcap capture permissions. Recorded PCAPs are saved under `~/.local/state/d3faulth-telecom/osmostp-captures/` and are not uploaded.

`verified_management_exchange` is set only when the activation probe reports ACTIVE **and** the capture contains both ASPUP_ACK and ASPAC_ACK. `ss7_data_routing` stays UNVERIFIED and `ss7_data_route_healthy` stays false. The next milestone is independently configured lab data endpoints routed through OsmoSTP and matching destination receipt. No external carrier access or subscriber-data lookups are implemented.

## v0.8 experimental local M3UA DATA route test

This isolated test creates two actual SCTP ASP connections bound to `127.0.0.2` and `127.0.0.3`, sends only the built-in synthetic M3UA DATA marker using fixed lab point codes 23 and 42, and listens for the same bytes on the second association. Simultaneously it captures `lo` traffic to the managed OsmoSTP listener on `127.0.0.1:29065`.

```bash
git fetch origin
git switch feature/v0.8-local-data-route
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
telecom stp-status
telecom local-data-route
```

**No arbitrary targets, identifiers, or payloads are supported.** `route_healthy: true` requires the matching payload to arrive on the destination association and at least two M3UA DATA frames to appear in the local PCAP. A successful ASPAC acknowledgment alone never marks the route healthy.

**Important:** An already running OsmoSTP with only dynamic ASP acceptance may not have usable AS routing keys or destination point-code routes. If so, the test reports UNVERIFIED; it does not silently rewrite the running STP's configuration. Use operator-documented Osmocom test AS/ASP routing-key configuration in a separately managed isolated environment before repeating. This experimental stage has not been verified against Kali yet.

Source information: Osmocom OsmoMSC manual sections on CS7 instance, ASP/AS, routing keys, and OsmoSTP M3UA, and Osmocom osmo-stp example configurations.

### DATA stream compatibility correction

Your Kali capture showed 10 negotiated outbound/inbound SCTP streams, a synthetic M3UA DATA frame sent on stream 0, and OsmoSTP M3UA ERR code 9 (Invalid Stream Identifier). The laboratory sender now places ASPUP/ASPAC on stream 0 and the fixed synthetic M3UA DATA message on stream 1 with PPID 3. It also inspects an immediate source-association response for a management ERR and includes it under `m3ua_error` when received.

Update and verify:

```bash
git pull origin feature/v0.8-local-data-route
source .venv/bin/activate
python -m unittest discover -s tests -v
telecom stp-status
telecom local-data-route
```

This corrects the stream selection only. If OsmoSTP still cannot route to point code 42, the destination's local Application Server and routing-key configuration remain unverified. Do not equate ASP ACTIVE or a single ingress DATA frame with successful delivery. The new code has not been live-tested on Kali; `main` remains unchanged.

## v0.8.1 routing configuration audit

Use `telecom routing-audit` to review the existing local OsmoSTP configuration and recent logs without restarting, reconfiguring or sending any traffic. It reports explicit AS/ASP definitions, routing contexts, point codes and the observed `unable to uniquely identify the AS` diagnostic. It does **not** establish that configured routes actually function.

```bash
git fetch origin
git switch feature/v0.8.1-routing-audit
source .venv/bin/activate
python -m unittest discover -s tests -v
telecom routing-audit
```

The auditor is static, uses conservative error classifications and always leaves signaling routing UNVERIFIED. It never modifies or generates an OsmoSTP configuration.

## v0.8.2 — Isolated AS/ASP manifest validation

This read-only feature compares the existing OsmoSTP configuration with a fixed two-ASP **expectation manifest** (source `127.0.0.2` point code 23 / routing context 100; destination `127.0.0.3` point code 42 / routing context 200; STP `127.0.0.1:29065`). These are **expected test values**, not claims about the current configuration.

```bash
git fetch origin
git switch feature/v0.8.2-as-validation
source .venv/bin/activate
python -m unittest discover -s tests -v
telecom as-validate | tee /tmp/as-before.json
# After independently approved and tested lab configuration changes:
telecom as-validate | tee /tmp/as-after.json
telecom as-compare /tmp/as-before.json /tmp/as-after.json
```

No services are restarted or modified. This text comparison highlights missing AS declarations, routing contexts and point codes, but cannot verify runtime routing or whether a routing key is associated with the correct ASP. The command deliberately returns `configuration_ready: false` and leaves the route UNVERIFIED until a separately verified end-to-end delivery test is available.

## v0.8.3 — configuration safety and rollback

This is a conservative **configuration validation checkpoint**. The local OsmoSTP instance is not modified unless the operator explicitly invokes `config-restore`; this branch never generates or installs an AS/ASP routing configuration.

```bash
git fetch origin
git switch feature/v0.8.3-config-safety
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
telecom config-preflight
telecom config-backup
```

`config-preflight` checks static loopback binding, VTY risk indicators, expected lab AS/ASP and point-code definitions and logs; `configuration_ready` remains false until separately verified. Backups are timestamped, integrity-labelled and permission-restricted under `~/.local/state/d3faulth-telecom/config-backups`. To check a saved backup, run `telecom config-verify-backup PATH`.

**Explicit restore procedure (only if needed):** stop the managed OsmoSTP separately with `telecom stp-stop`, review the intended backup and current file checksum, then run `telecom config-restore BACKUP --expect-current-sha256 CURRENT_SHA256`. Restore refuses to overwrite when the service is reported running, the backup hash mismatches, or the current file has changed since review. It does **not** restart OsmoSTP. Config syntax compatibility must still be checked against the installed OsmoSTP version before deployment. Do not manually expose M3UA or VTY outside 127.0.0.1.

The current release supports static validation and backup safety, **not verified end-to-end SS7 DATA routing**. The latter remains UNVERIFIED until an actual isolated destination receives the test DATA and corresponding captures are validated.

## Phase 1 — candidate routing preflight (not yet operational)

This development branch adds an **offline review-only** candidate configuration for two isolated loopback ASPs and a version-aware VTY command reference checker. It deliberately does not touch the managed running OsmoSTP or its backups.

```bash
git fetch origin
git switch feature/phase1-routing-preflight
source .venv/bin/activate
pip install -e '.[tui,dev]'
python -m unittest discover -s tests -v
telecom phase1-reference-check /tmp/osmostp-vty-reference.xml
telecom phase1-candidate
```

The candidate is saved once to `~/.local/state/d3faulth-telecom/candidates/osmo-stp-phase1.cfg`. Read it with `cat`; the command refuses to overwrite an existing file. The candidate proposes a separate M3UA listener on 127.0.0.1:29165 with synthetic point codes 23, 42 and routing contexts 100, 200. Static configuration and VTY-command checks do **not** prove that OsmoSTP accepts the complete config, that its ASP port mapping is correct, or that DATA can reach the receiver.

**Do not start or install this candidate yet.** An isolated startup needs VTY port isolation too (the default VTY listener may conflict), and the ASP-to-route semantics must be validated against OsmoSTP 2.1.0 on Kali. The existing osmo-stp.cfg and running service should remain unchanged. Neither routing nor end-to-end delivery is verified.

### Candidate listener correction (Phase 1)
OsmoSTP 2.1.0 VTY reference confirms `bind A.B.C.D [PORT]` and `accept-asp-connections (pre-configured|dynamic-permitted)`. Candidate now uses VTY `127.0.0.1:4240`, M3UA `127.0.0.1:29165`, and `accept-asp-connections pre-configured`. The routing-key allocation policy separately remains `static-only`.

**If you already generated the earlier candidate**, preserve it before creating a replacement:

```bash
old="$HOME/.local/state/d3faulth-telecom/candidates/osmo-stp-phase1.cfg"
mv -n "$old" "${old}.prior-review"
telecom phase1-candidate
```

Inspect the new file and rerun tests. Never launch the candidate as a second service until syntax and port isolation are verified in the installed environment. This branch still makes no live routing claim.

### Kali point-code parse checkpoint
An isolated 8-second startup test against installed OsmoSTP 2.1.0 accepted `point-code 0.0.1`, `routing-key 100 0.2.7`, and `routing-key 200 0.5.2`; the process exited from the intended timeout (124). OsmoSTP emitted `ASP Restart for server not implemented yet!` for each static ASP. This validates startup parsing only, **not** M3UA association or DATA delivery. The generated candidate still requires isolated listener and end-to-end tests. Preserve prior candidate files when regenerating.

### Phase 1 association verification (separate candidate only)

`telecom phase1-associations` probes the fixed local destination `127.0.0.1:29165` using individual SCTP sockets bound to `127.0.0.2` and `127.0.0.3`. It attempts ASPUP and ASPAC management exchanges, records observed ACK types or failures separately, and **never** sends M3UA DATA. Each record and the summary keep `routing: UNVERIFIED` regardless of ACK success. Static ASP association/port matching may fail; logs must determine why.

Start the validated candidate temporarily in one shell and probe during its lifetime in another:

```bash
# Terminal 1 — only this isolated candidate, not the managed primary:
candidate="$HOME/.local/state/d3faulth-telecom/candidates/osmo-stp-phase1-pc3-test.cfg"
timeout --signal=TERM --kill-after=3s 35s osmo-stp -c "$candidate" > /tmp/osmostp-phase1-associations.log 2>&1
```

```bash
# Terminal 2 — run promptly while terminal 1 is active:
telecom phase1-associations
```

Then review `/tmp/osmostp-phase1-associations.log` and `telecom stp-status`. A clean management ACK is not evidence of AS membership or forwarding. If binding/activation fails, **do not** adapt addresses to external networks. Capture local logs for diagnosis. Main and the original managed config are unchanged.

### Unexpected M3UA activation response details

The `telecom phase1-associations` probe now returns `response_details` for each management response (message name, class, type, length and raw hex). Unexpected responses additionally populate `unexpected_response`, and M3UA ERR frames expose the parsed numeric error code and a best-effort description from the existing decoder. Keep numeric codes and raw bytes as the primary evidence when debugging; mapping descriptions may need independent standards verification.

Use the same bounded, isolated candidate startup documented above, then run `telecom phase1-associations` from the activated project's virtual environment while it is listening. This change sends no DATA and does not make routing healthy.

### Phase 1 NOTIFY-aware management probe
The association probe recognizes M3UA NOTIFY (class 0/type 1), parses status and routing-context parameters, and waits up to 3 seconds / 12 responses per handshake stage for the expected ACK. It retains an ordered `responses` list of names and `response_details` records with raw packet hex, while reporting M3UA ERR separately. NOTIFY with status 1/2 is displayed as AS_INACTIVE. Use the same two-terminal, bounded candidate startup as above. No M3UA DATA is sent and routing remains UNVERIFIED.

### Concurrent management and synthetic DATA test (Phase 1)

After running unit tests, launch the isolated, parser-tested candidate on `127.0.0.1:29165` for a bounded period in Terminal 1. Do not modify the managed service on port 29065:

```bash
candidate="$HOME/.local/state/d3faulth-telecom/candidates/osmo-stp-phase1-pc3-test.cfg"
timeout --signal=TERM --kill-after=3s 40s osmo-stp -c "$candidate" > /tmp/osmostp-phase1-concurrent.log 2>&1
```

In Terminal 2, while the candidate is listening:

```bash
cd ~/d3faulth-telecom
source .venv/bin/activate
telecom phase1-concurrent
# Optional: rerun bounded candidate start and then execute:
telecom phase1-proof
```

The first command keeps destination and source SCTP associations open together, validates ASPUP_ACK/ASPAC_ACK for each, sends the fixed synthetic M3UA DATA marker from point code 23 to 42, and verifies actual destination socket receipt. It never controls a service or contacts off-loopback addresses. The second command captures only loopback SCTP port 29165 with tshark, then checks for at least two decoded M3UA DATA frames and receiver receipt. This is corroboration, not exhaustive per-packet cryptographic correlation. Check the returned `delivery`, `data_frames`, and OsmoSTP log before any merge. If the test fails, routing stays UNVERIFIED; status must not be inferred from ASP activation alone. A non-running candidate causes a connection failure, not a fallback to the primary service.

### Phase 1 post-DATA diagnostics

`telecom phase1-concurrent` now records a `post_data_responses` object with separate `source` and `destination` ordered arrays. For M3UA ERROR and NOTIFY frames, records include class, type, raw hex, decoded error code or NOTIFY status and routing contexts. Unexpected DATA or malformed responses are preserved as evidence rather than silently ignored. No routing context is added to outgoing DATA by this change; OsmoSTP configuration is unchanged. Receiver receipt alone does not mark PCAP or routing as verified. Start the bounded isolated OsmoSTP candidate first and rerun this command while the candidate is listening.

### Live 15-second AS/route observation

Run the isolated candidate on 127.0.0.1:29165 / VTY 127.0.0.1:4240, ensuring no other candidate occupies these ports. From a second terminal run `telecom phase1-concurrent --observe-seconds 15`. After both ASPAC acknowledgments the command prints a readiness message and **holds both SCTP associations open for 15 seconds before sending the synthetic DATA message**. While the pause is active, connect via `telnet 127.0.0.1 4240` from another terminal and enter:

```
show cs7 instance 0 as active
show cs7 instance 0 asp
show cs7 instance 0 route
```

The pause is bounded between 0 and 30 seconds and the sockets close afterward. Save VTY output before the pause ends; AS_DOWN after the process finishes is expected. Neither the primary managed OsmoSTP nor its configuration is changed. The observation window proves neither delivery nor packet capture; routing stays UNVERIFIED until actual corroborating evidence exists.

### Phase 1 route-table preflight

The observed OsmoSTP log `MTP-TRANSFER.req for DPC 42: no route!` and the empty `show cs7 instance 0 route` establish that the isolated test did not find an MTP forwarding route. The route-key declarations alone do not prove such a route exists.

Run `telecom phase1-routes --reference /tmp/osmostp-vty-reference.xml` to compare the candidate's explicit route entries against point codes 0.2.7 and 0.5.2 and check whether the installed VTY supports `update route POINT_CODE MASK linkset LS_NAME` inside `config-cs7-rt`. This is a **read-only** audit. It intentionally does not generate an executable route candidate yet: the appropriate mask notation and whether the AS name can serve as a linkset target must first be verified for installed OsmoSTP 2.1.0. Neither primary nor candidate service is modified; forwarding and DATA receipt remain unverified.
