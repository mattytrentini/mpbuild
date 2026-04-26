"""Tests for the interactive Textual TUI.

Uses Textual's Pilot harness (App.run_test()) for headless interaction.
"""

from __future__ import annotations

import pytest
from textual.widgets import Button, Select, Static, Tree

from mpbuild import board_database
from mpbuild.find_boards import find_mpy_root
from mpbuild.interactive import MpBuildApp

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _clear_caches():
    """find_mpy_root and board_database are @cache-decorated; clear between tests."""
    find_mpy_root.cache_clear()
    board_database.cache_clear()
    yield
    find_mpy_root.cache_clear()
    board_database.cache_clear()


@pytest.fixture
def populated_mpy_root(mpy_root, make_board, monkeypatch):
    """An mpy_root with two ports / three boards, plus monkeypatched cwd so the
    `board_database()` factory locates it."""
    make_board(
        "stm32",
        "PYBV11",
        mcu="stm32f4",
        product="Pyboard v1.1",
        vendor="George Robotics",
        images=[],
        deploy=[],
        variants={"DP": "Double-precision float", "THREAD": "Threading"},
    )
    make_board(
        "stm32",
        "NUCLEO_F401RE",
        mcu="stm32f4",
        product="Nucleo F401RE",
        vendor="ST",
        images=[],
        deploy=[],
    )
    make_board(
        "rp2",
        "RPI_PICO",
        mcu="rp2040",
        product="Raspberry Pi Pico",
        vendor="Raspberry Pi",
        images=[],
        deploy=[],
    )
    monkeypatch.chdir(mpy_root)
    return mpy_root


async def test_tree_populates_with_ports_and_boards(populated_mpy_root):
    """The tree's first level shows ports; expanding shows boards."""
    app = MpBuildApp()
    async with app.run_test():
        tree = app.query_one("#board-tree", Tree)
        port_labels = {str(child.label) for child in tree.root.children}
        assert "stm32" in port_labels
        assert "rp2" in port_labels

        stm32_node = next(c for c in tree.root.children if str(c.label) == "stm32")
        board_labels = {str(leaf.label) for leaf in stm32_node.children}
        assert board_labels == {"PYBV11", "NUCLEO_F401RE"}


async def test_actions_disabled_until_board_selected(populated_mpy_root):
    """Build, Clean, and the variant Select all start disabled."""
    app = MpBuildApp()
    async with app.run_test():
        assert app.query_one("#build-btn", Button).disabled is True
        assert app.query_one("#clean-btn", Button).disabled is True
        assert app.query_one("#variant-select", Select).disabled is True


async def test_selecting_a_board_populates_info_and_enables_actions(populated_mpy_root):
    """Programmatically selecting a board populates the info panel
    and enables Build/Clean."""
    app = MpBuildApp()
    async with app.run_test() as pilot:
        tree = app.query_one("#board-tree", Tree)
        # Find the PYBV11 leaf and select it via Tree's API.
        stm32_node = next(c for c in tree.root.children if str(c.label) == "stm32")
        stm32_node.expand()
        pybv11_leaf = next(leaf for leaf in stm32_node.children if str(leaf.label) == "PYBV11")
        tree.select_node(pybv11_leaf)
        await pilot.pause()

        info = app.query_one("#info-text", Static)
        rendered = str(info.render())
        assert "Pyboard v1.1" in rendered
        assert "stm32f4" in rendered
        assert "George Robotics" in rendered

        assert app.query_one("#build-btn", Button).disabled is False
        assert app.query_one("#clean-btn", Button).disabled is False


async def test_variant_select_shown_for_board_with_variants(populated_mpy_root):
    """A board with variants reveals the variant Select."""
    app = MpBuildApp()
    async with app.run_test() as pilot:
        tree = app.query_one("#board-tree", Tree)
        stm32_node = next(c for c in tree.root.children if str(c.label) == "stm32")
        stm32_node.expand()
        pybv11 = next(leaf for leaf in stm32_node.children if str(leaf.label) == "PYBV11")
        tree.select_node(pybv11)
        await pilot.pause()

        select = app.query_one("#variant-select", Select)
        assert select.display is True
        # The Select isn't disabled (a board is selected) and it allows
        # selecting one of the variants we provided.
        assert select.disabled is False


async def test_variant_select_hidden_for_board_without_variants(populated_mpy_root):
    """RPI_PICO has no variants; the Select stays hidden after selection."""
    app = MpBuildApp()
    async with app.run_test() as pilot:
        tree = app.query_one("#board-tree", Tree)
        rp2_node = next(c for c in tree.root.children if str(c.label) == "rp2")
        rp2_node.expand()
        pico_leaf = next(leaf for leaf in rp2_node.children if str(leaf.label) == "RPI_PICO")
        tree.select_node(pico_leaf)
        await pilot.pause()

        assert app.query_one("#variant-select", Select).display is False


async def test_selecting_port_node_keeps_actions_disabled(populated_mpy_root):
    """Selecting a port (non-leaf) shouldn't enable the build/clean actions."""
    app = MpBuildApp()
    async with app.run_test() as pilot:
        tree = app.query_one("#board-tree", Tree)
        stm32_node = next(c for c in tree.root.children if str(c.label) == "stm32")
        tree.select_node(stm32_node)
        await pilot.pause()

        assert app.query_one("#build-btn", Button).disabled is True
        assert app.query_one("#clean-btn", Button).disabled is True


async def test_right_arrow_expands_branch(populated_mpy_root):
    """Right arrow on a collapsed port node expands it."""
    app = MpBuildApp()
    async with app.run_test() as pilot:
        tree = app.query_one("#board-tree", Tree)
        stm32_node = next(c for c in tree.root.children if str(c.label) == "stm32")
        assert stm32_node.is_expanded is False
        tree.move_cursor(stm32_node)
        tree.focus()
        await pilot.press("right")
        await pilot.pause()
        assert stm32_node.is_expanded is True


async def test_left_arrow_collapses_branch(populated_mpy_root):
    """Left arrow on an expanded port node collapses it."""
    app = MpBuildApp()
    async with app.run_test() as pilot:
        tree = app.query_one("#board-tree", Tree)
        stm32_node = next(c for c in tree.root.children if str(c.label) == "stm32")
        stm32_node.expand()
        await pilot.pause()
        assert stm32_node.is_expanded is True
        tree.move_cursor(stm32_node)
        tree.focus()
        await pilot.press("left")
        await pilot.pause()
        assert stm32_node.is_expanded is False
