"""
This is the api interface for mpbuild
"""

import re
import time
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from .board_database import Board
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

    def __init__(
        self, board: Board, variant: Optional[str], proc: subprocess.CompletedProcess
    ) -> None:
        super().__init__(f"Failed to build {board.name}-{variant}")
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

    board: Board
    """
    The board used to build the firmware.

    This is used by octoprobe to find matching MCUs/boards.
    """

    variant: Optional[str]
    """
    None: Default variant
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
        return f"Firmware({self.variant_name_full}, {self.filename}, {self.micropython_version_text})"

    @property
    def variant_name_full(self) -> str:
        """
        return <port>-<board>-<variant>
        """
        name = f"{self.board.port.name}-{self.board.name}"
        if self.variant is None:
            return name
        return name + f"{name}-{self.variant}"

    @property
    def variant_normalized(self) -> str:
        """
        return <board>-<variant>
        """
        if self.variant is None:
            return self.board.name
        return f"{self.board.name}-{self.variant}"


_FIRMWARE_FILENAMES = {
    "esp32": "firmware.bin",
    "esp8266": "firmware.bin",
    "rp2": "firmware.uf2",
    "samd": "firmware.bin",
    "stm32": "firmware.dfu",
    "unix": "micropython",
}


class BuildFolder:
    """
    This class extracts information from the build folder:
    * the firmware filename
    * the micropython version text (e.g. '3.4.0; MicroPython v1.24.0 on 2024-10-25')
    """

    _REGEX_MICROPY_GIT_TAG = re.compile(r'MICROPY_GIT_TAG\s+"(.*?)"')
    """
    Example input: #define MICROPY_GIT_TAG "v1.24.1"
    """

    _REGEX_MICROPY_BUILD_DATE = re.compile(r'MICROPY_BUILD_DATE\s+"(.*?)"')
    """
    Example input: #define MICROPY_BUILD_DATE "2024-12-05"
    """

    _REGEX_MICROPY_SYS_VERSION = re.compile(r'mp_sys_version_obj, "(\d+\.\d+\.\d+); "')
    """
    static const MP_DEFINE_STR_OBJ(mp_sys_version_obj, "3.4.0; " MICROPY_BANNER_NAME_AND_VERSION);
    """

    def __init__(self, board: Board, variant: Optional[str]) -> None:
        self.board = board
        self.variant = variant

        def get_build_folder() -> Path:
            if board.physical_board:
                # Example: board_name == 'stm32'
                build_directory = f"build-{self.board.name}"
                if variant is not None:
                    build_directory += f"-{variant}"
                return self.board.port.directory / build_directory

            # Example: board_name == 'unix'
            build_directory = "build"
            if variant is not None:
                build_directory += f"-{variant}"
            return self.board.port.directory / build_directory

        self.build_folder = get_build_folder()

    @property
    def firmware_filename(self) -> Path:
        """
        Returns the filename of the compiled binary.
        """
        filename = _FIRMWARE_FILENAMES.get(self.board.port.name, None)
        if filename is None:
            raise MpbuildNotSupportedException(
                f"Entry port='{self.board.port.name}' missing in 'FIRMWARE_FILENAMES'!"
            )

        _filename = self.build_folder / filename
        if not _filename.is_file():
            raise MpbuildException(
                f"The firmware for {self.board.name}-{self.variant} was not found: {_filename}"
            )

        return _filename

    @property
    def micro_version_text(self) -> str:
        """
        Example: '3.4.0; MicroPython v1.24.0 on 2024-10-25'
        """
        filename_mpversion_h = self.build_folder / "genhdr" / "mpversion.h"

        repo_folder = self.build_folder.parents[2]
        filename_modsys_c = repo_folder / "py" / "modsys.c"

        def get_regex(filename: Path, pattern: re.Pattern) -> str:
            try:
                text = filename.read_text()
            except FileNotFoundError as e:
                raise MpbuildException(
                    f"Firmware for {self.board.name}-{self.variant}: Could not read: {filename}"
                ) from e

            match = pattern.search(text)
            if match is None:
                raise MpbuildException(
                    f"Firmware for {self.board.name}-{self.variant}: Could not find '{pattern.pattern}' in: {filename}"
                )
            return match.group(1)

        git_tag = get_regex(filename_mpversion_h, self._REGEX_MICROPY_GIT_TAG)
        build_date = get_regex(filename_mpversion_h, self._REGEX_MICROPY_BUILD_DATE)
        modsys = get_regex(filename_modsys_c, self._REGEX_MICROPY_SYS_VERSION)
        return f"{modsys}; MicroPython {git_tag} on {build_date}"


def build(
    logfile: Path,
    board: Board,
    variant: Optional[str] = None,
    do_clean: bool = False,
) -> Firmware:
    """ """

    build_cmd = docker_build_cmd(
        board=board,
        variant=variant,
        do_clean=do_clean,
        extra_args=[],
        docker_interactive=False,
    )

    with logfile.open("w") as f:
        begin_s = time.monotonic()
        f.write(f"{build_cmd}\n\n\n")
        f.flush()
        proc = subprocess.run(
            build_cmd,
            shell=True,
            check=False,
            text=True,
            stdout=f,
            stderr=subprocess.STDOUT,
        )
        f.write(f"\n\nreturncode={proc.returncode}\n")
        f.write(f"duration={time.monotonic()-begin_s:0.3f}s\n")

    if proc.returncode != 0:
        raise MpbuildDockerException(board=board, variant=variant, proc=proc)

    build_folder = BuildFolder(board=board, variant=variant)

    return Firmware(
        filename=build_folder.firmware_filename,
        board=board,
        variant=variant,
        micropython_version_text=build_folder.micro_version_text,
    )


def build_by_variant_normalized(
    logfile: Path, db: Database, variant_normalized: str, do_clean: bool
) -> Firmware:
    """
    This is the main entry point into mpbuild.

    'variant_normalized' is taken from the micropython filename convention:
    Examples (filename -> variant_normalized):
        PYBV11-20241129-v1.24.1.dfu  ->  PYBV11
        PYBV11-THREAD-20241129-v1.24.1.dfu  ->  PYBV11-THREAD

    This will build the firmware and return
    * firmware: Firmware: The path to the firmware and much more
    * proc: The output from the docker container. This might be useful for logging purposes.

    If the build fails:
    * an exception is raised
    * captured output with the error message is written to stdout/strerr (it would be better to write it to a logfile)
    """

    board_str, _, variant_str = variant_normalized.partition("-")
    # Example variant_str:
    #  "": for the default variant
    #  "THREAD": for variant "THREAD"

    try:
        board = db.boards[board_str]
    except KeyError as e:
        raise MpbuildException(
            f"Board '{board_str}' not found. Valid boards are {[b for b in db.boards]}"
        ) from e

    variant = None if variant_str == "" else variant_str

    return build(logfile=logfile, board=board, variant=variant, do_clean=do_clean)
