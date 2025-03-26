from . import board_database
import json

from urllib.request import Request, urlopen
from urllib.error import HTTPError

from rich.progress import Progress
from rich import print
from rich.panel import Panel
from rich.table import Table


def check_boards(verbose: bool = False, mpy_dir: str = None) -> None:
    db = board_database(mpy_dir)
    num_boards = len(db.boards)

    # Lists to store issues
    no_images = []
    image_not_found = []
    image_too_large = []
    board_json_issues = []

    base_url = (
        r"https://raw.githubusercontent.com/micropython/micropython-media/main/boards"
    )

    with Progress(transient=True) as progress:
        task1 = progress.add_task("[cyan]Checking boards...", total=num_boards)

        # Check each board
        for _board in db.boards.values():
            if _board.physical_board:
                # Check board.json file format
                json_path = _board.directory / "board.json"
                try:
                    if json_path.exists():
                        with open(json_path) as f:
                            board_json = json.load(f)
                            # Check for issues in board.json
                            issues = db.check_board_json(
                                board_json, _board.name, _board.port.name
                            )
                            board_json_issues.extend(issues)
                except (json.JSONDecodeError, IOError) as e:
                    board_json_issues.append(
                        f"{_board.port.name}/{_board.name}: Error reading board.json: {str(e)}"
                    )

            # Check images
            image_list = _board.images
            if len(image_list) == 0:
                # No images specified in board.json (should be at least one)
                no_images.append((_board.port.name, _board.name))

            for image in image_list:
                # Check each image listed in board.json
                image_url = f"{base_url}/{_board.name}/{image}"
                req = Request(image_url, method="HEAD")
                try:
                    f = urlopen(req)
                    if f.status == 200:
                        # Check size < ~500KB
                        image_size = int(f.headers["Content-Length"])
                        if image_size > 500_000:
                            image_too_large.append(
                                (_board.port.name, _board.name, image_url, image_size)
                            )
                except HTTPError:
                    image_not_found.append((_board.port.name, _board.name, image_url))

            progress.update(task1, advance=1)

    # Display output
    grid = Table.grid(expand=True)
    grid.add_column()
    grid.add_column()
    grid.add_column()

    first_row = [
        Panel(
            "\n".join([f"{p}/[bright_white]{b}[/]" for p, b in no_images]),
            title="No images",
            subtitle="No image in board.json",
        ),
        Panel(
            "\n".join(
                [
                    f"[link={url}]{p}/[bright_white]{b}[/][/link]"
                    for p, b, url in image_not_found
                ]
            ),
            title="Not found",
            subtitle="Image not in micropython-media",
        ),
        Panel(
            "\n".join(
                [
                    f"[link={url}]{p}/[bright_white]{b}[/][/link]"
                    for p, b, url, s in image_too_large
                ]
            ),
            title="Too large",
            subtitle="Image > 500KB",
        ),
    ]

    grid.add_row(*first_row)

    # Add board.json issues panel if there are any
    if board_json_issues:
        json_panel = Panel(
            "\n".join(board_json_issues),
            title="board.json issues",
            subtitle="Missing or invalid keys",
        )
        grid.add_row(json_panel)

    print(grid)


# Backwards compatibility
def check_images(verbose: bool = False, mpy_dir: str = None) -> None:
    """Legacy function, redirects to check_boards"""
    check_boards(verbose, mpy_dir)
