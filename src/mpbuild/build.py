import os
from typing import Optional, List

import multiprocessing
import subprocess

from . import board_database
from .find_boards import find_mpy_root

ARM_BUILD_CONTAINER = "micropython/build-micropython-arm"
BUILD_CONTAINERS = {
    "stm32": ARM_BUILD_CONTAINER,
    "rp2": ARM_BUILD_CONTAINER,
    "nrf": ARM_BUILD_CONTAINER,
    "mimxrt": ARM_BUILD_CONTAINER,
    "renesas-ra": ARM_BUILD_CONTAINER,
    "samd": ARM_BUILD_CONTAINER,
    "esp32": "espressif/idf",
    "unix": "micropython/build-micropython-unix",  # Special, doesn't have boards
}

IDF_DEFAULT = "v5.2.2"

nprocs = multiprocessing.cpu_count()


def build_board(
    board: str,
    variant: Optional[str] = None,
    extra_args: Optional[List[str]] = [],
    build_container_override: Optional[str] = None,
    idf: Optional[str] = IDF_DEFAULT,
    mpy_dir: str = None,
) -> None:
    mpy_dir, _ = find_mpy_root(mpy_dir)

    db = board_database()
    port = db.boards[board].port.name

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
    variant = f" {variant_param}={variant}" if variant else ""

    args = " " + " ".join(extra_args)

    make_mpy_cross_cmd = "make -C mpy-cross && "
    update_submodules_cmd = (
        f"make -C ports/{port} submodules BOARD={board}{variant} && "
    )

    uid, gid = os.getuid(), os.getgid()

    if extra_args and extra_args[0].strip() == "clean":
        # When cleaning we run with full privs
        uid, gid = 0, 0
        # Don't need to build mpy_cross or update submodules
        make_mpy_cross_cmd = ""
        update_submodules_cmd = ""

    home = os.environ["HOME"]

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
        f'make -j {nprocs} -C ports/{port} BOARD={board}{variant}{args}"'
    )
    # fmt: on

    print(build_cmd)
    subprocess.run(build_cmd, shell=True)


def clean_board(
    board: str,
    variant: Optional[str] = None,
    idf: Optional[str] = IDF_DEFAULT,
    mpy_dir: str = None,
) -> None:
    build_board(
        board=board,
        variant=variant,
        mpy_dir=mpy_dir,
        idf=idf,
        extra_args=["clean"],
    )
