"""Claude-like fullscreen launcher UI helpers."""

from dataclasses import dataclass
import os
import shutil
from typing import Sequence

from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style


@dataclass(frozen=True)
class MenuOption:
    key: str
    title: str
    description: str
    meta: str = ""


STYLE = Style.from_dict(
    {
        "header.cmd": "fg:#f8fafc",
        "frame.border": "fg:#38bdf8",
        "frame.title": "bold fg:#fbbf24",
        "frame.text": "fg:#d1d5db",
        "line": "fg:#64748b",
        "prompt.prefix": "bold fg:#f8fafc",
        "prompt.value": "fg:#f8fafc",
        "prompt.cursor": "bold fg:#0f172a bg:#f8fafc",
        "list.selected": "bold fg:#0f172a bg:#fde68a",
        "list.normal": "fg:#e2e8f0",
        "selected.desc": "fg:#94a3b8",
        "footer": "fg:#f59e0b",
    }
)


def fullscreen_menu(
    title: str,
    subtitle: str,
    options: Sequence[MenuOption],
    footer: str,
    initial_key: str | None = None,
) -> str | None:
    """Render launcher-like fullscreen menu and return selected key."""
    if not options:
        return None

    index = 0
    if initial_key:
        for pos, option in enumerate(options):
            if option.key == initial_key:
                index = pos
                break

    state = {"index": index, "result": None, "query": "", "show_help": False}
    max_visible = 8

    def _term_width() -> int:
        return shutil.get_terminal_size((120, 30)).columns

    def _line(width: int) -> str:
        return "-" * max(40, width - 2)

    def _fit(text: str, width: int) -> str:
        clean = text.replace("\n", " ").strip()
        if len(clean) <= width:
            return clean.ljust(width)
        if width <= 3:
            return clean[:width]
        return clean[: width - 3] + "..."

    def _filtered() -> list[MenuOption]:
        query = state["query"].strip().lower()
        if not query:
            return list(options)
        return [
            item
            for item in options
            if query in item.title.lower()
            or query in item.description.lower()
            or query in item.key.lower()
            or query in item.meta.lower()
        ]

    def _clamp_index() -> None:
        visible = _filtered()
        if not visible:
            state["index"] = 0
            return
        if state["index"] >= len(visible):
            state["index"] = len(visible) - 1
        if state["index"] < 0:
            state["index"] = 0

    def _header() -> FormattedText:
        cwd = os.getcwd()
        width = _term_width()
        frame_w = min(110, max(48, width - 4))
        inner = frame_w - 4
        top = "+" + ("-" * (frame_w - 2)) + "+"
        bottom = top

        subtitle_lines = [line.strip() for line in subtitle.splitlines() if line.strip()]
        while len(subtitle_lines) < 2:
            subtitle_lines.append("")

        row1 = f"| {_fit(title, inner)} |"
        row2 = f"| {_fit(subtitle_lines[0], inner)} |"
        row3 = f"| {_fit(subtitle_lines[1], inner)} |"

        return FormattedText(
            [
                ("class:header.cmd", f" {cwd}>agent-forge\n"),
                ("class:frame.border", f" {top}\n"),
                ("class:frame.title", f" {row1}\n"),
                ("class:frame.text", f" {row2}\n"),
                ("class:frame.text", f" {row3}\n"),
                ("class:frame.border", f" {bottom}\n"),
                ("class:line", _line(width)),
            ]
        )

    def _body() -> FormattedText:
        _clamp_index()
        visible = _filtered()
        width = _term_width()
        fragments: list[tuple[str, str]] = []

        fragments.append(("class:prompt.prefix", "\n > "))
        if state["query"]:
            fragments.append(("class:prompt.value", state["query"]))
        fragments.append(("class:prompt.cursor", " "))
        fragments.append(("class:line", f"\n{_line(width)}\n"))

        if state["show_help"]:
            fragments.append(("class:list.normal", " Commands\n\n"))
            fragments.append(("class:selected.desc", "  Up/Down or j/k  Navigate\n"))
            fragments.append(("class:selected.desc", "  Type text       Filter commands\n"))
            fragments.append(("class:selected.desc", "  Enter           Run selected command\n"))
            fragments.append(("class:selected.desc", "  Backspace       Delete filter (or go back if empty)\n"))
            fragments.append(("class:selected.desc", "  Esc / Left      Go back\n"))
            fragments.append(("class:selected.desc", "  Ctrl+L          Clear filter\n"))
            fragments.append(("class:selected.desc", "  ?               Toggle help\n"))
            return FormattedText(fragments)

        if not visible:
            fragments.append(("class:selected.desc", " No command matches your filter.\n"))
            return FormattedText(fragments)

        start = 0
        if len(visible) > max_visible:
            start = max(0, state["index"] - (max_visible // 2))
            start = min(start, len(visible) - max_visible)
        end = min(len(visible), start + max_visible)

        for pos in range(start, end):
            opt = visible[pos]
            selected = pos == state["index"]
            style = "class:list.selected" if selected else "class:list.normal"
            prefix = "> " if selected else "  "
            fragments.append((style, f" {prefix}{opt.title}\n"))

        selected_opt = visible[state["index"]]
        fragments.append(("class:selected.desc", f"\n {selected_opt.description}\n"))
        if selected_opt.meta:
            fragments.append(("class:selected.desc", f" {selected_opt.meta}\n"))

        return FormattedText(fragments)

    def _footer() -> FormattedText:
        visible = _filtered()
        return FormattedText(
            [
                (
                    "class:footer",
                    f"\n ? shortcuts  |  {footer}  |  {len(visible)}/{len(options)}",
                )
            ]
        )

    root = HSplit(
        [
            Window(FormattedTextControl(_header), height=7),
            Window(FormattedTextControl(_body), always_hide_cursor=True),
            Window(FormattedTextControl(_footer), height=2),
        ]
    )

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _up(event) -> None:
        visible = _filtered()
        if not visible:
            return
        state["index"] = (state["index"] - 1) % len(visible)

    @kb.add("down")
    @kb.add("j")
    def _down(event) -> None:
        visible = _filtered()
        if not visible:
            return
        state["index"] = (state["index"] + 1) % len(visible)

    @kb.add("home")
    def _home(event) -> None:
        state["index"] = 0

    @kb.add("end")
    def _end(event) -> None:
        visible = _filtered()
        if visible:
            state["index"] = len(visible) - 1

    @kb.add("enter")
    def _enter(event) -> None:
        visible = _filtered()
        if not visible:
            return
        state["result"] = visible[state["index"]].key
        event.app.exit()

    @kb.add("?")
    def _toggle_help(event) -> None:
        state["show_help"] = not state["show_help"]

    @kb.add("c-l")
    def _clear_query(event) -> None:
        state["query"] = ""
        _clamp_index()

    @kb.add("backspace")
    def _backspace(event) -> None:
        if state["query"]:
            state["query"] = state["query"][:-1]
            _clamp_index()
            return
        event.app.exit()

    @kb.add("escape")
    @kb.add("left")
    @kb.add("c-c")
    def _exit(event) -> None:
        event.app.exit()

    @kb.add("<any>")
    def _type(event) -> None:
        data = event.data
        if not data:
            return
        if data.isprintable() and data not in {"\n", "\r", "\t"}:
            state["query"] += data
            _clamp_index()

    app = Application(
        layout=Layout(root),
        key_bindings=kb,
        full_screen=True,
        mouse_support=False,
        style=STYLE,
    )
    app.run()
    return state["result"]
