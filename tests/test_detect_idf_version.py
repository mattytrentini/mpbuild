"""Tests for ESP-IDF version detection (three-tier fallback)."""

from mpbuild.build import (
    _detect_idf_version_from_lockfile,
    _detect_idf_version_from_ci_workflow,
    detect_idf_version,
)

# ---------------------------------------------------------------------------
# Sample lockfile content matching the real MicroPython format
# ---------------------------------------------------------------------------
LOCKFILE_ESP32 = """\
dependencies:
  espressif/lan867x:
    component_hash: 0ff9dae3affeff53811e7c8283e67c6d36dc0c03e3bc5102c0fba629e08bf6c4
    dependencies:
    - name: idf
      require: private
      version: '>=5.3'
    source:
      registry_url: https://components.espressif.com/
      type: service
    targets:
    - esp32
    - esp32p4
    version: 1.0.3
  espressif/mdns:
    component_hash: 46ee81d32fbf850462d8af1e83303389602f6a6a9eddd2a55104cb4c063858ed
    dependencies:
    - name: idf
      require: private
      version: '>=5.0'
    source:
      registry_url: https://components.espressif.com/
      type: service
    version: 1.1.0
  idf:
    source:
      type: idf
    version: 5.5.1
direct_dependencies:
- espressif/lan867x
- espressif/mdns
- idf
manifest_hash: 40b684ab14058130e675aab422296e4ad9d87ee39c5aa46d7b3df55c245e14f5
target: esp32
version: 2.0.0
"""

LOCKFILE_ESP32S3 = """\
dependencies:
  espressif/mdns:
    version: 1.1.0
  idf:
    source:
      type: idf
    version: 5.4.2
direct_dependencies:
- espressif/mdns
- idf
target: esp32s3
version: 2.0.0
"""

CI_WORKFLOW = (
    'env:\n  IDF_OLDEST_VER: &oldest "v5.3"\n  IDF_NEWEST_VER: &newest "v5.5.1"\n'
)


# ===================================================================
# Tier 1 – Lockfile detection
# ===================================================================
class TestLockfileDetection:
    def test_esp32_version(self, mpy_root, make_lockfile):
        """Detects IDF version from the esp32 lockfile."""
        make_lockfile("esp32", LOCKFILE_ESP32)
        assert _detect_idf_version_from_lockfile(mpy_root, "esp32") == "v5.5.1"

    def test_esp32s3_version(self, mpy_root, make_lockfile):
        """Detects IDF version from the esp32s3 lockfile."""
        make_lockfile("esp32s3", LOCKFILE_ESP32S3)
        assert _detect_idf_version_from_lockfile(mpy_root, "esp32s3") == "v5.4.2"

    def test_per_chip_type(self, mpy_root, make_lockfile):
        """Different chip types can report different IDF versions."""
        make_lockfile("esp32", LOCKFILE_ESP32)
        make_lockfile("esp32s3", LOCKFILE_ESP32S3)
        assert _detect_idf_version_from_lockfile(mpy_root, "esp32") == "v5.5.1"
        assert _detect_idf_version_from_lockfile(mpy_root, "esp32s3") == "v5.4.2"

    def test_missing_lockfile(self, mpy_root):
        """Returns None when the lockfile does not exist."""
        assert _detect_idf_version_from_lockfile(mpy_root, "esp32") is None

    def test_wrong_mcu(self, mpy_root, make_lockfile):
        """Returns None when lockfile exists for esp32 but not the requested MCU."""
        make_lockfile("esp32", LOCKFILE_ESP32)
        assert _detect_idf_version_from_lockfile(mpy_root, "esp32c6") is None

    def test_no_idf_in_lockfile(self, mpy_root, make_lockfile):
        """Returns None when the lockfile has no idf dependency."""
        make_lockfile(
            "esp32",
            "dependencies:\n  espressif/mdns:\n    version: 1.1.0\ntarget: esp32\n",
        )
        assert _detect_idf_version_from_lockfile(mpy_root, "esp32") is None

    def test_prepends_v(self, mpy_root, make_lockfile):
        """Lockfile stores '5.5.1'; result must be 'v5.5.1'."""
        make_lockfile("esp32", LOCKFILE_ESP32)
        result = _detect_idf_version_from_lockfile(mpy_root, "esp32")
        assert result is not None and result.startswith("v")


# ===================================================================
# Tier 2 – CI workflow detection
# ===================================================================
class TestCIWorkflowDetection:
    def test_with_anchor_and_quotes(self, mpy_root, make_workflow):
        """Standard format: IDF_NEWEST_VER: &newest "v5.5.1" """
        make_workflow(CI_WORKFLOW)
        assert _detect_idf_version_from_ci_workflow(mpy_root) == "v5.5.1"

    def test_without_anchor(self, mpy_root, make_workflow):
        make_workflow('env:\n  IDF_NEWEST_VER: "v5.4.2"\n')
        assert _detect_idf_version_from_ci_workflow(mpy_root) == "v5.4.2"

    def test_single_quotes(self, mpy_root, make_workflow):
        make_workflow("env:\n  IDF_NEWEST_VER: 'v5.4.1'\n")
        assert _detect_idf_version_from_ci_workflow(mpy_root) == "v5.4.1"

    def test_without_quotes(self, mpy_root, make_workflow):
        make_workflow("env:\n  IDF_NEWEST_VER: v5.3\n")
        assert _detect_idf_version_from_ci_workflow(mpy_root) == "v5.3"

    def test_missing_workflow(self, mpy_root):
        assert _detect_idf_version_from_ci_workflow(mpy_root) is None

    def test_no_idf_version_in_workflow(self, mpy_root, make_workflow):
        make_workflow("name: esp32 port\non:\n  push:\n")
        assert _detect_idf_version_from_ci_workflow(mpy_root) is None


# ===================================================================
# Combined – three-tier fallback (detect_idf_version)
# ===================================================================
class TestDetectIdfVersionFallback:
    def test_lockfile_wins_over_ci(self, mpy_root, make_lockfile, make_workflow):
        """Tier 1 (lockfile) takes priority over tier 2 (CI workflow)."""
        make_lockfile("esp32", LOCKFILE_ESP32)  # version 5.5.1
        make_workflow('env:\n  IDF_NEWEST_VER: "v5.3"\n')  # version v5.3
        assert detect_idf_version(mpy_root, "esp32") == "v5.5.1"

    def test_falls_back_to_ci_when_no_lockfile(self, mpy_root, make_workflow):
        """When lockfile is missing, tier 2 (CI workflow) is used."""
        make_workflow(CI_WORKFLOW)
        assert detect_idf_version(mpy_root, "esp32") == "v5.5.1"

    def test_falls_back_to_ci_for_unknown_mcu(
        self, mpy_root, make_lockfile, make_workflow
    ):
        """Lockfile exists for esp32, but not for esp32c6 → falls back to CI."""
        make_lockfile("esp32", LOCKFILE_ESP32)
        make_workflow('env:\n  IDF_NEWEST_VER: "v5.4.0"\n')
        assert detect_idf_version(mpy_root, "esp32c6") == "v5.4.0"

    def test_returns_none_when_nothing_available(self, mpy_root):
        """Returns None when neither lockfile nor CI workflow is available."""
        assert detect_idf_version(mpy_root, "esp32") is None
