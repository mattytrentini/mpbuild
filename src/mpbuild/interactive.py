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


def _spawn(cmd: str) -> subprocess.Popen[str]:
    """Start ``cmd`` under a shell, line-buffered, with stderr merged into stdout."""
    return subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def _stream_proc(proc: subprocess.Popen[str]) -> Iterator[str]:
    """Yield ``proc``'s stdout lines as they arrive, then a final exit-code line."""
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
        ("s", "stop", "Stop"),
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
                        yield Button("Stop", id="stop-btn", variant="error")
                yield RichLog(id="build-log", wrap=False, highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._selected_board: Board | None = None
        # Single source of truth for "is a build running": None = idle.
        # Build/Clean clicks while non-None terminate it before starting a new one.
        self._running_proc: subprocess.Popen[str] | None = None
        tree = self.query_one("#board-tree", BoardTree)
        tree.root.expand()
        self._populate_tree(tree)
        # Variant select starts hidden until a board with variants is picked.
        self.query_one("#variant-select", Select).display = False
        # Border-title labels give each pane a cheap visual identity. The
        # log's title gets swapped to the running board name during a build.
        tree.border_title = "Boards"
        self.query_one("#info-pane").border_title = "Selected"
        self.query_one("#build-log", RichLog).border_title = "Output"
        self._refresh_action_state()

    def on_unmount(self) -> None:
        # Don't leave an orphan docker container when the app exits.
        self._terminate_running()

    def _populate_tree(self, tree: BoardTree) -> None:
        db = board_database()
        for port in sorted(db.ports.values()):
            port_node = tree.root.add(port.name, expand=False)
            for board in sorted(port.boards.values()):
                port_node.add_leaf(board.name, data=board)

    def _refresh_action_state(self) -> None:
        """Recompute Build/Clean/Stop/variant-select enable states.

        - Build/Clean/variant: enabled iff a board is selected (regardless of
          whether a build is running — Option B lets you replace mid-flight).
        - Stop: enabled iff a build is currently running.
        """
        has_board = self._selected_board is not None
        is_running = self._running_proc is not None and self._running_proc.poll() is None
        self.query_one("#build-btn", Button).disabled = not has_board
        self.query_one("#clean-btn", Button).disabled = not has_board
        self.query_one("#variant-select", Select).disabled = not has_board
        self.query_one("#stop-btn", Button).disabled = not is_running

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        board = event.node.data
        if not isinstance(board, Board):
            self._selected_board = None
            self._refresh_action_state()
            return
        self._selected_board = board
        self._render_info(board)
        self._refresh_action_state()

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
        if event.button.id == "stop-btn":
            self._terminate_running()
            return
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

    def action_stop(self) -> None:
        self._terminate_running()

    def _run_build(self, *, do_clean: bool) -> None:
        board = self._selected_board
        assert board is not None
        # Implicit cancellation: clicking Build/Clean while a build runs
        # terminates the current one before starting the replacement.
        self._terminate_running()
        log = self.query_one("#build-log", RichLog)
        log.clear()
        title = "Cleaning" if do_clean else "Building"
        variant = self._selected_variant()
        suffix = f" ({variant})" if variant else ""
        log.border_title = f"{title} {board.name}{suffix}"
        log.write(f"[bold cyan][{title} {board.name}{suffix}][/]")
        self._stream_build(board, variant, do_clean)

    @work(thread=True, group="build")
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
        proc = _spawn(cmd)
        self.call_from_thread(self._set_running_proc, proc)
        try:
            for line in _stream_proc(proc):
                self.call_from_thread(self._log_line, line)
        finally:
            self.call_from_thread(self._on_build_finished, proc)

    def _set_running_proc(self, proc: subprocess.Popen[str]) -> None:
        self._running_proc = proc
        self._refresh_action_state()

    def _on_build_finished(self, proc: subprocess.Popen[str]) -> None:
        # Identity check: only clear if we still own this proc. A late callback
        # from a terminated build mustn't trample a freshly started one.
        if self._running_proc is proc:
            self._running_proc = None
            self.query_one("#build-log", RichLog).border_title = "Output"
            self._refresh_action_state()

    def _terminate_running(self) -> None:
        proc = self._running_proc
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass

    def _log_line(self, text: str) -> None:
        self.query_one("#build-log", RichLog).write(text)


def start_app() -> None:
    MpBuildApp().run()
