"""Three aligned telecom nodes with links drawn between their ports."""
from rich.text import Text

NODE_WIDTH = 10

def _centers(width):
    cell = max(20, (max(64, width) - 4) // 3)
    return cell, [cell // 2 + i * cell for i in range(3)]

def _put(line, column, string):
    for offset, char in enumerate(string):
        if 0 <= column + offset < len(line):
            line[column + offset] = char

def topology_lines(width, left, center, right, left_status="UNTESTED", right_status="UNIMPLEMENTED"):
    cell, centers = _centers(width)
    canvas_width = cell * 3
    rows = [[" "] * canvas_width for _ in range(5)]
    for index, (label, cx) in enumerate(zip((left, center, right), centers)):
        _put(rows[0], cx - len(label) // 2, label)
        for y, sprite in enumerate(("┏━━━━━━━━┓", "┃ ▣  ▣  ┃", "┗━┳━━━━┳━┛"), 1):
            _put(rows[y], cx - NODE_WIDTH // 2, sprite)
    for idx, status in enumerate((left_status, right_status)):
        left_end = centers[idx] + NODE_WIDTH // 2
        right_begin = centers[idx + 1] - NODE_WIDTH // 2
        fill = "━" if status == "HEALTHY" else "╳" if status == "FAILED" else "┄"
        for x in range(left_end, right_begin):
            rows[2][x] = fill
        if status == "HEALTHY":
            rows[2][right_begin - 2] = "▶"
    rows[4] = list("".join((" " * cell for _ in range(3))))
    return ["".join(row) for row in rows]

def topology_render(width, single_status, path=None):
    running_path = path is not None
    labels = ("ASP CLIENT", "SCTP RELAY", "DEST RESPONDER") if running_path else ("ASP CLIENT", "STP TEST", "HLR / SIM")
    statuses = (path["segments"][0]["status"], path["segments"][1]["status"]) if running_path else (single_status, "UNIMPLEMENTED")
    rows = topology_lines(width, *labels, *statuses)
    result = Text()
    _, centers = _centers(width)
    for row_index, row in enumerate(rows[:4]):
        if row_index == 2:
            previous = 0
            for i, status in enumerate(statuses):
                begin = centers[i] + NODE_WIDTH // 2
                finish = centers[i + 1] - NODE_WIDTH // 2
                result.append(row[previous:begin], style="cyan")
                color = "bright_green" if status == "HEALTHY" else "bright_red" if status == "FAILED" else "grey50"
                result.append(row[begin:finish], style=color)
                previous = finish
            result.append(row[previous:], style="cyan")
        else:
            result.append(row, style="cyan")
        result.append("\n")
    if running_path:
        overall = path.get("status", "UNTESTED")
        result.append(f"Two-hop signaling transport: {overall}\n",
                      style="bold green" if overall == "HEALTHY" else "bold red" if overall == "FAILED" else "yellow")
        result.append("127.0.0.1 only • transport-management exchange, no HLR/MAP service", style="dim")
    else:
        result.append(f"Single-hop signaling test: {single_status}\n", style="yellow")
        result.append("HLR is not implemented; gray means disconnected.", style="dim")
    return result
