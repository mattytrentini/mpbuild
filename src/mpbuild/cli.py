from typing import Optional

import typer
from typing_extensions import Annotated

from . import __app_name__, __version__


app = typer.Typer()


@app.command()
def build(board: str, variant: Annotated[Optional[str], typer.Argument()] = None) -> None:
    v = f" ({variant})" if variant else ""
    print(f"Build everything for {board=}{v}!")

@app.command()
def clean(board: str) -> None:
    print(f"Cleeeeean! {board}")

from enum import Enum

# Need to add these at runtime
Ports = Enum("Ports", {"stm32":"stm32", "samd":"samd"})

@app.command()
def list(port: Annotated[Ports, typer.Option(help="port name")]=None) -> None:
    p = f" ({port.name})" if port else ""
    print(f"List all o' 'em boards{p}")
    

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
