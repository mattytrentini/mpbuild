from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.reactive import var
from textual.widgets import Tree, Footer, Header, Static

from . import board_database
from .board_database import Board


class MpBuild(App):
    """Textual code browser app."""

    TITLE = "mpbuild interactive"
    SUB_TITLE = "The friendly MicroPython build tool"
    CSS_PATH = "interactive.tcss"
    BINDINGS = [
        ("f", "toggle_files", "Toggle Files"),
        ("b", "build", "Build Board"),
        ("q", "quit", "Quit"),
    ]

    show_tree = var(True)
    selected_board = var(None)

    def watch_show_tree(self, show_tree: bool) -> None:
        """Called when show_tree is modified."""
        self.set_class(show_tree, "-show-tree")

    def compose(self) -> ComposeResult:
        """Compose our UI."""
        yield Header()
        with Container():
            tree: Tree = Tree(":snake: MicroPython", id="tree-view")
            yield tree
            with VerticalScroll(id="code-view"):
                yield Static(id="code", expand=True)
        yield Footer()

    def on_mount(self) -> None:
        tree: Tree = self.query_one(Tree)
        tree.focus()
        tree.root.expand()
        db = board_database(".")
        for port in sorted(db.ports.values()):
            port_tree = tree.root.add(port.name, data=db.ports[port.name])
            # for board in sorted([b.name for b in db.ports[port.name].boards.values()]):
            for board in sorted(db.ports[port.name].boards.values()):
                port_tree.add_leaf(board.name, data=board)

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        event.stop()
        code_view = self.query_one("#code", Static)
        board: Board = event.node.data
        if isinstance(board, Board):
            code_view.update(f"{board.vendor} {board.product} ({board.name})")
            self.selected_board = board
        else:
            self.selected_board = None

    # def on_directory_tree_file_selected(
    #     self, event: Tree.FileSelected
    # ) -> None:
    #     """Called when the user click a file in the directory tree."""
    #     event.stop()
    #     code_view = self.query_one("#code", Static)
    #     try:
    #         syntax = Syntax.from_path(
    #             str(event.path),
    #             line_numbers=True,
    #             word_wrap=False,
    #             indent_guides=True,
    #             theme="github-dark",
    #         )
    #     except Exception:
    #         code_view.update(Traceback(theme="github-dark", width=None))
    #         self.sub_title = "ERROR"
    #     else:
    #         code_view.update(syntax)
    #         self.query_one("#code-view").scroll_home(animate=False)
    #         self.sub_title = str(event.path)

    def action_toggle_files(self) -> None:
        """Called in response to key binding."""
        self.show_tree = not self.show_tree

    def action_build(self) -> None:
        """Called in response to key binding."""
        if self.selected_board:
            print(f"build {self.selected_board.name}")
            # build_board(self.selected_board.name)


def start_app():
    MpBuild().run()


if __name__ == "__main__":
    start_app()
