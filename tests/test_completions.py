from unittest.mock import patch
import pytest

from mpbuild.completions import (
    complete_board,
    complete_port,
    complete_board_variant,
    list_boards,
    list_ports,
    list_variants_for_board,
)


@patch("mpbuild.completions.list_boards")
def test_complete_board(mock_list_boards):
    mock_list_boards.return_value = ["ARDUINO_NANO_RP2040_CONNECT", "ESP32_GENERIC", "RASPBERRY_PI_PICO"]
    
    assert complete_board("") == ["ARDUINO_NANO_RP2040_CONNECT", "ESP32_GENERIC", "RASPBERRY_PI_PICO"]
    assert complete_board("ESP") == ["ESP32_GENERIC"]
    assert complete_board("RAS") == ["RASPBERRY_PI_PICO"]
    assert complete_board("NONEXISTENT") == []


@patch("mpbuild.completions.list_ports")
def test_complete_port(mock_list_ports):
    mock_list_ports.return_value = ["esp32", "rp2", "stm32", "unix"]
    
    assert complete_port("") == ["esp32", "rp2", "stm32", "unix"]
    assert complete_port("esp") == ["esp32"]
    assert complete_port("s") == ["stm32"]
    assert complete_port("nonexistent") == []


@patch("mpbuild.completions.list_boards")
@patch("mpbuild.completions.list_variants_for_board")
def test_complete_board_variant_no_dash(mock_list_variants, mock_list_boards):
    mock_list_boards.return_value = ["ESP32_GENERIC", "RASPBERRY_PI_PICO", "ARDUINO_NANO_RP2040_CONNECT"]
    mock_list_variants.return_value = ["SPIRAM", "D4", "OTA"]
    
    # Test partial board name - single match with variants adds backspace
    with patch("mpbuild.completions.complete_board") as mock_complete_board:
        mock_complete_board.return_value = ["ESP32_GENERIC"]
        result = complete_board_variant("ESP")
        assert result == ["ESP32_GENERIC\\b"]
    
    # Test exact board name with variants - includes board and variant options
    with patch("mpbuild.completions.complete_board") as mock_complete_board:
        mock_complete_board.return_value = ["ESP32_GENERIC"]
        result = complete_board_variant("ESP32_GENERIC")
        # When exact match found in boards list, it adds variant options to the list
        assert set(result) == {"ESP32_GENERIC", "ESP32_GENERIC-SPIRAM", "ESP32_GENERIC-D4", "ESP32_GENERIC-OTA"}
    
    # Test board with no variants
    with patch("mpbuild.completions.complete_board") as mock_complete_board:
        mock_complete_board.return_value = ["RASPBERRY_PI_PICO"]
        mock_list_variants.return_value = []
        result = complete_board_variant("RASPBERRY_PI_PICO")
        assert result == []


@patch("mpbuild.completions.list_boards")
@patch("mpbuild.completions.list_variants_for_board")
def test_complete_board_variant_with_dash(mock_list_variants, mock_list_boards):
    mock_list_boards.return_value = ["ESP32_GENERIC", "RASPBERRY_PI_PICO"]
    mock_list_variants.return_value = ["SPIRAM", "D4", "OTA"]
    
    # Test partial variant
    result = complete_board_variant("ESP32_GENERIC-S")
    assert result == ["ESP32_GENERIC-SPIRAM"]
    
    # Test all variants
    result = complete_board_variant("ESP32_GENERIC-")
    assert set(result) == {"ESP32_GENERIC-SPIRAM", "ESP32_GENERIC-D4", "ESP32_GENERIC-OTA"}
    
    # Test invalid board
    result = complete_board_variant("INVALID_BOARD-")
    assert result == []


@patch("mpbuild.completions.list_boards")
@patch("mpbuild.completions.list_variants_for_board")
def test_complete_board_variant_single_match_with_variants(mock_list_variants, mock_list_boards):
    """Test the bug fix for undefined variants variable"""
    mock_list_boards.return_value = ["RASPBERRY_PI_PICO"]
    mock_list_variants.return_value = ["W", "2"]
    
    with patch("mpbuild.completions.complete_board") as mock_complete_board:
        # Single board match, but incomplete name
        mock_complete_board.return_value = ["RASPBERRY_PI_PICO"]
        result = complete_board_variant("RAS")
        # Should complete the board name with backspace to allow variant completion
        assert result == ["RASPBERRY_PI_PICO\\b"]


@patch("mpbuild.completions.list_boards")
@patch("mpbuild.completions.list_variants_for_board")
def test_complete_board_variant_single_match_no_variants(mock_list_variants, mock_list_boards):
    """Test single board match with no variants"""
    mock_list_boards.return_value = ["ARDUINO_NANO_RP2040_CONNECT"]
    mock_list_variants.return_value = []
    
    with patch("mpbuild.completions.complete_board") as mock_complete_board:
        # Single board match, but incomplete name, no variants
        mock_complete_board.return_value = ["ARDUINO_NANO_RP2040_CONNECT"]
        result = complete_board_variant("ARD")
        # Should just complete the board name without backspace
        assert result == ["ARDUINO_NANO_RP2040_CONNECT"]