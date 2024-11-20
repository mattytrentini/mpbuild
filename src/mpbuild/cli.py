from typing import Optional, List
from typing_extensions import Annotated

import typer

from . import __app_name__, __version__, OutputFormat
from .build import build_board, clean_board, IDF_DEFAULT
from .list_boards import print_boards
from .check_images import check_images
from .completions import list_ports, list_boards, list_variants_for_board

import shutil
from . import board_database

app = typer.Typer(chain=True, context_settings={"help_option_names": ["-h", "--help"]})


def _complete(words: list[str], incomplete: str):
    completion = []
    for name in words:
        if name.startswith(incomplete):
            completion.append(name)
    return completion


def _complete_board(incomplete: str):
    return _complete(list_boards(), incomplete)


def _complete_variant(ctx: typer.Context, incomplete: str):
    board = ctx.params.get("board") or []
    return _complete(list_variants_for_board(board), incomplete)


def _complete_port(incomplete: str):
    return _complete(list_ports(), incomplete)


@app.command()
def build(
    board: Annotated[
        str, typer.Argument(help="Board name", autocompletion=_complete_board)
    ],
    variant: Annotated[
        Optional[str],
        typer.Argument(help="Board variant", autocompletion=_complete_variant),
    ] = None,
    idf: Annotated[
        Optional[str],
        typer.Option(help="esp32 port only: select IDF version to build with"),
    ] = IDF_DEFAULT,
    extra_args: Annotated[
        Optional[List[str]], typer.Argument(help="additional arguments to pass to make")
    ] = None,
    build_container: Annotated[
        Optional[str],
        typer.Option(help="Override the default build container"),
    ] = None,
) -> None:
    """
    Build a MicroPython board.
    """
    build_board(board, variant, extra_args or [], build_container, idf)


@app.command()
def clean(
    board: str, variant: Annotated[Optional[str], typer.Argument()] = None
) -> None:
    """
    Clean a MicroPython board.
    """
    clean_board(board, variant)


@app.command("list")
def list_boards_and_variants(
    port: Annotated[
        Optional[str], typer.Argument(help="Port name", autocompletion=_complete_port)
    ] = None,
    fmt: Annotated[
        OutputFormat,
        typer.Option(
            "--format", case_sensitive=False, help="Configure the output format"
        ),
    ] = OutputFormat.rich,
) -> None:
    """
    List available boards.
    """
    print_boards(port, fmt)


@app.command("check_images")
def image_check(
    verbose: Annotated[bool, typer.Option(help="More verbose output")] = False,
) -> None:
    """
    Check images
    """
    check_images(verbose)


@app.command("copy_board")
def copy_board(
    src_board: Annotated[
        str,
        typer.Argument(help="Source board (copy from)", autocompletion=_complete_board),
    ],
    new_board: Annotated[
        Optional[str], typer.Argument(help="Name of the new board (copy to)")
    ] = None,
) -> None:
    """
    Copy a board definition (to start a new board)
    """
    # Check for uppercase (allow with -f?)
    if any(c for c in new_board if c.islower()):
        print("The new board must not contain lowercase letters")
        raise SystemExit()

    db = board_database(None)

    if new_board in db.boards.keys():
        print(
            f"The new board must have a unique name:\n  {db.boards[new_board].directory} exists"
        )
        raise SystemExit()

    if src_board not in db.boards.keys():
        print("Invalid board")
        raise SystemExit()

    board = db.boards[src_board]

    dest_path = board.port.directory / "boards" / new_board

    # Check if the destination board name already exists
    if dest_path.exists():
        print("Invalid: Destination board name already exists")
        raise SystemExit()

    print(f"Copying {board.directory} to {dest_path}")
    shutil.copytree(board.directory, dest_path)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} v{__version__}")

        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show the application's version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    return
