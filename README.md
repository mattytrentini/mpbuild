<div align="center">

# mpbuild

![](https://github.com/user-attachments/assets/2cf9fb34-aae4-4e24-a16c-76d387ca6dff)

Build MicroPython firmware with ease!

**mpbuild** builds MicroPython firmware in containers so you don't need to install any compiler toolchains or development tools. It knows which containers to use for each board so the appropriate build tools are used.

</div>

## Table of Contents

- [Usage](#usage)
  - [Advanced Usage](#advanced-usage)
  - [Use as a Module](#use-as-a-module)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
- [Examples](#examples)
- [Related links](#related-links)

## Usage

**mpbuild** is intended to be executed in the root of a MicroPython repository. Help text (accessed with adding `--help`) is extensive and documents advanced options.

> [!NOTE]
> Note that there are some _special_ builds. `unix`, `webassembly` and `windows` can all be specified as `BOARD`s but their target isn't a microcontroller. See the [MicroPython documentation](https://github.com/micropython/micropython/) for details.

> [!WARNING]
> Currently **mpbuild** is tested on Linux (specifically Ubuntu 24.04 on WSL on Windows 11) but it's intended to work on any platform that supports Docker.

Build a board, with optional variant:

```bash
mpbuild build BOARD[-VARIANT]
```

Remove build artifacts:

```bash
mpbuild clean BOARD[-VARIANT]
```

List the available boards, optionally filter by the port name.

Displays the board names (as a clickable link), variants and number of boards per port:

```bash
mpbuild list [PORT]
```

## Advanced Usage

Validate the state of all images referenced in board definitions:

```bash
mpbuild check_images
```

## Use as a Module

> [!CAUTION]
> This is _very much_ a work-in-progress and the API is subject to change.

**mpbuild** can also be used from Python as a module. This allows it to easily be integrated into other tools.

Example:

```python
import mpbuild

mpbuild.build("RPI_PICO")
mpbuild.list()
```

## Testing

Run the test suite with pytest:

```bash
pytest
```

Run tests with coverage report:

```bash
pytest --cov=mpbuild --cov-report=term-missing
```

## Installation

```bash
uv tool install mpbuild
```

Or use pipx, pip etc.

After installation, you may want to also install command-line tab completion for your shell (bash, zsh, fish and PowerShell are supported). Tab completion includes the various mpbuild commands as well as the board names and variants:

```bash
mpbuild --install-completion
```

### Prerequisites

A clone of MicroPython (or a fork):

```bash
git clone git@github.com:micropython/micropython.git
```

[Docker](https://www.docker.com/) is currently necessary for managing containers and must be installed and available on your system path.

## Examples

```bash
$ mpbuild build RPI_PICO
# Downloads appropriate containers and builds firmware for the Raspberry Pi Pico
```

```bash
$ mpbuild list rp2
🐍 MicroPython Boards
└── rp2   19
    ├── ADAFRUIT_FEATHER_RP2040
    ├── ADAFRUIT_ITSYBITSY_RP2040
    ├── ADAFRUIT_QTPY_RP2040
    ├── ARDUINO_NANO_RP2040_CONNECT
    ├── GARATRONIC_PYBSTICK26_RP2040
    ├── NULLBITS_BIT_C_PRO
    ├── PIMORONI_PICOLIPO  FLASH_16M
    ├── PIMORONI_TINY2040  FLASH_8M
    ├── POLOLU_3PI_2040_ROBOT
    ├── POLOLU_ZUMO_2040_ROBOT
    ├── RPI_PICO
    ├── RPI_PICO2  RISCV
    ├── RPI_PICO_W
    ├── SIL_RP2040_SHIM
    ├── SPARKFUN_PROMICRO
    ├── SPARKFUN_THINGPLUS
    ├── W5100S_EVB_PICO
    ├── W5500_EVB_PICO
    └── WEACTSTUDIO  FLASH_2M, FLASH_4M, FLASH_8M
```
