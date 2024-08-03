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

## todo

- Check we're at the root of a MicroPython repo
- Tab completion for board names and ports
- May want a way to override the container used for building?
- Add interative modes (textual?) to select boards/variants
