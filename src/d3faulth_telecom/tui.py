"""D3FAULTH Telecom Lab v0.2 — real-event terminal dashboard."""
from collections import deque
from datetime import datetime, timezone
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Static, RichLog
from textual.containers import Horizontal, Vertical
from textual import work
from rich.text import Text
from .lab import run_exchange, recent_events
from . import capture

SPRITES = {
    "MSC": (" ┏━━━━━━┓ ", " ┃ ▣  ▣ ┃ ", " ┗━┳━━┳━┛ "),
    "STP": (" ┏━━━━━━┓ ", " ┃ ▤▤▤▤ ┃ ", " ┗━┳━━┳━┛ "),
    "HLR": (" ┏━━━━━━┓ ", " ┃ ▥▥▥▥ ┃ ", " ┗━┳━━┳━┛ "),
    "SMSC":(" ┏━━━━━━┓ ", " ┃ ▣▤▣▤ ┃ ", " ┗━┳━━┳━┛ "),
}
SPARK = "▁▂▃▄▅▆▇█"

class TelecomApp(App):
    TITLE = "D3FAULTH // TELECOM LAB"
    SUB_TITLE = "SIGNALING OPERATIONS • v0.2"
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
        ok = self.route == "HEALTHY"
        bad = self.route == "FAILED"
        color = "green" if ok else "red" if bad else "grey62"
        wire = "━━━━▶━━" if ok else "╳╳╳╳╳╳" if bad else "┄┄┄┄┄┄"
        p = Text()
        p.append("     MSC / UE                  STP TEST               HLR / SIM\n", style="bold cyan")
        for i in range(3):
            p.append(SPRITES["MSC"][i] + "         " + SPRITES["STP"][i] + "          " + SPRITES["HLR"][i] + "\n", style="cyan")
        p.append("          ", style="cyan")
        p.append("┄┄┄┄┄┄┄┄┄", style="grey62")
        p.append("           ", style="grey62")
        p.append(wire, style=f"bold {color}")
        p.append("\n\n   PLANNED NODE              127.0.0.1:29055         PLANNED NODE\n", style="dim")
        p.append("   SCTP/M3UA test exchange is localhost-only.\n", style="yellow")
        p.append("   Gray nodes have no configured telecom service.", style="dim")
        self.query_one("#topology", Static).update(p)
        cap = capture.status()
        self.query_one("#status", Static).update(
            f" MODE: {'LOCAL LAB' if self.route != 'UNTESTED' else 'IDLE'}   •   SCTP/M3UA: {self.route}"
            f"   •   CAPTURE: {'RECORDING' if cap['active'] else 'OFF'}   •   LAST TEST: {self.last_at}")
        values = list(self.rates)
        chart = "".join(SPARK[min(7, n)] for n in values)
        self.query_one("#telemetry", Static).update(
            f"[bold cyan]┌─ LIVE TELEMETRY[/bold cyan]\n\n"
            f"  SCTP/M3UA EVENTS\n  [green]{chart}[/green]\n  {values[-1]} events / refresh\n\n"
            f"  ASPUP/ACK: [{color}]{self.route}[/{color}]\n  CAPTURE: {'ON' if cap['active'] else 'OFF'}\n"
            f"  SCCP: NOT INSTALLED\n  TCAP: NOT INSTALLED\n  MAP: NOT INSTALLED\n"
            f"  SDR: NOT DETECTED")
        self.query_one("#diagnostics", Static).update(
            "[bold cyan]┌─ ROUTE DIAGNOSTICS[/bold cyan]\n\n"
            f" TRANSPORT: SCTP\n ENDPOINT: loopback\n PORT: 29055\n"
            f" ROUTE: {self.route}\n LAST VERIFIED: {self.last_at}\n"
            f" ERROR: {self.last_error[:42]}\n\n"
            f" CAPTURE FILE:\n {str(cap['file'] or 'None')[-38:]}\n\n"
            " T test  F fault\n C record  X stop\n W Wireshark  Q quit")

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
