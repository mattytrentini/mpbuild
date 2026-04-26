import glob
import multiprocessing
import os
import re
import subprocess
import sys
from pathlib import Path

from rich import print
from rich.markdown import Markdown
from rich.panel import Panel

from . import board_database, find_mpy_root
from .board_database import Board

ARM_BUILD_CONTAINER = "micropython/build-micropython-arm"
ESP_IDF_CONTAINER = "espressif/idf"
ESP_IDF_FALLBACK_VERSION = "v5.4.2"
BUILD_CONTAINERS = {
    "stm32": ARM_BUILD_CONTAINER,
    "rp2": ARM_BUILD_CONTAINER,
    "nrf": ARM_BUILD_CONTAINER,
    "mimxrt": ARM_BUILD_CONTAINER,
    "renesas-ra": ARM_BUILD_CONTAINER,
    "samd": ARM_BUILD_CONTAINER,
    "psoc6": "ifxmakers/mpy-mtb-ci",
    "esp32": f"{ESP_IDF_CONTAINER}:{ESP_IDF_FALLBACK_VERSION}",
    "esp8266": "larsks/esp-open-sdk",
    "unix": "gcc:12-bookworm",  # Special, doesn't have boards
    "webassembly": ARM_BUILD_CONTAINER,  # installs emsdk on first build
    "windows": "micropython/build-micropython-win-mingw",  # cross compile linux to windows
}


def _detect_idf_version_from_lockfile(mpy_dir: Path, mcu: str) -> str | None:
    """
    Detect the ESP-IDF version from the MicroPython lockfiles (tier 1).

    Each ESP32 chip type (esp32, esp32s2, esp32s3, esp32c3, etc.) has its own
    lockfile at ``ports/esp32/lockfiles/dependencies.lock.<mcu>`` that specifies
    the exact IDF version used for that target.

    Args:
        mpy_dir: Path to the MicroPython repository root.
        mcu: The MCU/chip target name from board.json (e.g., "esp32", "esp32s3").

    Returns:
        The ESP-IDF version string (e.g., "v5.5.1"), or None if detection fails.
    """
    lockfile_path = mpy_dir / "ports" / "esp32" / "lockfiles" / f"dependencies.lock.{mcu}"
    if not lockfile_path.is_file():
        return None

    try:
        content = lockfile_path.read_text()
    except OSError:
        return None

    # Parse the idf dependency version from the lockfile YAML.
    # The structure is:
    #   dependencies:
    #     idf:
    #       source:
    #         type: idf
    #       version: 5.5.1
    # Match "idf:" at the top-level dependency indent, then find its "version:" field.
    match = re.search(r"^  idf:\n(?:    .*\n)*?    version:\s*([\d.]+)", content, re.MULTILINE)
    if match:
        return f"v{match.group(1)}"

    return None


def _detect_idf_version_from_ci_workflow(mpy_dir: Path) -> str | None:
    """
    Detect the recommended ESP-IDF version from the CI workflow file (tier 2).

    Parses ``.github/workflows/ports_esp32.yml`` to find the ``IDF_NEWEST_VER``
    value, which is the newest supported ESP-IDF version.

    Args:
        mpy_dir: Path to the MicroPython repository root.

    Returns:
        The ESP-IDF version string (e.g., "v5.5.1"), or None if detection fails.
    """
    workflow_path = mpy_dir / ".github" / "workflows" / "ports_esp32.yml"
    if not workflow_path.is_file():
        return None

    try:
        content = workflow_path.read_text()
    except OSError:
        return None

    # Match the IDF_NEWEST_VER env variable in the workflow YAML
    # e.g.: IDF_NEWEST_VER: &newest "v5.5.1"
    # or:   IDF_NEWEST_VER: "v5.5.1"
    match = re.search(r"IDF_NEWEST_VER:\s*(?:&\w+\s+)?([\"']?)(v[\d.]+)\1", content)
    if match:
        return match.group(2)

    return None


def detect_idf_version(mpy_dir: Path, mcu: str) -> str | None:
    """
    Detect the ESP-IDF version using a three-tier fallback strategy:

    1. **Lockfile** — per-chip-type lockfile in ``ports/esp32/lockfiles/``
    2. **CI workflow** — ``IDF_NEWEST_VER`` from ``.github/workflows/ports_esp32.yml``
    3. Returns ``None`` so callers can fall back to a hardcoded default.

    Args:
        mpy_dir: Path to the MicroPython repository root.
        mcu: The MCU/chip target name from board.json (e.g., "esp32", "esp32s3").

    Returns:
        The ESP-IDF version string (e.g., "v5.5.1"), or None if all detection fails.
    """
    return _detect_idf_version_from_lockfile(mpy_dir, mcu) or _detect_idf_version_from_ci_workflow(
        mpy_dir
    )


class MpbuildNotSupportedException(Exception):
    pass


def get_build_container(board: Board, variant: str | None = None) -> str:
    """
    Returns the container to be used for this board/variant.

    For the esp32 port, the ESP-IDF version is auto-detected using a
    three-tier fallback:

    1. Lockfile (``ports/esp32/lockfiles/dependencies.lock.<mcu>``) — per chip type
    2. CI workflow (``IDF_NEWEST_VER`` in ``.github/workflows/ports_esp32.yml``)
    3. Hardcoded fallback version

    Example: board="RPI_PICO" => "micropython/build-micropython-arm"
    Example: board="RPI_PICO", variant="RISCV" => "micropython/build-micropython-rp2350riscv"
    Example: board="ESP32_GENERIC" => "espressif/idf:v5.5.1" (auto-detected)
    """
    port = board.port

    if port.name == "rp2":
        if variant == "RISCV":
            # Special case: This board supports an ARM core as default
            # and a RISC-V core as a variant
            return "micropython/build-micropython-rp2350riscv"

        # RP2 requires a recent version of gcc
        return "micropython/build-micropython-arm:bookworm"

    if port.name == "esp32":
        idf_version = detect_idf_version(port.directory_repo, board.mcu)
        if idf_version:
            return f"{ESP_IDF_CONTAINER}:{idf_version}"
        return f"{ESP_IDF_CONTAINER}:{ESP_IDF_FALLBACK_VERSION}"

    try:
        return BUILD_CONTAINERS[port.name]
    except KeyError as e:
        raise MpbuildNotSupportedException(f"{board.name}-{variant}") from e


nprocs = multiprocessing.cpu_count()


def docker_build_cmd(
    board: Board,
    variant: str | None = None,
    extra_args: list[str] | None = None,
    do_clean: bool = False,
    build_container_override: str | None = None,
    docker_interactive: bool = True,
) -> str:
    """
    Returns the docker-command which will build the firmware.
    """
    if extra_args is None:
        extra_args = []

    port = board.port

    if variant:
        v = board.find_variant(variant)
        if not v:
            raise ValueError(
                f"Variant '{variant}' not found for board '{board.name}': "
                f"Valid variants are: {[v.name for v in board.variants]}"
            )

    build_container = (
        build_container_override
        if build_container_override
        else get_build_container(board=board, variant=variant)
    )

    variant_param = "BOARD_VARIANT" if board.physical_board else "VARIANT"
    variant_cmd = "" if variant is None else f" {variant_param}={variant}"

    ci_environment_cmd = ""
    ci_setup_cmd = ""
    if port.name == "webassembly":
        ci_setup_cmd = "source tools/ci.sh; ci_webassembly_setup;"
        ci_environment_cmd = 'source "emsdk/emsdk_env.sh";'
    elif port.name == "windows":
        extra_args = ["CROSS_COMPILE=i686-w64-mingw32-"] + extra_args

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
        ci_environment_cmd = ""
        ci_setup_cmd = ""

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

    # Build the docker run invocation. Each option, in order:
    #   {device_flags}             USB and serial devices for deploy
    #   -v <mpy>:<mpy> -w <mpy>    mount mpy dir at same path so elf/map paths match host
    #   --user <uid>:<gid>         match host user id so generated files aren't owned by root
    #   -e HOME=/tmp               set HOME to /tmp for the container
    build_cmd = (
        f"docker run --rm "
        f"{'-it ' if docker_interactive else ''}"
        f"{device_flags}"
        f"-v {mpy_dir}:{mpy_dir} -w {mpy_dir} "
        f"--user {uid}:{gid} "
        f"-e HOME=/tmp "
        f"{build_container} "
        f'bash -c "'
        f"git config --global --add safe.directory '*' 2> /dev/null;"
        f"{ci_setup_cmd}"
        f"{ci_environment_cmd}"
        f"{make_mpy_cross_cmd}"
        f"{update_submodules_cmd}"
        f'make -j {nprocs} -C ports/{port.name} BOARD={board.name}{variant_cmd}{args}"'
    )

    return build_cmd


def build_board(
    board: str,
    variant: str | None = None,
    extra_args: list[str] | None = None,
    build_container_override: str | None = None,
    mpy_dir: str | Path | None = None,
) -> None:
    """
    Build the firmware.

    This command writes to stdout/stderr and may exit the program on failure.
    """
    if extra_args is None:
        extra_args = []
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
        deploy_path = _board.deploy_filename
        if deploy_path is not None and deploy_path.is_file():
            print(Panel(Markdown(deploy_path.read_text())))


def clean_board(
    board: str,
    variant: str | None = None,
    mpy_dir: str | None = None,
) -> None:
    build_board(
        board=board,
        variant=variant,
        mpy_dir=mpy_dir,
        extra_args=["clean"],
    )
