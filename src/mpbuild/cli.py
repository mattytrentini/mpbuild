from typing import Optional, List
from typing_extensions import Annotated

import typer

from . import __app_name__, __version__, OutputFormat
from .find_boards import get_port
from .build import build_board, clean_board, IDF_DEFAULT
from .list_boards import list_boards
from .check_images import check_images


app = typer.Typer()


@app.command()
def build(
    board: str,
    variant: Annotated[Optional[str], typer.Argument()] = None,
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

    # Find the port for the supplied board
    port = get_port(board)

    build_board(port, board, variant, extra_args or [], build_container, idf)


@app.command()
def clean(
    board: str, variant: Annotated[Optional[str], typer.Argument()] = None
) -> None:
    """
    Clean a MicroPython board.
    """
    v = f" ({variant})" if variant else ""
    print(f"Clean {board=}{v}!")

    # Find the port for the supplied board
    port = get_port(board)

    clean_board(port, board)


@app.command("list")
def list_boards_and_variants(
    port: Annotated[Optional[str], typer.Argument(help="port name")] = None,
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
    list_boards(port, fmt)


@app.command("check-images")
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
