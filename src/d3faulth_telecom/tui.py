"""D3FAULTH Telecom Lab v0.2 — real-event terminal dashboard."""
from collections import deque
from datetime import datetime, timezone
import time
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Static, RichLog
from textual.containers import Horizontal, Vertical
from textual import work
from rich.text import Text
from .lab import run_exchange, recent_events
from . import capture, persistent
from .topology import topology_render

SPRITES = {
    "MSC": (" ┏━━━━━━┓ ", " ┃ ▣  ▣ ┃ ", " ┗━┳━━┳━┛ "),
    "STP": (" ┏━━━━━━┓ ", " ┃ ▤▤▤▤ ┃ ", " ┗━┳━━┳━┛ "),
    "HLR": (" ┏━━━━━━┓ ", " ┃ ▥▥▥▥ ┃ ", " ┗━┳━━┳━┛ "),
    "SMSC":(" ┏━━━━━━┓ ", " ┃ ▣▤▣▤ ┃ ", " ┗━┳━━┳━┛ "),
}
SPARK = "▁▂▃▄▅▆▇█"

class TelecomApp(App):
    TITLE = "D3FAULTH // TELECOM LAB"
    SUB_TITLE = "SIGNALING OPERATIONS • v0.4"
    CSS = """
    Screen { background: #070e13; color: #b6dadd; }
    Header, Footer { background: #14222b; color: #4ad9ed; }
    #brand { height: 3; text-align: center; content-align: center middle; color: #42dce5; text-style: bold; background: #071821; }
    #tabs { height: 3; color: #79c8cd; content-align: center middle; border-bottom: solid #1e6170; }
    #status { height: 3; color: #f3c36e; border: round #226676; padding: 0 1; }
    #middle { height: 17; }
    #topology { width: 2fr; height: 100%; border: round #29a9b6; padding: 1 2; }
    #telemetry { width: 1fr; height: 100%; border: round #295962; padding: 1 2; }
    #bottom { height: 1fr; min-height: 10; }
    #logs { width: 2fr; border: round #268996; padding: 0 1; }
    #details { width: 1fr; border: round #295962; padding: 1 2; }
    #log { height: 1fr; }
    .section { height: 2; color: #51d7e0; text-style: bold; }
    """
    BINDINGS = [
        Binding("t", "test", "Test"),
        Binding("n", "network_test", "Two-hop network"),
        Binding("s", "core_start", "Start persistent core"),
        Binding("z", "core_stop", "Stop persistent core"),
        Binding("shift+n", "network_fault", "Two-hop fault"),
        Binding("f", "fail", "Fault"),
        Binding("c", "capture_start", "Capture"),
        Binding("x", "capture_stop", "Stop capture"),
        Binding("w", "wireshark", "Wireshark"),
        Binding("l", "logs", "Logs"),
        Binding("d", "details", "Diagnostics"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit")
    ]
    def __init__(self):
        super().__init__()
        self.route = "UNTESTED"
        self.last_at = "NEVER"
        self.last_error = "None"
        self.rates = deque([0] * 18, maxlen=18)
        self.show_logs = True
        self.show_details = True
        self._seen = 0
        self.path = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("▣  D3FAULTH  //  TELECOM LAB  ▣    SIGNALING OPERATIONS CONTROL CENTER", id="brand")
        yield Static(" [01 TOPOLOGY]    [02 SCTP / M3UA]    [03 CAPTURE]    [04 RF: NOT CONNECTED] ", id="tabs")
        yield Static(id="status")
        with Horizontal(id="middle"):
            yield Static(id="topology")
            yield Static(id="telemetry")
        with Horizontal(id="bottom"):
            with Vertical(id="logs"):
                yield Static("┌─ LIVE SIGNALING EVENTS", classes="section")
                yield RichLog(id="log", markup=True, highlight=False, max_lines=250)
            with Vertical(id="details"):
                yield Static(id="diagnostics")
        yield Footer()

    def on_mount(self):
        self.set_interval(1.0, self.refresh_view)
        self.refresh_view()
        self.write_log("[cyan]Ready. Press T to verify the local SCTP/M3UA exchange.[/cyan]")

    def write_log(self, text):
        self.query_one("#log", RichLog).write(text)

    def refresh_view(self):
        events = recent_events(120)
        fresh = events[max(0, len(events) - self._seen):]
        for e in fresh:
            kind = e["kind"].upper()
            color = "red" if kind in ("ERROR", "FAULT") or e.get("status") == "FAILED" else "green" if kind in ("LINK", "ROUTE") else "cyan"
            self.write_log(f"[{color}]{e['at'][11:19]} [{kind}] {e['message']}[/{color}]")
        self._seen = len(events)
        self.rates.append(sum(1 for e in fresh if e["kind"] in ("send", "recv")))
        core = persistent.state()
        live_routes = core.get("routes", [])
        current = bool(core["running"] and core.get("observed_at")
                       and time.time() - core["observed_at"] < 7
                       and len(live_routes) == 2)
        live_path = None
        if current:
            first, second = live_routes[1], live_routes[0]
            both = first["status"] == "HEALTHY" and second["status"] == "HEALTHY"
            live_path = {"status": "HEALTHY" if both else "FAILED",
                         "segments": [first, second]}
        top_width = max(64, self.query_one("#topology", Static).size.width - 6)
        self.query_one("#topology", Static).update(
            topology_render(top_width, self.route, live_path if current else self.path))
        color = "green" if self.route == "HEALTHY" else "red" if self.route == "FAILED" else "grey62"
        cap = capture.status()
        self.query_one("#status", Static).update(
            f" MODE: LOCAL LAB   •   SINGLE-HOP: {self.route}   •   TWO-HOP: {self.path['status'] if self.path else 'UNTESTED'}"
            f"   •   CORE: {'LIVE' if current else 'OFF/STALE'}   •   CAPTURE: {'ON' if cap['active'] else 'OFF'}")
        values = list(self.rates)
        chart = "".join(SPARK[min(7, n)] for n in values)
        packets = capture.packet_metrics()
        self.query_one("#telemetry", Static).update(
            f"[bold cyan]┌─ LIVE TELEMETRY[/bold cyan]\n\n"
            f"  LAB EVENT COUNTER (NOT PCAP)\n  [green]{chart}[/green]\n  {values[-1]} logged events in sample\n\n"
            f"  PCAP SCTP FRAMES: {packets['count'] if packets['count'] is not None else 'N/A'}\n"
            f"  PERSISTENT CORE: {'HEALTHY' if current and live_path['status'] == 'HEALTHY' else 'DEGRADED' if current else 'OFF'}\n"
            f"  ASPUP/ACK: [{color}]{self.route}[/{color}]\n  CAPTURE: {'ON' if cap['active'] else 'OFF'}\n"
            f"  SCCP: NOT INSTALLED\n  TCAP: NOT INSTALLED\n  MAP: NOT INSTALLED\n"
            f"  SDR: NOT DETECTED")
        self.query_one("#diagnostics", Static).update(
            "[bold cyan]┌─ ROUTE DIAGNOSTICS[/bold cyan]\n\n"
            f" TRANSPORT: SCTP\n ENDPOINT: loopback\n PORT: 29055\n"
            f" SINGLE-HOP: {self.route}\n TWO-HOP: {self.path['status'] if self.path else 'UNTESTED'}\n LAST VERIFIED: {self.last_at}\n"
            f" CORE: {'LIVE' if current else 'OFF/STALE'}\n"
            f" ERROR: {self.last_error[:42]}\n\n"
            f" CAPTURE FILE:\n {str(cap['file'] or 'None')[-38:]}\n\n"
            " S core start  Z core stop\n T test  F fault\n C record  X stop\n W Wireshark  Q quit")

    @work(thread=True, exclusive=True)
    def execute_test(self, fail=False):
        try:
            result = run_exchange(fail=fail)
            self.call_from_thread(self.finish_test, result["status"], result.get("error"))
        except Exception as exc:
            self.call_from_thread(self.finish_test, "FAILED", str(exc))

    def finish_test(self, status, error):
        self.route = status
        self.last_at = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        self.last_error = error or ("Injected ACK loss" if status == "FAILED" else "None")
        self.refresh_view()

    @work(thread=True, exclusive=True)
    def execute_network(self, fail=False):
        """Run the multiprocessing network harness in a fresh CLI process.

        Python 3.14 forkserver must initialize outside the Textual worker
        thread; a child Python interpreter has its own main thread.
        """
        import json
        import subprocess
        import sys
        command = [sys.executable, "-m", "d3faulth_telecom.cli",
                   "network-fail" if fail else "network-test"]
        try:
            completed = subprocess.run(command, capture_output=True, text=True,
                                       timeout=20, check=False)
            if completed.returncode:
                raise RuntimeError(completed.stderr.strip() or "Network test failed")
            result = json.loads(completed.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired, RuntimeError) as exc:
            result = {"status": "FAILED", "error": str(exc),
                      "segments": [
                          {"from": "ASP", "to": "RELAY", "status": "FAILED"},
                          {"from": "RELAY", "to": "DESTINATION", "status": "FAILED"}]}
        self.call_from_thread(self.finish_network, result)

    def finish_network(self, result):
        self.path = result
        self.last_at = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        self.last_error = result.get("error", "None")
        self.write_log(f"[cyan]Two-hop transport: {result['status']} | {result.get('details', {})}[/cyan]")
        self.refresh_view()

    @work(thread=True, exclusive=True)
    def operate_core(self, stopping=False):
        try:
            result = persistent.stop() if stopping else persistent.start()
            message = f"Persistent core: {'STOPPED' if stopping else 'STARTED'} (PID {result.get('pid')})"
            self.call_from_thread(self.write_log, "[cyan]" + message + "[/cyan]")
        except Exception as exc:
            self.call_from_thread(self.write_log, "[red]Persistent core error: " + str(exc) + "[/red]")
        self.call_from_thread(self.refresh_view)

    def action_core_start(self): self.operate_core(False)
    def action_core_stop(self): self.operate_core(True)
    def action_network_test(self): self.execute_network(False)
    def action_network_fault(self): self.execute_network(True)
    def action_test(self): self.execute_test(False)
    def action_fail(self): self.execute_test(True)

    def action_capture_start(self):
        try:
            capture.start()
            self.write_log("[green]Loopback SCTP capture started.[/green]")
        except Exception as exc:
            self.write_log(f"[red]Capture error: {exc}[/red]")
        self.refresh_view()

    def action_capture_stop(self):
        capture.stop()
        self.write_log("[yellow]Capture stopped.[/yellow]")
        self.refresh_view()

    def action_wireshark(self):
        try:
            self.write_log("[cyan]" + capture.open_wireshark() + "[/cyan]")
        except Exception as exc:
            self.write_log(f"[red]{exc}[/red]")

    def action_logs(self):
        self.show_logs = not self.show_logs
        self.query_one("#logs").display = self.show_logs

    def action_details(self):
        self.show_details = not self.show_details
        self.query_one("#details").display = self.show_details

    def action_refresh(self): self.refresh_view()

    def on_unmount(self): capture.stop()
