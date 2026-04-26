"""Textual-based TUI for browsing boards and triggering builds.

Launched via ``mpbuild --interactive`` (see cli.py). The app reuses the
existing board database and docker_build_cmd; the build subprocess is
streamed live into a RichLog widget.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, RichLog, Select, Static, Tree

from . import board_database
from .board_database import Board
from .build import docker_build_cmd


class BoardTree(Tree):
    """Tree with right/left arrow keys mapped to expand/collapse, on top of
    the default keyboard navigation."""

    BINDINGS = [
        Binding("right", "expand_branch", "Expand", show=False),
        Binding("left", "collapse_branch", "Collapse", show=False),
    ]

    def action_expand_branch(self) -> None:
        node = self.cursor_node
        if node is not None:
            node.expand()

    def action_collapse_branch(self) -> None:
        """Collapse the cursor's branch — or, if on a leaf or already-collapsed
        node, hop to the parent and collapse that."""
        node = self.cursor_node
        if node is None:
            return
        if node.allow_expand and node.is_expanded:
            node.collapse()
            return
        parent = node.parent
        if parent is not None and parent is not self.root:
            self.move_cursor(parent)
            parent.collapse()


def _stream_command(cmd: str) -> Iterator[str]:
    """Run ``cmd`` via shell; yield stdout lines as they arrive, then a final exit line."""
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        yield line.rstrip("\n")
    proc.wait()
    yield f"[exit {proc.returncode}]"


class MpBuildApp(App):
    TITLE = "mpbuild"
    SUB_TITLE = "Interactive MicroPython firmware builder"
    CSS_PATH = "interactive.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("b", "build", "Build"),
        ("c", "clean", "Clean"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield BoardTree(":snake: MicroPython", id="board-tree")
            with Vertical(id="right-pane"):
                with Vertical(id="info-pane"):
                    yield Static("Select a board…", id="info-text")
                    yield Select([], id="variant-select", prompt="Variant")
                    with Horizontal(id="action-row"):
                        yield Button("Build", id="build-btn", variant="primary")
                        yield Button("Clean", id="clean-btn", variant="warning")
                yield RichLog(id="build-log", wrap=False, highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._selected_board: Board | None = None
        tree = self.query_one("#board-tree", BoardTree)
        tree.root.expand()
        self._populate_tree(tree)
        self._set_actions_enabled(False)
        # Variant select starts hidden until a board with variants is picked.
        self.query_one("#variant-select", Select).display = False

    def _populate_tree(self, tree: BoardTree) -> None:
        db = board_database()
        for port in sorted(db.ports.values()):
            port_node = tree.root.add(port.name, expand=False)
            for board in sorted(port.boards.values()):
                port_node.add_leaf(board.name, data=board)

    def _set_actions_enabled(self, enabled: bool) -> None:
        self.query_one("#build-btn", Button).disabled = not enabled
        self.query_one("#clean-btn", Button).disabled = not enabled
        self.query_one("#variant-select", Select).disabled = not enabled

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        board = event.node.data
        if not isinstance(board, Board):
            self._selected_board = None
            self._set_actions_enabled(False)
            return
        self._selected_board = board
        self._render_info(board)
        self._set_actions_enabled(True)

    def _render_info(self, board: Board) -> None:
        info = self.query_one("#info-text", Static)
        info.update(
            f"[bold]{board.product or board.name}[/]\n"
            f"[dim]Vendor:[/] {board.vendor or '—'}\n"
            f"[dim]MCU:[/]    {board.mcu or '—'}\n"
            f"[dim]Port:[/]   {board.port.name}\n"
            f"[dim]URL:[/]    {board.url}"
        )
        select = self.query_one("#variant-select", Select)
        if board.variants:
            select.set_options([(v.name, v.name) for v in board.variants])
            select.display = True
        else:
            select.set_options([])
            select.display = False

    def _selected_variant(self) -> str | None:
        select = self.query_one("#variant-select", Select)
        value = select.value
        return value if isinstance(value, str) else None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self._selected_board:
            return
        if event.button.id == "build-btn":
            self._run_build(do_clean=False)
        elif event.button.id == "clean-btn":
            self._run_build(do_clean=True)

    def action_build(self) -> None:
        if self._selected_board:
            self._run_build(do_clean=False)

    def action_clean(self) -> None:
        if self._selected_board:
            self._run_build(do_clean=True)

    def _run_build(self, *, do_clean: bool) -> None:
        board = self._selected_board
        assert board is not None
        log = self.query_one("#build-log", RichLog)
        log.clear()
        log.write(f"[bold]{'Cleaning' if do_clean else 'Building'} {board.name}…[/]")
        self._stream_build(board, self._selected_variant(), do_clean)

    @work(thread=True, exclusive=True, group="build")
    def _stream_build(self, board: Board, variant: str | None, do_clean: bool) -> None:
        try:
            cmd = docker_build_cmd(
                board=board,
                variant=variant,
                do_clean=do_clean,
                docker_interactive=False,
            )
        except Exception as e:  # ValueError from unknown variant, etc.
            self.call_from_thread(self._log_line, f"[red]error:[/] {e}")
            return
        for line in _stream_command(cmd):
            self.call_from_thread(self._log_line, line)

    def _log_line(self, text: str) -> None:
        self.query_one("#build-log", RichLog).write(text)


def start_app() -> None:
    MpBuildApp().run()
