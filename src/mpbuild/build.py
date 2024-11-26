import os
from typing import Optional, List

from pathlib import Path
import multiprocessing
import subprocess

from rich import print
from rich.panel import Panel
from rich.markdown import Markdown

from . import board_database, find_mpy_root
from .board_database import Variant, DEFAULT_VARIANT

ARM_BUILD_CONTAINER = "micropython/build-micropython-arm"
BUILD_CONTAINERS = {
    "stm32": ARM_BUILD_CONTAINER,
    "rp2": ARM_BUILD_CONTAINER,
    "nrf": ARM_BUILD_CONTAINER,
    "mimxrt": ARM_BUILD_CONTAINER,
    "renesas-ra": ARM_BUILD_CONTAINER,
    "samd": ARM_BUILD_CONTAINER,
    "esp32": "espressif/idf",
    "unix": "gcc:12-bookworm",  # Special, doesn't have boards
}


class MpbuildNotSupportedException(Exception):
    pass


def get_build_container(variant: Variant) -> str:
    """
    Returns the container to be used for this variant.

    Example: variant="RPI_PICO" => "micropython/build-micropython-arm"
    Example: variant="RPI_PICO RISCV" => "micropython/build-micropython-rp2350riscv"
    """
    assert isinstance(variant, Variant)
    assert variant.board.port is not None
    port = variant.board.port

    if variant.board.name == "RPI_PICO2":
        if variant.name == "RISCV":
            # Special case: This board supports a arm core as default
            # and a riscv core as a variant
            return "micropython/build-micropython-rp2350riscv"

        # RP2 requires a recent version of gcc
        return "micropython/build-micropython-arm:bookworm"

    try:
        return BUILD_CONTAINERS[port.name]
    except KeyError as e:
        raise MpbuildNotSupportedException(variant.name) from e


IDF_DEFAULT = "v5.2.2"

nprocs = multiprocessing.cpu_count()


def docker_build_cmd(
    variant: Variant,
    extra_args: List[str],
    do_clean: bool,
    build_container_override: str | None = None,
    idf: str = IDF_DEFAULT,
    docker_interactive: bool = True,
) -> str:
    """
    Returns the docker-command which will build the firmware.

    This is the command which may be called programatically.
    Therefor this command should NOT:
      * write to stdout/stderr
      * exit the program
    """
    assert isinstance(variant, Variant), variant
    assert isinstance(extra_args, list), extra_args
    assert isinstance(do_clean, bool), do_clean
    assert isinstance(build_container_override, str | None), build_container_override
    assert isinstance(idf, str), idf

    board = variant.board
    assert board.port is not None
    port = board.port

    build_container = (
        build_container_override
        if build_container_override
        else get_build_container(variant)
    )

    if port.name == "esp32" and not build_container_override:
        if not idf:
            idf = IDF_DEFAULT
        build_container += f":{idf}"

    variant_param = "BOARD_VARIANT" if variant.board.physical_board else "VARIANT"
    variant_cmd = (
        "" if variant.is_default_variant else f" {variant_param}={variant.name}"
    )

    args = " " + " ".join(extra_args)

    make_mpy_cross_cmd = "make -C mpy-cross && "
    update_submodules_cmd = (
        f"make -C ports/{port.name} submodules BOARD={board.name}{variant_cmd} && "
    )

    uid, gid = os.getuid(), os.getgid()

    if do_clean:
        # When cleaning we run with full privs
        uid, gid = 0, 0
        # Don't need to build mpy_cross or update submodules
        make_mpy_cross_cmd = ""
        update_submodules_cmd = ""

    home = os.environ["HOME"]
    mpy_dir = str(port.directory_repo)

    # fmt: off
    build_cmd = (
        f"docker run --rm "
        f"{'-it ' if docker_interactive else ''}"
        f"-v /sys/bus:/sys/bus "                # provides access to USB for deploy
        f"-v /dev:/dev "                        # provides access to USB for deploy
        f"--net=host --privileged "             # provides access to USB for deploy
        f"-v {mpy_dir}:{mpy_dir} -w {mpy_dir} " # mount micropython dir with same path so elf/map paths match host
        f"--user {uid}:{gid} "                  # match running user id so generated files aren't owned by root
        f"-v {home}:{home} -e HOME={home} "     # when changing user id to one not present in container this ensures home is writable
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
    idf: Optional[str] = IDF_DEFAULT,
    mpy_dir: str | Path | None = None,
) -> None:
    # mpy_dir = mpy_dir or Path.cwd()
    # mpy_dir = Path(mpy_dir)
    mpy_dir, _ = find_mpy_root(mpy_dir)
    db = board_database(mpy_dir)
    mpy_dir = db.mpy_root_directory

    if board not in db.boards.keys():
        print("Invalid board")
        raise SystemExit()

    _board = db.boards[board]
    port = _board.port.name
    variant = variant if variant else DEFAULT_VARIANT
    _variant = _board.find_variant(variant)
    if _variant is None:
        print(f"Invalid variant '{variant}'")
        raise SystemExit()

    if port not in BUILD_CONTAINERS.keys():
        print(f"Sorry, builds are not supported for the {port} port at this time")
        raise SystemExit()

    if port != "esp32" and idf != IDF_DEFAULT:
        print("An IDF version can only be specified for ESP32 builds")
        raise SystemExit()

    do_clean = bool(extra_args and extra_args[0].strip() == "clean")
    build_cmd = docker_build_cmd(
        variant=_variant,
        extra_args=extra_args,
        do_clean=do_clean,
        build_container_override=build_container_override,
        idf=idf,
    )

    title = "Build" if do_clean else "Clean"
    title += f" {port}/{board}" + (f" ({variant})" if variant else "")
    print(Panel(build_cmd, title=title, title_align="left", padding=1))

    proc = subprocess.run(build_cmd, shell=True, check=False)

    if proc.returncode != 0:
        print(f"ERROR: The following command returned {proc.returncode}: {build_cmd}")
        raise SystemExit(proc.returncode)

    # Display deployment markdown
    # Note: Only displaying the first deploy file.
    # Q: Are there cases where there's >1? A: Currently, no.
    #    >>> sum([len(b.deploy) for b in db.boards.values()])
    #    166
    #    >>> len(db.boards())
    #    169  # 3x boards are the 'special' boards without deployment instructions.
    if _board.deploy and "clean" not in extra_args:
        if _board.deploy_filename.is_file():
            print(Panel(Markdown(_board.deploy_filename.read_text())))


def clean_board(
    board: str,
    variant: Optional[str] = None,
    idf: Optional[str] = IDF_DEFAULT,
    mpy_dir: Optional[str] = None,
) -> None:
    build_board(
        board=board,
        variant=variant,
        mpy_dir=mpy_dir,
        idf=idf,
        extra_args=["clean"],
    )
