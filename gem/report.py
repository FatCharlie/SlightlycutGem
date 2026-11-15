"""Terminal output: rich tables when python3-rich is installed, plain text if not."""
from dataclasses import dataclass

READY, WARN, FAIL, SKIP, ABSENT, MANUAL = "READY", "WARN", "FAIL", "SKIP", "NOT FITTED", "CHECK BY HAND"
STYLE = {READY: "bold green", WARN: "bold yellow", FAIL: "bold red",
         SKIP: "dim", ABSENT: "dim", MANUAL: "cyan"}
ICON = {READY: "✔", WARN: "!", FAIL: "✘", SKIP: "·", ABSENT: "–", MANUAL: "?"}

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    console = Console()
    HAVE_RICH = True
except ImportError:  # plain fallback
    console = None
    HAVE_RICH = False


@dataclass
class Check:
    group: str
    name: str
    status: str
    detail: str = ""
    fix: str = ""


def say(text, style=None):
    if HAVE_RICH:
        console.print(text if style is None else f"[{style}]{text}[/]", soft_wrap=True)
    else:
        print(_strip(text))


def _strip(text):
    import re
    return re.sub(r"\[/?[a-z ]+\]", "", text)


def status_table(title, checks):
    if not HAVE_RICH:
        print(f"\n{title}\n" + "=" * len(title))
        for c in checks:
            print(f"[{c.status:>13}] {c.group:12} {c.name:30} {c.detail}")
            if c.fix:
                print(f"{'':16}-> {c.fix}")
        return
    t = Table(title=title, box=box.ROUNDED, title_style="bold")
    t.add_column("Group", style="dim", no_wrap=True)
    t.add_column("Component", style="bold")
    t.add_column("Status", no_wrap=True)
    t.add_column("Detail")
    last = None
    for c in checks:
        if last is not None and c.group != last:
            t.add_section()
        detail = c.detail
        if c.fix:
            colour = "yellow" if c.status in (FAIL, WARN) else "dim"
            detail += f"\n[{colour}]→ {c.fix}[/]"
        t.add_row(c.group if c.group != last else "", c.name,
                  f"[{STYLE[c.status]}]{ICON[c.status]} {c.status}[/]", detail)
        last = c.group
    console.print(t)


def panel(title, lines):
    if not HAVE_RICH:
        print(f"\n{title}")
        for line in lines:
            print("  " + _strip(line))
        return
    console.print(Panel("\n".join(lines), title=title, expand=False))
