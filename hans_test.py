from mpbuild import find_boards, build, find_boards_hmaerki

"""
mpbuild build RPI_PICO2 --build-container micropython/build-micropython-arm:bookworm

https://forums.raspberrypi.com/viewtopic.php?p=2245570#p2245570

Target board (PICO_BOARD) is 'pico2'.
Using board configuration from /home/maerki/work_octoprobe_testbed_tutorial/git_cache/micropython_firmware_a8dacbe8afd409416648f667b0aa01b5/lib/pico-sdk/src/boards/include/boards/pico2.h
Pico Platform (PICO_PLATFORM) is 'rp2350-riscv'.
Defaulting compiler (PICO_COMPILER) to 'pico_riscv_gcc' since not specified.
Configuring toolchain based on PICO_COMPILER 'pico_riscv_gcc'
"""


def get_build_container(port: str, board: str, variant: str) -> str | None:
    return "build-micropython-arm-rp2riscv"
    if board == "RPI_PICO2":
        if variant == "RISCV":
            return "build-micropython-arm-rp2riscv"
        return "micropython/build-micropython-arm:bookworm"
    return None


def main():
    db = find_boards_hmaerki.Database()
    for variant in db.dict_boards["PYBV11"].iter_variants():
        print(variant)
    """
    Build rp2 RPI_PICO None
    Build stm32 PYBV11 None
    Build stm32 PYBV11 DP
    Build stm32 PYBV11 DP_THREAD
    Build stm32 PYBV11 NETWORK
    Build stm32 PYBV11 THREAD
    """
    for board in ("RPI_PICO", "PYBV11"):
        for port, variant in find_boards.ivariants(board):
            print(f"Build {port} {board} {variant}")


def main2():
    list_firmwares = []
    # for board in ("M5STACK_ATOM", "ESP32_GENERIC", "WEACTSTUDIO", "RPI_PICO", "ADAFRUIT_F405_EXPRESS", "PYBV11"):
    for board in ("RPI_PICO", "PYBV11"):
        for port, variant in find_boards.ivariants(board):
            print(f"Build {board} {variant}")
            firmware_filename = build.build_board(port, board, variant)
            print(firmware_filename)
            assert firmware_filename.exists(), firmware_filename
            list_firmwares.append(firmware_filename)

    print(f"=== build {len(list_firmwares)} firmwares")
    for firmware_filename in list_firmwares:
        print(firmware_filename)


def main3():
    list_firmwares = []
    db = find_boards_hmaerki.Database()
    # for board_name in ("M5STACK_ATOM", "ESP32_GENERIC", "WEACTSTUDIO", "RPI_PICO", "RPI_PICO2", "ADAFRUIT_F405_EXPRESS", "PYBV11"):
    for board_name in ("RPI_PICO", "RPI_PICO2", "PYBV11"):
        board = db.dict_boards[board_name]
        for variant in board.variants:
            print(f"Build {variant.name_normalized}")
            firmware_filename = build.build_board(
                variant.board.port.name,
                variant.board.name,
                variant.name,
                build_container_override="build-micropython-arm-rp2riscv",
            )
            print(firmware_filename)
            assert firmware_filename.exists(), firmware_filename
            list_firmwares.append(firmware_filename)

    print(f"=== build {len(list_firmwares)} firmwares")
    for firmware_filename in list_firmwares:
        print(firmware_filename)


def main5():
    def build_board(port: str, board: str, variant: str):
        firmware_filename = build.build_board(
            port,
            board,
            variant,
            build_container_override=get_build_container(port, board, variant),
        )
        print(firmware_filename)

    # build_board("rp2", "RPI_PICO2", "")
    build_board("rp2", "RPI_PICO2", "RISCV")


main3()
