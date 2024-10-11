import os
import sys
from typing import Optional, List, Tuple

from pathlib import Path
import multiprocessing
import subprocess

from rich import print
from rich.panel import Panel
from rich.markdown import Markdown

from . import board_database, find_mpy_root

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

IDF_DEFAULT = "v5.2.2"

nprocs = multiprocessing.cpu_count()


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

    if board not in db.boards.keys():
        print("Invalid board")
        raise SystemExit()

    _board = db.boards[board]
    port = _board.port.name

    if variant and variant not in [v.name for v in _board.variants]:
        print("Invalid variant")
        raise SystemExit()

    if port not in BUILD_CONTAINERS.keys():
        print(f"Sorry, builds are not supported for the {port} port at this time")
        raise SystemExit()

    if port != "esp32" and idf != IDF_DEFAULT:
        print("An IDF version can only be specified for ESP32 builds")
        raise SystemExit()

    build_container = (
        build_container_override if build_container_override else BUILD_CONTAINERS[port]
    )

    if port == "esp32" and not build_container_override:
        if not idf:
            idf = IDF_DEFAULT
        build_container += f":{idf}"

    variant_param = "VARIANT" if board == port else "BOARD_VARIANT"
    variant_cmd = f" {variant_param}={variant}" if variant else ""

    args = " " + " ".join(extra_args)

    make_mpy_cross_cmd = "make -C mpy-cross && "
    update_submodules_cmd = f"make -C ports/{port} submodules BOARD={board}{variant_cmd} && "
    if sys.platform != "win32":
        uid, gid = os.getuid(), os.getgid()
    else:
        uid, gid = (1000, 1000)  # Default to user id 1000 for Windows WSL2

    if extra_args and extra_args[0].strip() == "clean":
        # When cleaning we run with full privs
        uid, gid = 0, 0
        # Don't need to build mpy_cross or update submodules
        make_mpy_cross_cmd = ""
        update_submodules_cmd = ""

    home = str(Path.home())
    mpy_dir = db.mpy_root_directory

    if sys.platform == "win32":
        mpy_dir, home = adapt_for_wsl(mpy_dir, home)
    # fmt: off
    build_cmd = (
        f"docker run -it --rm "
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
        f'make -j {nprocs} -C ports/{port} BOARD={board}{variant_cmd}{args}"'
    )
    # fmt: on
    if sys.platform == "win32":
        build_cmd = f"wsl -- {build_cmd}"

    title = "Build" if "clean" not in extra_args else "Clean"
    title += f" {port}/{board}" + (f" ({variant})" if variant else "")
    print(Panel(build_cmd, title=title, title_align="left", padding=1))

    subprocess.run(build_cmd, shell=True)

    # Display deployment markdown
    # Note: Only displaying the first deploy file.
    # Q: Are there cases where there's >1? A: Currently, no.
    #    >>> sum([len(b.deploy) for b in db.boards.values()])
    #    166
    #    >>> len(db.boards())
    #    169  # 3x boards are the 'special' boards without deployment instructions.
    if _board.deploy and "clean" not in extra_args:
        deploy_filename = Path(
            "/".join(
                [
                    str(mpy_dir),
                    "ports",
                    _board.port.name,
                    "boards",
                    _board.name,
                    _board.deploy[0],
                ]
            )
        )
        if deploy_filename.is_file():
            with open(deploy_filename) as deployfile:
                print(Panel(Markdown(deployfile.read())))


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


def adapt_for_wsl(mpy_dir: Path, home: str) -> Tuple[str, str]:
    """Adapt paths for running docker from WSL2.
    Both windows and wsl paths to the repo are supported , but wsl hosted paths are faster.
    """
    # wsl2 home directory is /home/<username>
    r = subprocess.run(
        'wsl -e bash -c "printenv"', capture_output=True, text=True, universal_newlines=True
    )
    for line in r.stdout.splitlines():
        if line.startswith("HOME="):
            wsl_home = line.split("=")[1]
        elif line.startswith("WSL_DISTRO_NAME="):
            distro = line.split("=")[1]

    # Translate windows paths to wsl paths
    if ":\\" in str(mpy_dir):
        warning = (
            f"The MicroPython repo is located on the Windows path: [bold]{mpy_dir}[/bold].\n"
            f"While this should work, please note that builds will be [bold]6-60 times slower[/bold].\n"
            f"For the fastest performance speed, store your files on the WSL file system , for example in: [bold]{home}/micropython[/bold]\n"
            f"See https://learn.microsoft.com/en-us/windows/wsl/filesystems#file-storage-and-performance-across-file-systems for more information."
        )
        print(Panel(warning, title="[bold]Warning[/bold]", title_align="left", style="yellow"))

        # PYBV11 WSL Hosted      : 19s   0:19 minutes
        # PYBV11 Windows Hosted  : 126s  2:06 minutes (6 times slower)
        # RPI_PICO WSL Hosted    : 12s   0:20 minutes
        # RPI_PICO Windows Hosted: 1095s 18:25 minutes (60 times slower)
        r = subprocess.run(
            f'wsl wslpath "{mpy_dir}"', capture_output=True, text=True, universal_newlines=True
        )
        wsl_mpy_dir = r.stdout.strip()
    else:
        # Translate windows unc paths to wsl paths
        # Assuming distro = Ubuntu
        distro = distro or "TEST-Ubuntu"
        wsl_mpy_dir = (
            mpy_dir.as_posix()
            .replace(f"//wsl$/{distro}/", "/")
            .replace(f"//wsl.localhost/{distro}/", "/")
        )
        if "//wsl$" in wsl_mpy_dir:
            raise ValueError(
                f"mpy_dir: {mpy_dir} is not located on the default WSL2 distro: {distro}."
            )
    wsl_home = wsl_home or home
    return wsl_mpy_dir, wsl_home
