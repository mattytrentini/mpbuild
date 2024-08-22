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
    "esp32": "espressif/idf",
    "unix": "micropython/build-micropython-unix",  # Special, doesn't have boards
}

IDF_DEFAULT = "v5.2.2"

# docker run -it --rm -e HOME=/tmp  -e BOARD=$BOARD -e ARGS="$ARGS" -e
# DEPLOY_PORT=$DEPLOY_PORT -e UID=$(id -u) -v /sys/bus:/sys/bus -v /dev:/dev
# --net=host --privileged -v "$CD":"$CD" -w "$CD" --user 1000:1000
# espressif/idf:$IDF_VER bash -c "git config --global --add safe.directory
# '*';make -C ports/esp32 BOARD=ESP32_GENERIC_C3"


def build_board(
    port: str, board: str, variant: Optional[str] = None, idf: Optional[str] = None
) -> None:
    if port not in _build_containers.keys():
        print(f"Sorry, builds are not supported for the {port} port at this time")
        # TODO(mst) Should raise an exception and abort with an error code
        return

    if port != "esp32" and idf != IDF_DEFAULT:
        print("An IDF version can only be specified for ESP32 builds")
        # TODO(mst) Should raise an exception and abort with an error code
        return

    build_container = _build_containers[port]

    if port == "esp32":
        if not idf:
            idf = IDF_DEFAULT
        build_container += f":{idf}"

    args = f"BOARD_VARIANT={variant}" if variant else ""
    
    # TODO(mst) Will need to replace at least pwd for Windows builds
    build_cmd = (
        f"docker run -it --rm "
        f"-v /sys/bus:/sys/bus "            # provides access to USB for deploy
        f"-v /dev:/dev "                    # provides access to USB for deploy
        f"--net=host --privileged "         # provides access to USB for deploy
        f"-v $(pwd):/$(pwd) -w /$(pwd) "    # mount micropython dir with same path so elf/map paths match host
        f"--user $(id -u):$(id -u)  "       # match running user id so generated files aren't owned by root
        f"-e HOME=/tmp "                    # when changing user id to one not present in container this ensures home is writable
        f"{build_container} "
        f'bash -c "'
        f"git config --global --add safe.directory '*' 2> /dev/null;"
        f'make -C mpy-cross && make -C ports/{port} submodules all BOARD={board} {args}"'
    )

    print(build_cmd)
    subprocess.run(build_cmd, shell=True)


def clean_board(port: str, board: str, variant: Optional[str] = None) -> None:
    if port not in _build_containers.keys():
        print(f"Sorry, builds are not supported for the {port} port at this time")
        # TODO(mst) Should raise an exception and abort with an error code
        return

    build_container = _build_containers[port]

    if port == "esp32":
        idf = IDF_DEFAULT
        build_container += f":{idf}"

    # Don't change the UID here, run clean at full permissions possible.
    build_cmd = (
        f'docker run -ti --rm '
        f'-v $(pwd):$(pwd) -w $(pwd) '
        f'{build_container} '
        f'bash -c "make -C mpy-cross clean && make -C ports/{port} clean BOARD={board}"'
    )
    print(build_cmd)
    subprocess.run(build_cmd, shell=True)
