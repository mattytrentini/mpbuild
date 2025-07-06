import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from . import board_database, OutputFormat
from rich.tree import Tree
from rich import print


@dataclass
class Pin:
    """Represents a pin definition from pins.csv"""

    functional_name: str
    mcu_pin: str

    @property
    def display_name(self) -> str:
        """Return the best name to display for this pin"""
        return self.functional_name if self.functional_name else self.mcu_pin


def parse_pins_csv(pins_file: Path) -> List[Pin]:
    """Parse a pins.csv file and return a list of Pin objects"""
    pins = []

    if not pins_file.exists():
        return pins

    try:
        with pins_file.open("r", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    # Handle format: functional_name,mcu_pin
                    functional_name = row[0].strip()
                    mcu_pin = row[1].strip()
                    pins.append(Pin(functional_name, mcu_pin))
                elif len(row) == 1:
                    # Handle format: mcu_pin (no functional name)
                    mcu_pin = row[0].strip()
                    pins.append(Pin("", mcu_pin))
    except (UnicodeDecodeError, csv.Error):
        # If CSV parsing fails, return empty list
        pass

    return pins


def print_pins(
    board: Optional[str] = None,
    port: Optional[str] = None,
    fmt: OutputFormat = OutputFormat.rich,
    mpy_dir: Optional[str] = None,
) -> None:
    """Print pins for boards"""
    db = board_database(mpy_dir, port)

    if port and port not in db.ports.keys():
        raise ValueError("Invalid port")

    if board and board not in db.boards.keys():
        raise ValueError("Invalid board")

    # Filter boards based on inputs
    boards_to_show = []
    if board:
        boards_to_show = [db.boards[board]]
    elif port:
        boards_to_show = list(db.ports[port].boards.values())
    else:
        boards_to_show = list(db.boards.values())

    if fmt == OutputFormat.rich:
        tree = Tree(":pushpin: [bright_white]Board Pins[/]")

        for b in sorted(boards_to_show):
            pins_file = b.directory / "pins.csv"
            pins = parse_pins_csv(pins_file)

            if pins:
                board_node = tree.add(
                    f"[bright_white]{b.name}[/] [bright_black]({len(pins)} pins)[/]"
                )

                # Group pins by type for better display
                cpu_pins = [
                    p
                    for p in pins
                    if not p.functional_name or p.functional_name == p.mcu_pin
                ]
                board_pins = [
                    p
                    for p in pins
                    if p.functional_name and p.functional_name != p.mcu_pin
                ]

                if board_pins:
                    board_section = board_node.add("[bright_blue]Board Pins[/]")
                    for pin in sorted(board_pins, key=lambda p: p.functional_name):
                        board_section.add(
                            f"[green]{pin.functional_name}[/] → [yellow]{pin.mcu_pin}[/]"
                        )

                if cpu_pins:
                    cpu_section = board_node.add("[bright_blue]CPU Pins[/]")
                    for pin in sorted(cpu_pins, key=lambda p: p.mcu_pin):
                        cpu_section.add(f"[yellow]{pin.mcu_pin}[/]")
            else:
                tree.add(f"[bright_white]{b.name}[/] [bright_black](no pins.csv)[/]")

        print(tree)

    elif fmt == OutputFormat.text:
        """Output space-separated list of pins"""
        all_pins = []
        for b in sorted(boards_to_show):
            pins_file = b.directory / "pins.csv"
            pins = parse_pins_csv(pins_file)
            all_pins.extend([pin.display_name for pin in pins])

        print(" ".join(sorted(set(all_pins))))
