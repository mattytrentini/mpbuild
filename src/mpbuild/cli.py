from typing import Optional, List
from typing_extensions import Annotated

import typer

from . import __app_name__, __version__, OutputFormat
from .build import build_board, clean_board, BUILD_CONTAINERS
from .list_boards import print_boards
from .check_images import check_images
from .completions import complete_port, complete_board_variant

app = typer.Typer(chain=True, context_settings={"help_option_names": ["-h", "--help"]})


@app.command()
def build(
    board_variant: Annotated[
        str, typer.Argument(help="Board name or Board-Variant", autocompletion=complete_board_variant)
    ],
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
    # Parse the board and variant from the combined format
    if "-" in board_variant:
        board, variant = board_variant.split("-", 1)
    else:
        board = board_variant
        variant = None
    build_board(board, variant, extra_args or [], build_container)


@app.command()
def clean(
    board_variant: Annotated[
        str, typer.Argument(help="Board name or Board-Variant", autocompletion=complete_board_variant)
    ]
) -> None:
    """
    Clean a MicroPython board.
    """
    # Parse the board and variant from the combined format
    if "-" in board_variant:
        board, variant = board_variant.split("-", 1)
    else:
        board = board_variant
        variant = None
    
    clean_board(board, variant)


@app.command("list")
def list_boards_and_variants(
    port: Annotated[
        Optional[str], typer.Argument(help="Port name", autocompletion=complete_port)
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
