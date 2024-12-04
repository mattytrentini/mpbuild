from typing import Optional, List
from typing_extensions import Annotated

import typer

from . import __app_name__, __version__, OutputFormat
from .build import build_board, clean_board, IDF_DEFAULT
from .list_boards import print_boards
from .check_images import check_images
from .completions import list_ports, list_boards, list_variants_for_board
from .find_boards import parse_board_spec

app = typer.Typer(chain=True, context_settings={"help_option_names": ["-h", "--help"]})


def _complete(words: list[str], incomplete: str):
    completion = []
    for name in words:
        if name.startswith(incomplete):
            completion.append(name)
    return completion


def _complete_spec(incomplete: str):
    parts = incomplete.split("/")
    if len(parts) == 1:
        if incomplete.lower() == incomplete:
            return _complete_port(incomplete)
        return _complete_board(incomplete)
    elif len(parts) == 2:
        if parts[0].lower() == parts[0]:
            port = parts[0]
            #todo
        else:
            board = parts[0]
            #todo


def _complete_board(incomplete: str):
    return _complete(list_boards(), incomplete)


def _complete_variant(ctx: typer.Context, incomplete: str):
    board = ctx.params.get("board") or []
    return _complete(list_variants_for_board(board), incomplete)


def _complete_port(incomplete: str):
    return _complete(list_ports(), incomplete)


@app.command()
def build(
    board_spec: Annotated[
        str, typer.Argument(help="Board name, optionally with /variant", autocompletion=_complete_spec)
    ],
    #variant: Annotated[
    #    Optional[str],
    #    typer.Argument(help="Board variant", autocompletion=_complete_variant),
    #] = None,
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
    port, board, variant = parse_board_spec(board_spec)
    build_board(board, variant, extra_args or [], build_container, idf, port=port)


@app.command()
def clean(
    board_spec: Annotated[
        str, typer.Argument(help="Board name, optionally with /variant")
    ],
) -> None:
    """
    Clean a MicroPython board.
    """
    port, board, variant = parse_board_spec(board_spec)
    clean_board(board, variant, port=port)


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
