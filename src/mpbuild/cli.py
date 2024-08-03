from typing import Optional
from typing_extensions import Annotated

import typer

from . import __app_name__, __version__, valid_ports
from .find_boards import ports_and_boards
from .build import build_board, clean_board


app = typer.Typer()


@app.command()
def build(
    board: str, variant: Annotated[Optional[str], typer.Argument()] = None
) -> None:
    """
    Build a MicroPython board.
    """
    v = f" ({variant})" if variant else ""
    print(f"Build {board}{v}!")

    # Find the port for the supplied board
    port = None
    p_and_b = ports_and_boards()
    for p in p_and_b.keys():
        if board in p_and_b[p]:
            port = p
            break
    if port:
        print(f"{board} is in {p}")
    else:
        print(f"{board} is an invalid board")
        raise typer.Exit(code=1)

    build_board(port, board)


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
    port = None
    p_and_b = ports_and_boards()
    for p in p_and_b.keys():
        if board in p_and_b[p]:
            port = p
            break
    if port:
        print(f"{board} is in {p}")
    else:
        print(f"{board} is an invalid board")
        raise typer.Exit(code=1)

    clean_board(port, board)


@app.command("list")
def list_boards(
    port: Annotated[valid_ports, typer.Option(help="port name")] = None,
) -> None:
    """
    List available boards.
    """
    p = f" ({port.name})" if port else ""

    p_and_b = ports_and_boards()

    for p in p_and_b.keys():
        if not port or (port and port.name == p):
            print(f"{p: <10}    ({len(p_and_b[p])})")
            for b in p_and_b[p]:
                print(f"    {b}")
            print()


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
