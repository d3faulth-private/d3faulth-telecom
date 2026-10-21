"""Textual terminal-first signaling monitor. T=run lab test, F=fault, W=Wireshark."""
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Static, RichLog
from textual.reactive import reactive
from textual import work
from rich.text import Text
from .lab import run_exchange, recent_events

BANNER = r"""
╔══════════════════════════════════════════════════════════════════════╗
║   ██████╗ ██████╗ ███████╗ █████╗ ██╗   ██╗██╗  ████████╗██╗  ██╗  ║
║   ██╔══██╗╚════██╗██╔════╝██╔══██╗██║   ██║██║  ╚══██╔══╝██║  ██║  ║
║   ██║  ██║ █████╔╝█████╗  ███████║██║   ██║██║     ██║   ███████║  ║
║   ██║  ██║ ╚═══██╗██╔══╝  ██╔══██║██║   ██║██║     ██║   ██╔══██║  ║
║   ██████╔╝██████╔╝██║     ██║  ██║╚██████╔╝███████╗██║   ██║  ██║  ║
║   ╚═════╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝ ╚══════╝ ╚═╝   ╚═╝  ╚═╝  ╚═╝  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

class TelecomApp(App):
    TITLE = "D3FAULTH // TELECOM LAB"
    SUB_TITLE = "SIGNALING OBSERVABILITY • v0.1"
    CSS = """
    Screen { background: #08151b; color: #8ef3e4; }
    Header, Footer { background: #102c35; color: #78f0e4; }
    #banner { height: 9; content-align: center middle; color: #42d4df; text-style: bold; }
    #status { height: 3; color: #e2bd72; border: round #35626a; padding: 0 2; }
    #topology { height: 13; border: round #2e99a2; padding: 1 2; color: #a8e9e7; }
    #metrics { height: 5; border: round #35626a; padding: 1 2; }
    #loghead { color: #38ccd9; height: 1; }
    #log { height: 1fr; border: round #35626a; color: #9be0d3; }
    """
    BINDINGS = [Binding("t", "test", "Test SCTP/M3UA"), Binding("f", "fail", "Inject failure"),
                Binding("w", "wireshark", "Wireshark"), Binding("r", "refresh", "Refresh"), Binding("q", "quit", "Quit")]
    route = reactive("UNTESTED")
    busy = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(BANNER, id="banner")
        yield Static(" MODE: IDLE · NO CONNECTION VERIFIED · PRESS T TO TEST", id="status")
        yield Static(id="topology")
        yield Static(id="metrics")
        yield Static("┌─ SIGNALING EVENT MONITOR ─────────────────────────────────────────", id="loghead")
        yield RichLog(id="log", highlight=True, markup=True, max_lines=150)
        yield Footer()

    def on_mount(self):
        self.render_topology()
        self.write_events()

    def render_topology(self):
        ok = self.route == "HEALTHY"
        bad = self.route == "FAILED"
        color = "green" if ok else "red" if bad else "grey58"
        wire = "━━━━━━" if ok else "╳╳╳╳╳╳" if bad else "┄┄┄┄┄┄"
        topo = Text()
        topo.append("   ┌──────────┐               ┌──────────┐               ┌──────────┐\n", style="cyan")
        topo.append("   │ MSC / UE │", style="cyan")
        topo.append(" ─ ─ ─ ─ ─ ─ │   STP    │", style="cyan")
        topo.append("   ", style="cyan")
        topo.append(wire, style=f"bold {color}")
        topo.append("   │ HLR SIM  │\n", style="cyan")
        topo.append("   └──────────┘               └──────────┘               └──────────┘\n", style="cyan")
        topo.append("       Planned nodes             TEST SERVER            PLANNED NODE\n", style="dim")
        topo.append("                          127.0.0.1 : 29055\n", style="dim")
        topo.append("   VERIFIED LINK: LOCAL SCTP + M3UA ASPUP/ACK (STP TEST ENDPOINT)\n", style="white")
        topo.append("   Unimplemented nodes are NOT shown as connected.\n", style="yellow")
        self.query_one("#topology", Static).update(topo)
        self.query_one("#status", Static).update(f" MODE: {'ISOLATED LAB' if self.route != 'UNTESTED' else 'IDLE'}  ·  SCTP/M3UA: {self.route}  ·  HOST: LOOPBACK")
        self.query_one("#metrics", Static).update(f"[b]SCTP transport[/b]  {'VERIFIED' if ok or bad else 'NOT TESTED'}     [b]M3UA ACK[/b]  {self.route}\n[dim]MAP / subscriber lookups: NOT IMPLEMENTED   •   RF devices: NOT CONNECTED[/dim]")

    def write_events(self):
        log = self.query_one("#log", RichLog)
        log.clear()
        for e in recent_events():
            label = e["kind"].upper()
            color = "red" if label in ("ERROR", "FAULT") or e.get("status") == "FAILED" else "green" if label in ("LINK", "ROUTE") else "cyan"
            log.write(f"[{color}]{e['at'][11:19]} [{label}] {e['message']}[/]")

    @work(thread=True, exclusive=True)
    def run_test(self, fail=False):
        try:
            result = run_exchange(fail=fail)
            self.call_from_thread(self.finish_test, result["status"], None)
        except Exception as exc:
            self.call_from_thread(self.finish_test, "FAILED", str(exc))

    def finish_test(self, status, error):
        self.route = status
        self.render_topology()
        self.write_events()
        if error:
            self.query_one("#log", RichLog).write(f"[red]ERROR: {error}[/red]")

    def action_test(self): self.run_test(False)
    def action_fail(self): self.run_test(True)
    def action_refresh(self): self.write_events()
    def action_wireshark(self):
        import shutil, subprocess
        if shutil.which("wireshark"):
            term = shutil.which("x-terminal-emulator")
            subprocess.Popen([term, "-e", "wireshark"] if term else ["wireshark"], start_new_session=True)
            self.query_one("#log", RichLog).write("[cyan]Wireshark launched independently.[/cyan]")
        else:
            self.query_one("#log", RichLog).write("[yellow]Wireshark is not installed.[/yellow]")
