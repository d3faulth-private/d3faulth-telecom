"""Deterministic centered three-column topology for narrow or wide TUIs."""
from rich.text import Text

def topology_lines(width, left, center, right, left_status="UNTESTED", right_status="UNIMPLEMENTED"):
    width = max(50, width)
    cell = max(16, (width - 4) // 3)
    def center_text(s):
        return s.center(cell)
    rows = [
        center_text(left) + center_text(center) + center_text(right),
        center_text("┏━━━━━━━━┓") + center_text("┏━━━━━━━━┓") + center_text("┏━━━━━━━━┓"),
        center_text("┃ ▣  ▣  ┃") + center_text("┃ ▤▤▤▤  ┃") + center_text("┃ ▥▥▥▥  ┃"),
        center_text("┗━┳━━━━┳━┛") + center_text("┗━┳━━━━┳━┛") + center_text("┗━┳━━━━┳━┛"),
    ]
    def link(state):
        return "━━━━━━▶" if state == "HEALTHY" else "╳╳╳╳╳╳╳" if state == "FAILED" else "┄┄┄┄┄┄┄"
    rows.append(center_text(link(left_status)) + center_text(link(right_status)) + center_text(""))
    return rows

def topology_render(width, single_status, path=None):
    """All equipment boxes are centered in three equal columns."""
    is_path = path is not None
    left, mid, right = ("ASP CLIENT", "SCTP RELAY", "DEST RESPONDER") if is_path else ("ASP CLIENT", "STP TEST", "HLR / SIM")
    s1 = path["segments"][0]["status"] if is_path else single_status
    s2 = path["segments"][1]["status"] if is_path else "UNIMPLEMENTED"
    lines = topology_lines(width, left, mid, right, s1, s2)
    t = Text()
    for row in lines[:4]:
        t.append(row + "\n", style="cyan")
    t.append(lines[4] + "\n", style="green" if s1 == "HEALTHY" and s2 == "HEALTHY" else "cyan")
    if is_path:
        t.append("Two-hop localhost M3UA management test: " + path["status"] + "\n", style="bold green" if path["status"] == "HEALTHY" else "bold red")
        t.append("Two distinct SCTP associations; nodes exit after each test.", style="dim")
    else:
        t.append("Single-hop localhost M3UA test: " + single_status + "\n", style="yellow")
        t.append("HLR is not implemented; it is NOT connected.", style="dim")
    return t
