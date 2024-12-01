#
# Compile some microptyhon firmware.
#
# If the environment variable 'MICROPY_DIR' is set, it should point
# to the ports directory of the micropython repository.
#
set -eox pipefail # https://www.youtube.com/watch?v=9fSkygQ-ZjI

if [ -n "$MICROPY_DIR" ]; then
  # This might be dangerous for firmware developers: All changes to the micropython repo will be undone!
  git -C $MICROPY_DIR clean -fXd

  cd $MICROPY_DIR
fi


if [ ! -d "`pwd`/ports/renesas-ra" ]; then
  echo "`pwd`/ports/renesas-ra does NOT exist. Please make 'MICROPY_DIR' to point to the micropython ports directory."
  exit 1
fi

mpbuild list

# Standard case
mpbuild build RPI_PICO2

# Special case: Variant uses another build container
mpbuild build RPI_PICO2 RISCV

# Standard case
mpbuild build PYBV11
mpbuild build ESP8266_GENERIC

# Special case: Variant
mpbuild build PYBV11 THREAD

# Special case: Unix
mpbuild build unix
mpbuild build unix minimal

# Special case: Webassembly
# mpbuild build webassembly
# mpbuild build webassembly standard

# Special case: Windows
# mpbuild build windows
# mpbuild build windows dev
# mpbuild build windows standard

