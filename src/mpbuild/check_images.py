from . import board_database

from urllib.request import Request, urlopen
from urllib.error import HTTPError

from rich.progress import Progress
from rich import print
from rich.panel import Panel
from rich.table import Table


def check_images(verbose: bool = False, mpy_dir: str = None) -> None:
    db = board_database(mpy_dir)
    # TODO(mst) A minor improvement: Should count the number of images in all
    # the boards for each port (this assumes one per board).
    num_boards = len(db.boards)

    # no_images = [("stm32", "fooobar"), ("rp2", "PICO")] # []
    # image_not_found = [("stm32", "fooobar", "https://raw.githubusercontent.com/micropython/micropython-media/main/boards/VK_RA6M5/VK-RA6M5.jpg"),
    #                    ("stm32", "fooobar", "https://raw.githubusercontent.com/micropython/micropython-media/main/boards/VK_RA6M5/VK-RA6M5.jpg"),
    #                    ("rp2", "PICO", "https://raw.githubusercontent.com/micropython/micropython-media/main/boards/VK_RA6M5/VK-RA6M5.jpg")] # []
    # image_too_large = [("esp32", "GENERIC", "https://raw.githubusercontent.com/micropython/micropython-media/main/boards/VK_RA6M5/VK-RA6M5.jpg", 500_000),
    #                    ("rp2", "PICO", "https://raw.githubusercontent.com/micropython/micropython-media/main/boards/VK_RA6M5/VK-RA6M5.jpg", 400_000)] # []
    no_images = []
    image_not_found = []
    image_too_large = []

    base_url = (
        r"https://raw.githubusercontent.com/micropython/micropython-media/main/boards"
    )
    with Progress(transient=True) as progress:
        task1 = progress.add_task("[cyan]Checking images...", total=num_boards)
        for _board in db.boards.values():
            image_list = _board.images
            if len(image_list) == 0:
                # No images specified in build.json (should be at least one)
                no_images.append((_board.port.name, _board.name))
            for image in image_list:
                # Check each image listed in board.json
                image_url = f"{base_url}/{_board.name}/{image}"
                req = Request(image_url, method="HEAD")
                try:
                    f = urlopen(req)
                except HTTPError:
                    image_not_found.append((_board.port.name, _board.name, image_url))
                if f.status == 200:
                    # Check size < ~500KB
                    image_size = int(f.headers["Content-Length"])
                    if image_size > 500_000:
                        image_too_large.append(
                            (_board.port.name, _board.name, image_url, image_size)
                        )
            progress.update(task1, advance=1)

    # Display output
    grid = Table.grid(expand=True)
    grid.add_column()
    grid.add_column()
    grid.add_column()
    grid.add_row(
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
    )
    print(grid)
