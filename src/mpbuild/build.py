import os
from typing import Optional, List

from pathlib import Path
import multiprocessing
import subprocess
import sys
import glob

from rich import print
from rich.panel import Panel
from rich.markdown import Markdown

from . import board_database, find_mpy_root
from .board_database import Board

ARM_BUILD_CONTAINER = "micropython/build-micropython-arm"
BUILD_CONTAINERS = {
    "stm32": ARM_BUILD_CONTAINER,
    "rp2": ARM_BUILD_CONTAINER,
    "nrf": ARM_BUILD_CONTAINER,
    "mimxrt": ARM_BUILD_CONTAINER,
    "renesas-ra": ARM_BUILD_CONTAINER,
    "samd": ARM_BUILD_CONTAINER,
    "psoc6": "ifxmakers/mpy-mtb-ci",
    "esp32": "espressif/idf:v5.4.2",
    "esp8266": "larsks/esp-open-sdk",
    "unix": "gcc:12-bookworm",  # Special, doesn't have boards
}


class MpbuildNotSupportedException(Exception):
    pass


def get_build_container(board: Board, variant: Optional[str] = None) -> str:
    """
    Returns the container to be used for this board/variant.

    Example: board="RPI_PICO" => "micropython/build-micropython-arm"
    Example: board="RPI_PICO", variant="RISCV" => "micropython/build-micropython-rp2350riscv"
    """
    port = board.port

    if port.name == "rp2":
        if variant == "RISCV":
            # Special case: This board supports an ARM core as default
            # and a RISC-V core as a variant
            return "micropython/build-micropython-rp2350riscv"

        # RP2 requires a recent version of gcc
        return "micropython/build-micropython-arm:bookworm"

    try:
        return BUILD_CONTAINERS[port.name]
    except KeyError as e:
        raise MpbuildNotSupportedException(f"{board.name}-{variant}") from e


nprocs = multiprocessing.cpu_count()


def docker_build_cmd(
    board: Board,
    variant: Optional[str] = None,
    extra_args: List[str] = [],
    do_clean: bool = False,
    build_container_override: str | None = None,
    docker_interactive: bool = True,
) -> str:
    """
    Returns the docker-command which will build the firmware.
    """

    port = board.port

    if variant:
        v = board.find_variant(variant)
        if not v:
            raise ValueError(
                f"Variant '{variant}' not found for board '{board.name}': Valid variants are: {[v.name for v in board.variants]}"
            )

    build_container = (
        build_container_override
        if build_container_override
        else get_build_container(board=board, variant=variant)
    )

    variant_param = "BOARD_VARIANT" if board.physical_board else "VARIANT"
    variant_cmd = "" if variant is None else f" {variant_param}={variant}"

    args = " " + " ".join(extra_args)

    make_mpy_cross_cmd = "make -C mpy-cross && "
    update_submodules_cmd = (
        f"make -C ports/{port.name} BOARD={board.name}{variant_cmd} submodules && "
    )
    uid, gid = os.getuid(), os.getgid()

    if do_clean:
        # When cleaning we run with full privs
        uid, gid = 0, 0
        # Don't need to build mpy_cross or update submodules
        make_mpy_cross_cmd = ""
        update_submodules_cmd = ""

    mpy_dir = str(port.directory_repo)

    # Dynamically find all ttyACM and ttyUSB devices
    tty_devices = []
    for pattern in ["/dev/ttyACM*", "/dev/ttyUSB*"]:
        tty_devices.extend(glob.glob(pattern))

    # Build device flags
    device_flags = ""
    if os.path.exists("/dev/bus/usb/") and os.listdir("/dev/bus/usb/"):
        device_flags += "--device /dev/bus/usb/ "  # USB access
    for device in tty_devices:
        device_flags += f"--device {device} "

    # fmt: off
    build_cmd = (
        f"docker run --rm "
        f"{'-it ' if docker_interactive else ''}"
        f"{device_flags}"                       # provides access to USB and serial devices for deploy
        f"-v {mpy_dir}:{mpy_dir} -w {mpy_dir} " # mount micropython dir with same path so elf/map paths match host
        f"--user {uid}:{gid} "                  # match running user id so generated files aren't owned by root
        f"-e HOME=/tmp "                        # set HOME to /tmp for container
        f"{build_container} "
        f'bash -c "'
        f"git config --global --add safe.directory '*' 2> /dev/null;"
        f'{make_mpy_cross_cmd}'
        f'{update_submodules_cmd}'
        f'make -j {nprocs} -C ports/{port.name} BOARD={board.name}{variant_cmd}{args}"'
    )
    # fmt: on

    return build_cmd


def build_board(
    board: str,
    variant: Optional[str] = None,
    extra_args: List[str] = [],
    build_container_override: Optional[str] = None,
    mpy_dir: str | Path | None = None,
) -> None:
    """
    Build the firmware.

    This command writes to stdout/stderr and may exit the program on failure.
    """
    mpy_dir, _ = find_mpy_root(mpy_dir)
    db = board_database(mpy_dir)
    mpy_dir = db.mpy_root_directory

    if board not in db.boards.keys():
        print("Invalid board")
        raise SystemExit()

    _board = db.boards[board]
    port = _board.port.name

    if variant is not None:
        _variant = _board.find_variant(variant)
        if _variant is None:
            print(f"Invalid variant '{variant}'")
            raise SystemExit()

    if port not in BUILD_CONTAINERS.keys():
        print(f"Sorry, builds are not supported for the {port} port at this time")
        raise SystemExit()

    do_clean = bool(extra_args and extra_args[0].strip() == "clean")
    build_cmd = docker_build_cmd(
        board=_board,
        variant=variant,
        extra_args=extra_args,
        do_clean=do_clean,
        build_container_override=build_container_override,
        docker_interactive=sys.stdin.isatty(),
    )

    title = "Clean" if do_clean else "Build"
    title += f" {port}/{board}" + (f" ({variant})" if variant else "")
    print(Panel(build_cmd, title=title, title_align="left", padding=1))

    proc = subprocess.run(build_cmd, shell=True, check=False)

    if proc.returncode != 0:
        print(f"ERROR: The following command returned {proc.returncode}: {build_cmd}")
        raise SystemExit(proc.returncode)

    # Display deployment markdown for successful builds
    # Note: Only displaying the first deploy file.
    # Q: Are there cases where there's >1? A: Currently, no.
    #    >>> sum([len(b.deploy) for b in db.boards.values()])
    #    166
    #    >>> len(db.boards())
    #    169  # 3x boards are the 'special' boards without deployment instructions.
    if _board.deploy and "clean" not in extra_args and proc.returncode == 0:
        if _board.deploy_filename.is_file():
            print(Panel(Markdown(_board.deploy_filename.read_text())))


def clean_board(
    board: str,
    variant: Optional[str] = None,
    mpy_dir: Optional[str] = None,
) -> None:
    build_board(
        board=board,
        variant=variant,
        mpy_dir=mpy_dir,
        extra_args=["clean"],
    )
