"""Tests for the typer CLI surface (cli.py).

These tests exercise argument parsing and dispatch — the underlying
implementations (build_board, clean_board, print_boards, check_boards)
are monkeypatched so the CLI is tested in isolation.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from mpbuild import OutputFormat, __version__
from mpbuild.cli import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ===================================================================
# --version
# ===================================================================
class TestVersion:
    def test_long_form(self, runner):
        """`mpbuild --version` prints the version and exits 0."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert f"mpbuild v{__version__}" in result.output

    def test_short_form(self, runner):
        """`mpbuild -v` does the same."""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert f"mpbuild v{__version__}" in result.output


# ===================================================================
# build
# ===================================================================
class TestBuild:
    def test_dispatches_with_defaults(self, runner, monkeypatch):
        """`mpbuild build BOARD` calls build_board with default-shaped args."""
        called = {}

        def fake(board, variant, extra_args, build_container):
            called.update(
                board=board, variant=variant,
                extra_args=extra_args, build_container=build_container,
            )

        monkeypatch.setattr("mpbuild.cli.build_board", fake)

        result = runner.invoke(app, ["build", "PYBV11"])

        assert result.exit_code == 0
        assert called == {
            "board": "PYBV11",
            "variant": None,
            "extra_args": [],
            "build_container": None,
        }

    def test_with_variant(self, runner, monkeypatch):
        """A second positional argument is forwarded as the variant."""
        called = {}
        monkeypatch.setattr(
            "mpbuild.cli.build_board",
            lambda b, v, e, c: called.update(b=b, v=v, e=e, c=c),
        )
        result = runner.invoke(app, ["build", "PYBV11", "DP_THREAD"])
        assert result.exit_code == 0
        assert called == {"b": "PYBV11", "v": "DP_THREAD", "e": [], "c": None}

    def test_empty_string_variant_normalised_to_none(self, runner, monkeypatch):
        """An explicit '' variant is converted to None before dispatch."""
        called = {}
        monkeypatch.setattr(
            "mpbuild.cli.build_board",
            lambda b, v, e, c: called.update(v=v),
        )
        result = runner.invoke(app, ["build", "PYBV11", ""])
        assert result.exit_code == 0
        assert called["v"] is None

    def test_build_container_override(self, runner, monkeypatch):
        """The --build-container flag is forwarded as the override.

        Note: chain=True on the typer app means options must precede
        positional arguments — a `--xxx` token after a positional is
        interpreted as the next subcommand in the chain.
        """
        called = {}
        monkeypatch.setattr(
            "mpbuild.cli.build_board",
            lambda b, v, e, c: called.update(c=c),
        )
        result = runner.invoke(
            app, ["build", "--build-container", "custom/image:tag", "PYBV11"]
        )
        assert result.exit_code == 0
        assert called["c"] == "custom/image:tag"


# ===================================================================
# clean
# ===================================================================
class TestClean:
    def test_dispatches_with_defaults(self, runner, monkeypatch):
        """`mpbuild clean BOARD` calls clean_board with variant=None."""
        called = {}
        monkeypatch.setattr(
            "mpbuild.cli.clean_board",
            lambda b, v: called.update(b=b, v=v),
        )
        result = runner.invoke(app, ["clean", "PYBV11"])
        assert result.exit_code == 0
        assert called == {"b": "PYBV11", "v": None}

    def test_with_variant(self, runner, monkeypatch):
        called = {}
        monkeypatch.setattr(
            "mpbuild.cli.clean_board",
            lambda b, v: called.update(b=b, v=v),
        )
        result = runner.invoke(app, ["clean", "PYBV11", "DP_THREAD"])
        assert result.exit_code == 0
        assert called == {"b": "PYBV11", "v": "DP_THREAD"}


# ===================================================================
# list
# ===================================================================
class TestList:
    def test_no_args_uses_defaults(self, runner, monkeypatch):
        """`mpbuild list` calls print_boards(None, OutputFormat.rich)."""
        called = {}
        monkeypatch.setattr(
            "mpbuild.cli.print_boards",
            lambda port, fmt: called.update(port=port, fmt=fmt),
        )
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert called["port"] is None
        assert called["fmt"] == OutputFormat.rich

    def test_with_port_and_format(self, runner, monkeypatch):
        """--format must come before the positional under chain=True."""
        called = {}
        monkeypatch.setattr(
            "mpbuild.cli.print_boards",
            lambda port, fmt: called.update(port=port, fmt=fmt),
        )
        result = runner.invoke(app, ["list", "--format", "text", "stm32"])
        assert result.exit_code == 0
        assert called["port"] == "stm32"
        assert called["fmt"] == OutputFormat.text


# ===================================================================
# check_boards / check_images (legacy alias)
# ===================================================================
class TestCheckBoards:
    def test_check_boards(self, runner, monkeypatch):
        called = {}
        monkeypatch.setattr(
            "mpbuild.cli.check_boards",
            lambda verbose: called.update(verbose=verbose),
        )
        result = runner.invoke(app, ["check_boards"])
        assert result.exit_code == 0
        assert called == {"verbose": False}

    def test_check_boards_verbose(self, runner, monkeypatch):
        called = {}
        monkeypatch.setattr(
            "mpbuild.cli.check_boards",
            lambda verbose: called.update(verbose=verbose),
        )
        result = runner.invoke(app, ["check_boards", "--verbose"])
        assert result.exit_code == 0
        assert called == {"verbose": True}

    def test_legacy_check_images_alias(self, runner, monkeypatch):
        """The hidden 'check_images' command still dispatches to check_boards."""
        called = {}
        monkeypatch.setattr(
            "mpbuild.cli.check_boards",
            lambda verbose: called.update(verbose=verbose),
        )
        result = runner.invoke(app, ["check_images"])
        assert result.exit_code == 0
        assert called == {"verbose": False}


# ===================================================================
# Import smoke — guards against the class of bug PR #96 fixed
# (undeclared dep on typing_extensions broke `import mpbuild.cli`)
# ===================================================================
class TestImportSmoke:
    def test_cli_module_imports_cleanly(self):
        """Importing mpbuild.cli must not raise — would have caught the
        typing_extensions ModuleNotFoundError regression at test time."""
        import importlib

        import mpbuild.cli

        importlib.reload(mpbuild.cli)
