# mpbuild

## Usage

```bash
> mpbuild build BOARD [VARIANT]
```

```bash
> mpbuild clean BOARD [VARIANT]
```

```bash
> mpbuild list [--port PORT]
```

- Should it list boards and variants? (yes, probably. Alternatively, '-a'.)


## requirements to use on Linux

- Docker or compatible container runtime
- Python 3.x

## Requirements to use on Windows

- Docker or compatible container runtime using WSL2
- Python 3.x
- WSL2
- Linux Distro: Ubuntu, Arch, Kali-linux have been tested

- micropython repo cloned to a WSL2 hosted directory
  `/home/<user>/micropython`

- MICROPY_DIR set to the WSL2 hosted directory
  `$env:MICROPY_DIR="\\wsl.localhost\Ubuntu\home\<user>\micropython"`

- Optional: Windows drive letter mapped to WSL2 hosted directory
  `net use U: \\wsl$\Ubuntu`
  `dir U:\home\<user>\micropython\ports\rp2\build_RPI_PICO\firmware.uf2`

## Development

- rye for managing the project
    ``` shell
    rye sync
    rye build
    ```
- Use ruff for formatting
- pre-commit
  - ruff formatting and linting

## todo

- Check we're at the root of a MicroPython repo
- Tab completion for board names and ports
- May want a way to override the container used for building?
- Add interative modes (textual?) to select boards/variants
- Fix version - only use the version number from pyproject.toml
  - And query it with importlib.metadata.version
- Check docker is in the path
- IDF version should be configurable
- Add unix and webassembly 'special' builds (no boards, build by port name)
