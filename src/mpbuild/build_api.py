"""
This is the api interface for mpbuild
"""

import subprocess
from pathlib import Path
from dataclasses import dataclass

from .board_database import Variant
from .build import MpbuildNotSupportedException, docker_build_cmd
from .board_database import Database


class MpbuildException(Exception):
    """
    Thrown by the API if the build fails.
    """


class MpbuildDockerException(MpbuildException):
    """
    Thrown by the API if docker fails.
    The exception contains
    * the variant which failed
    * proc.returncode
    * proc.stdout
    * proc.stderr

    stdout/stderr might be very long!
    """

    def __init__(self, variant: Variant, proc: subprocess.CompletedProcess) -> None:
        super().__init__(f"Failed to build {variant.name_full}")
        self.proc = proc

    def __str__(self) -> str:
        """
        As the docker build failed, also return the docker output - which may be many lines long!
        """
        lines = (
            super().__str__(),
            f"returncode: {self.proc.returncode}",
            f"stdout: {self.proc.stdout}",
            f"stderr: {self.proc.stderr}",
        )
        return "\n  ".join(lines)


@dataclass(frozen=True, order=True)
class Firmware:
    filename: Path
    """
    the compiled firmware
    """

    variant: Variant
    """
    The variant used to build the firmware.

    This is used by octoprobe to find matching MCUs/boards.
    """

    micropython_version_text: str | None
    """
    Example:
    Calling '>>> micropython_version'
    on firmware https://micropython.org/resources/firmware/PYBV11-20240602-v1.23.0.dfu
    will return: '3.4.0; MicroPython v1.23.0 on 2024-06-02'

    This string will be used by octoprobe to verify if the correct firmware is installed.

    Set to 'None' if the value is not known.
    """

    def __str__(self) -> str:
        return f"Firmware({self.variant.name_full}, {self.filename}, {self.micropython_version_text})"


_FIRMWARE_FILENAMES = {
    "stm32": "firmware.dfu",
    "rp2": "firmware.uf2",
    "esp32": "micropython.bin",
    "unix": "micropython",
}


def get_firmware_filename(variant: Variant) -> Path:
    """
    Returns the filename of the compiled binary.
    """
    try:
        board = variant.board
        assert board.port is not None
        port = board.port
        port_name = port.name
        board_name = variant.board.name
        variant_name = variant.name

        filename = _FIRMWARE_FILENAMES[port_name]
        if board.physical_board:
            # Example: board_name == 'stm32'
            build_directory = f"build-{board_name}"
            if not variant.is_default_variant:
                build_directory += f"-{variant_name}"
            return port.directory / build_directory / filename

        # Example: board_name == 'unix'
        return port.directory / f"build-{variant_name}" / filename
    except KeyError as e:
        raise MpbuildNotSupportedException(
            f"Entry port='{port_name}' missing in 'FIRMWARE_FILENAMES'!"
        ) from e


def build_by_variant(
    variant: Variant, do_clean: bool
) -> tuple[Firmware, subprocess.CompletedProcess]:
    """ """
    assert isinstance(variant, Variant)
    assert isinstance(do_clean, bool)

    build_cmd = docker_build_cmd(
        variant=variant,
        do_clean=do_clean,
        extra_args=[],
        docker_interactive=False,
    )

    proc = subprocess.run(
        build_cmd,
        shell=True,
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        # print(f"Error calling: {build_cmd}")
        # print(f"stdout: {proc.stdout}")
        # print(f"stderr: {proc.stderr}")
        raise MpbuildDockerException(variant=variant, proc=proc)

    filename = get_firmware_filename(variant)
    if not filename.is_file():
        raise MpbuildException(
            f"The firmware for {variant.name_full} was not found: {filename}"
        )

    return (
        Firmware(filename=filename, variant=variant, micropython_version_text=None),
        proc,
    )


def build_by_variant_str(
    db: Database, variant_str: str, do_clean: bool
) -> tuple[Firmware, subprocess.CompletedProcess]:
    """
    This will build the firmware and return
    * firmware: Firmware: The path to the firmware and much more
    * proc: The output from the docker container. This might be useful for logging purposes.

    If the build fails:
    * an exception is raised
    * captured output with the error message is written to stdout/strerr (it would be better to write it to a logfile)
    """
    assert isinstance(db, Database)
    assert isinstance(variant_str, str)
    assert isinstance(do_clean, bool)

    board_str, _, variant_str = variant_str.partition("-")
    db_variant = db.get_board(board_str).get_variant(variant_str)
    return build_by_variant(variant=db_variant, do_clean=do_clean)
