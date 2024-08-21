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

_default_idf_version = "v5.2.2"

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

    if port != "esp32" and idf:
        print("An IDF version can only be specified for ESP32 builds")
        # TODO(mst) Should raise an exception and abort with an error code
        return

    build_container = _build_containers[port]

    if port == "esp32":
        if not idf:
            idf = _default_idf_version
        build_container += f":{idf}"

    # TODO(mst) Will need to replace at least pwd for Windows builds
    build_cmd = (
        f"docker run -it --rm"
        f"-e HOME=/tmp "
        f"-e UID=$(id -u) "
        f"-v /sys/bus:/sys/bus "
        f"-v /dev:/dev "
        f"--net=host --privileged "
        f"-v $(pwd):/$(pwd) -w /$(pwd) "
        f"--user $(id -u):$(id -u)  "
        f"{build_container} "
        f'bash -c "'
        f"git config --global --add safe.directory '*';"
        f'make -C mpy-cross && make -C ports/{port} submodules all BOARD={board}"'
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
        idf = _default_idf_version
        build_container += f":{idf}"

    # Need to replace pwd
    build_cmd = f'docker run -ti --rm -v $(pwd):/w -w /w {build_container} bash -c "make -C mpy-cross clean && make -C ports/{port} clean BOARD={board}"'
    print(build_cmd)
    subprocess.run(build_cmd, shell=True)
