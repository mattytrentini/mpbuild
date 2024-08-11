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

## Development

- rye for managing the project
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
- IDF version should be passed in
