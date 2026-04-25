"""Tests for board_database — Board.factory, Database, and validation rules."""

from __future__ import annotations

import pytest

from mpbuild.board_database import (
    Board,
    Database,
    MpbuildMpyDirectoryException,
    Port,
    Variant,
)


# ===================================================================
# Board.factory
# ===================================================================
class TestBoardFactory:
    def test_minimal(self, mpy_root, make_board):
        """All required fields present: parsed verbatim, physical_board=True."""
        board_dir = make_board(
            "stm32",
            "PYBV11",
            url="https://example.com/pybv11",
            mcu="stm32f4",
            product="Pyboard v1.1",
            vendor="George Robotics",
            images=["pybv1_1.jpg"],
            deploy=["../PYBV10/deploy.md"],
        )
        port = Port(name="stm32", directory=mpy_root / "ports" / "stm32")
        board = Board.factory(port, board_dir / "board.json")

        assert board.name == "PYBV11"
        assert board.mcu == "stm32f4"
        assert board.product == "Pyboard v1.1"
        assert board.vendor == "George Robotics"
        assert board.images == ["pybv1_1.jpg"]
        assert board.deploy == ["../PYBV10/deploy.md"]
        assert board.url == "https://example.com/pybv11"
        assert board.physical_board is True
        assert board.variants == []

    def test_url_default_when_missing(self, mpy_root, make_board):
        """Missing 'url' falls back to micropython.org."""
        board_dir = make_board("stm32", "PYBV11", mcu="stm32f4")
        port = Port(name="stm32", directory=mpy_root / "ports" / "stm32")
        board = Board.factory(port, board_dir / "board.json")
        assert board.url == "http://micropython.org"

    def test_string_fields_default_to_empty(self, mpy_root, make_board):
        """mcu/product/vendor default to '' when absent."""
        board_dir = make_board("stm32", "BARE")
        port = Port(name="stm32", directory=mpy_root / "ports" / "stm32")
        board = Board.factory(port, board_dir / "board.json")
        assert board.mcu == ""
        assert board.product == ""
        assert board.vendor == ""

    def test_list_fields_default_to_empty(self, mpy_root, make_board):
        """images/deploy default to [] when absent."""
        board_dir = make_board("stm32", "BARE")
        port = Port(name="stm32", directory=mpy_root / "ports" / "stm32")
        board = Board.factory(port, board_dir / "board.json")
        assert board.images == []
        assert board.deploy == []

    def test_variants_parsed_and_sorted(self, mpy_root, make_board):
        """variants dict becomes a list of Variant, sorted by name."""
        board_dir = make_board(
            "stm32",
            "PYBV11",
            mcu="stm32f4",
            variants={
                "THREAD": "Threading",
                "DP": "Double-precision float",
                "DP_THREAD": "Double precision float + Threads",
            },
        )
        port = Port(name="stm32", directory=mpy_root / "ports" / "stm32")
        board = Board.factory(port, board_dir / "board.json")

        assert [v.name for v in board.variants] == ["DP", "DP_THREAD", "THREAD"]
        assert board.variants[0].text == "Double-precision float"
        assert board.variants[0].board is board

    def test_variants_default_to_empty(self, mpy_root, make_board):
        """Missing 'variants' key yields an empty list."""
        board_dir = make_board("stm32", "PYBV11", mcu="stm32f4")
        port = Port(name="stm32", directory=mpy_root / "ports" / "stm32")
        board = Board.factory(port, board_dir / "board.json")
        assert board.variants == []


# ===================================================================
# Database.__post_init__ — tree walking and special ports
# ===================================================================
class TestDatabase:
    def test_walks_tree(self, mpy_root, make_board):
        """Discovers boards across multiple ports."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        make_board("stm32", "NUCLEO_F401RE", mcu="stm32f4")
        make_board("rp2", "RPI_PICO", mcu="rp2040")

        db = Database(mpy_root)

        assert "PYBV11" in db.boards
        assert "NUCLEO_F401RE" in db.boards
        assert "RPI_PICO" in db.boards
        assert "stm32" in db.ports
        assert "rp2" in db.ports
        assert set(db.ports["stm32"].boards) == {"PYBV11", "NUCLEO_F401RE"}

    def test_port_filter_narrows_results(self, mpy_root, make_board):
        """port_filter limits both ports and boards to the matched port (plus
        whichever 'special' port matches)."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        make_board("rp2", "RPI_PICO", mcu="rp2040")

        db = Database(mpy_root, port_filter="stm32")

        assert "stm32" in db.ports
        assert "rp2" not in db.ports
        assert "PYBV11" in db.boards
        assert "RPI_PICO" not in db.boards
        # Special ports are also gated by the filter — none match "stm32"
        assert "unix" not in db.ports

    def test_special_ports_added(self, mpy_root):
        """unix/webassembly/windows appear with physical_board=False."""
        db = Database(mpy_root)
        for name in ("unix", "webassembly", "windows"):
            assert name in db.boards
            assert db.boards[name].physical_board is False

    def test_special_port_variants_from_subdir(self, mpy_root):
        """Special-port variants come from variants/* subdirs of the port."""
        unix_variants = mpy_root / "ports" / "unix" / "variants"
        unix_variants.mkdir(parents=True)
        (unix_variants / "standard").mkdir()
        (unix_variants / "minimal").mkdir()

        db = Database(mpy_root)

        unix_board = db.boards["unix"]
        assert {v.name for v in unix_board.variants} == {"standard", "minimal"}

    def test_port_filter_can_select_special_port(self, mpy_root, make_board):
        """port_filter='unix' yields only the unix special port."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root, port_filter="unix")
        assert set(db.ports.keys()) == {"unix"}

    def test_raises_when_ports_dir_missing(self, tmp_path):
        """Database refuses to construct if mpy_root_directory has no ports/."""
        with pytest.raises(ValueError, match="mpy_root_directory"):
            Database(tmp_path)


# ===================================================================
# Database.assert_mpy_root_direcory
# ===================================================================
class TestAssertMpyRootDirectory:
    def test_passes_for_valid_root(self, mpy_root):
        """No exception raised when ports/ exists."""
        Database.assert_mpy_root_direcory(mpy_root)

    def test_raises_for_invalid_root(self, tmp_path):
        """Raises MpbuildMpyDirectoryException when ports/ is missing."""
        with pytest.raises(MpbuildMpyDirectoryException, match="micropython repo"):
            Database.assert_mpy_root_direcory(tmp_path)


# ===================================================================
# Database.check_board_json — validation rules
# ===================================================================
class TestCheckBoardJson:
    @staticmethod
    def _good_board() -> dict:
        return {
            "mcu": "stm32f4",
            "product": "Pyboard v1.1",
            "vendor": "George Robotics",
            "images": ["pybv1_1.jpg"],
            "deploy": ["../PYBV10/deploy.md"],
            "url": "http://example.com",
        }

    def test_no_issues_for_complete(self):
        """A fully populated board.json yields zero issues."""
        assert Database.check_board_json(self._good_board(), "PYBV11", "stm32") == []

    @pytest.mark.parametrize("missing", ["mcu", "product", "vendor", "images", "deploy"])
    def test_missing_required_key(self, missing):
        """Each required key produces a 'Missing required key' issue."""
        bad = self._good_board()
        del bad[missing]
        issues = Database.check_board_json(bad, "PYBV11", "stm32")
        assert len(issues) == 1
        assert f"Missing required key '{missing}'" in issues[0]
        assert "stm32/PYBV11" in issues[0]

    def test_missing_url_separately_reported(self):
        """A missing 'url' is reported as 'Missing URL key' (distinct from required-key)."""
        bad = self._good_board()
        del bad["url"]
        issues = Database.check_board_json(bad, "PYBV11", "stm32")
        assert any("Missing URL key" in i for i in issues)

    def test_variants_must_be_dict(self):
        """A non-dict 'variants' is flagged."""
        bad = self._good_board()
        bad["variants"] = ["DP", "THREAD"]  # list, not dict
        issues = Database.check_board_json(bad, "PYBV11", "stm32")
        assert any("'variants' is not a dictionary" in i for i in issues)

    def test_variants_dict_is_accepted(self):
        """A dict 'variants' produces no issue."""
        good = self._good_board()
        good["variants"] = {"DP": "Double-precision float"}
        assert Database.check_board_json(good, "PYBV11", "stm32") == []

    def test_images_must_be_list(self):
        """A non-list 'images' is flagged."""
        bad = self._good_board()
        bad["images"] = "single.jpg"
        issues = Database.check_board_json(bad, "PYBV11", "stm32")
        assert any("'images' is not a list" in i for i in issues)

    def test_deploy_must_be_list(self):
        """A non-list 'deploy' is flagged."""
        bad = self._good_board()
        bad["deploy"] = "deploy.md"
        issues = Database.check_board_json(bad, "PYBV11", "stm32")
        assert any("'deploy' is not a list" in i for i in issues)


# ===================================================================
# Board / Port property tests
# ===================================================================
class TestBoardProperties:
    def test_directory_for_physical_board(self, mpy_root, make_board):
        """A physical board's directory is ports/<port>/boards/<name>/."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        assert db.boards["PYBV11"].directory == mpy_root / "ports" / "stm32" / "boards" / "PYBV11"

    def test_directory_for_special_board(self, mpy_root):
        """A special board's directory is the port directory itself."""
        (mpy_root / "ports" / "unix").mkdir()
        db = Database(mpy_root)
        assert db.boards["unix"].directory == mpy_root / "ports" / "unix"

    def test_directory_raises_when_missing(self, mpy_root):
        """A board pointing at a non-existent dir raises ValueError."""
        port = Port(name="stm32", directory=mpy_root / "ports" / "stm32")
        board = Board(
            name="GHOST", variants=[], url="", mcu="", product="", vendor="",
            images=[], deploy=[], physical_board=True, port=port,
        )
        with pytest.raises(ValueError, match="Directory does not exist"):
            _ = board.directory

    def test_deploy_filename_when_deploy_set(self, mpy_root, make_board):
        """deploy_filename returns directory/deploy[0]."""
        make_board("stm32", "PYBV11", mcu="stm32f4", deploy=["../PYBV10/deploy.md"])
        db = Database(mpy_root)
        board = db.boards["PYBV11"]
        assert board.deploy_filename == board.directory / "../PYBV10/deploy.md"

    def test_deploy_filename_none_when_deploy_empty(self, mpy_root, make_board):
        """deploy_filename returns None if the deploy list is empty."""
        make_board("stm32", "PYBV11", mcu="stm32f4", deploy=[])
        db = Database(mpy_root)
        assert db.boards["PYBV11"].deploy_filename is None

    def test_find_variant_hit(self, mpy_root, make_board):
        """find_variant returns the matching Variant."""
        make_board(
            "stm32", "PYBV11", mcu="stm32f4",
            variants={"DP": "Double-precision float", "THREAD": "Threading"},
        )
        db = Database(mpy_root)
        variant = db.boards["PYBV11"].find_variant("DP")
        assert isinstance(variant, Variant)
        assert variant.name == "DP"

    def test_find_variant_miss(self, mpy_root, make_board, capsys):
        """find_variant returns None and prints when the variant isn't found."""
        make_board("stm32", "PYBV11", mcu="stm32f4", variants={"DP": "Double"})
        db = Database(mpy_root)
        assert db.boards["PYBV11"].find_variant("NOPE") is None
        captured = capsys.readouterr()
        assert "NOPE" in captured.out
        assert "DP" in captured.out

    def test_port_directory_repo(self, mpy_root, make_board):
        """Port.directory_repo walks up two levels and validates the result."""
        make_board("stm32", "PYBV11", mcu="stm32f4")
        db = Database(mpy_root)
        assert db.ports["stm32"].directory_repo == mpy_root

    def test_port_directory_repo_raises_for_invalid(self, tmp_path):
        """directory_repo raises if the inferred repo isn't a MicroPython tree."""
        port = Port(name="stm32", directory=tmp_path / "ports" / "stm32")
        with pytest.raises(MpbuildMpyDirectoryException):
            _ = port.directory_repo
