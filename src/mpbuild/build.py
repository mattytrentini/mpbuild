from typing import Optional

import subprocess

# ['esp8266', 'esp32', 'samd', 'nrf', 'renesas-ra', 'mimxrt', 'stm32', 'cc3200', 'rp2']

_arm_build_container = "micropython/build-micropython-arm"
_build_containers = {
    "stm32": _arm_build_container,
    "rp2": _arm_build_container,
    "nrf": _arm_build_container,
    "mimxrt": _arm_build_container,
    "renesas-ra": _arm_build_container,
    "samd": _arm_build_container,
    "esp32": "espressif/idf:v5.2.2",
    "unix": "micropython/build-micropython-unix",  # Special, doesn't have boards
}


def build_board(port: str, board: str, variant: Optional[str] = None) -> None:
    if port not in _build_containers.keys():
        print(f"Sorry, builds are not supported for the {port} port at this time")
        # TODO(mst) Should raise an exception and abort with an error code
        return

    build_container = _build_containers[port]

    # Need to replace pwd
    build_cmd = f'docker run -ti --rm -v $(pwd):/w -w /w {build_container} bash -c "make -C mpy-cross && make -C ports/{port} submodules all BOARD={board}"'
    print(build_cmd)
    subprocess.run(build_cmd, shell=True)


def clean_board(port: str, board: str, variant: Optional[str] = None) -> None:
    if port not in _build_containers.keys():
        print(f"Sorry, builds are not supported for the {port} port at this time")
        # TODO(mst) Should raise an exception and abort with an error code
        return

    build_container = _build_containers[port]

    # Need to replace pwd
    build_cmd = f'docker run -ti --rm -v $(pwd):/w -w /w {build_container} bash -c "make -C mpy-cross clean && make -C ports/{port} clean BOARD={board}"'
    print(build_cmd)
    subprocess.run(build_cmd, shell=True)
