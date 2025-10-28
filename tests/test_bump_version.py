"""
Comprehensive tests for version bump script.

Tests the bump-version.sh script that handles semantic versioning
for manual deployment workflow.
"""

import subprocess
from pathlib import Path

import pytest


class TestBumpVersionScript:
    """Tests for bump-version.sh script."""

    @pytest.fixture
    def script_path(self):
        """Get path to bump-version.sh script."""
        return Path(__file__).parent.parent / "scripts" / "bump-version.sh"

    def run_script(self, script_path, current_version, bump_type):
        """Helper to run the bump-version.sh script."""
        result = subprocess.run(
            [str(script_path), current_version, bump_type],
            capture_output=True,
            text=True,
        )
        return result

    def test_script_exists(self, script_path):
        """Test that bump-version.sh script exists."""
        assert script_path.exists(), f"Script not found at {script_path}"
        assert script_path.is_file(), "Script path is not a file"

    def test_script_is_executable(self, script_path):
        """Test that script has executable permissions."""
        import stat

        st = script_path.stat()
        assert st.st_mode & stat.S_IXUSR, "Script is not executable"

    def test_patch_version_bump(self, script_path):
        """Test patch version bump (X.Y.Z -> X.Y.Z+1)."""
        result = self.run_script(script_path, "v1.2.3", "patch")

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert result.stdout.strip() == "v1.2.4"
        assert "v1.2.3 → v1.2.4 (patch)" in result.stderr

    def test_minor_version_bump(self, script_path):
        """Test minor version bump (X.Y.Z -> X.Y+1.0)."""
        result = self.run_script(script_path, "v1.2.3", "minor")

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert result.stdout.strip() == "v1.3.0"
        assert "v1.2.3 → v1.3.0 (minor)" in result.stderr

    def test_major_version_bump(self, script_path):
        """Test major version bump (X.Y.Z -> X+1.0.0)."""
        result = self.run_script(script_path, "v1.2.3", "major")

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert result.stdout.strip() == "v2.0.0"
        assert "v1.2.3 → v2.0.0 (major)" in result.stderr

    def test_version_without_v_prefix(self, script_path):
        """Test version bump works without 'v' prefix."""
        result = self.run_script(script_path, "1.2.3", "patch")

        assert result.returncode == 0
        assert result.stdout.strip() == "v1.2.4"

    def test_initial_version_patch(self, script_path):
        """Test patch bump from v0.0.0."""
        result = self.run_script(script_path, "v0.0.0", "patch")

        assert result.returncode == 0
        assert result.stdout.strip() == "v0.0.1"

    def test_initial_version_minor(self, script_path):
        """Test minor bump from v0.0.0."""
        result = self.run_script(script_path, "v0.0.0", "minor")

        assert result.returncode == 0
        assert result.stdout.strip() == "v0.1.0"

    def test_initial_version_major(self, script_path):
        """Test major bump from v0.0.0."""
        result = self.run_script(script_path, "v0.0.0", "major")

        assert result.returncode == 0
        assert result.stdout.strip() == "v1.0.0"

    def test_large_version_numbers(self, script_path):
        """Test bump with large version numbers."""
        result = self.run_script(script_path, "v99.99.99", "patch")

        assert result.returncode == 0
        assert result.stdout.strip() == "v99.99.100"

    def test_major_bump_resets_minor_and_patch(self, script_path):
        """Test that major bump resets minor and patch to 0."""
        result = self.run_script(script_path, "v1.5.8", "major")

        assert result.returncode == 0
        assert result.stdout.strip() == "v2.0.0"

    def test_minor_bump_resets_patch(self, script_path):
        """Test that minor bump resets patch to 0."""
        result = self.run_script(script_path, "v1.5.8", "minor")

        assert result.returncode == 0
        assert result.stdout.strip() == "v1.6.0"

    def test_missing_arguments_fails(self, script_path):
        """Test that script fails when arguments are missing."""
        result = subprocess.run(
            [str(script_path)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Missing required arguments" in result.stdout

    def test_missing_bump_type_fails(self, script_path):
        """Test that script fails when bump type is missing."""
        result = subprocess.run(
            [str(script_path), "v1.2.3"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Missing required arguments" in result.stdout

    def test_invalid_bump_type_fails(self, script_path):
        """Test that script fails with invalid bump type."""
        result = self.run_script(script_path, "v1.2.3", "invalid")

        assert result.returncode != 0
        assert "Invalid bump type" in result.stdout

    def test_invalid_version_format_fails(self, script_path):
        """Test that script fails with invalid version format."""
        result = self.run_script(script_path, "1.2", "patch")

        assert result.returncode != 0
        assert "Invalid version format" in result.stdout

    def test_invalid_version_with_letters_fails(self, script_path):
        """Test that script fails with non-numeric version."""
        result = self.run_script(script_path, "v1.2.a", "patch")

        assert result.returncode != 0
        assert "Invalid version format" in result.stdout

    def test_version_with_extra_parts_fails(self, script_path):
        """Test that script fails with more than 3 version parts."""
        result = self.run_script(script_path, "v1.2.3.4", "patch")

        assert result.returncode != 0
        assert "Invalid version format" in result.stdout


class TestVersionBumpEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def script_path(self):
        """Get path to bump-version.sh script."""
        return Path(__file__).parent.parent / "scripts" / "bump-version.sh"

    def run_script(self, script_path, current_version, bump_type):
        """Helper to run the bump-version.sh script."""
        result = subprocess.run(
            [str(script_path), current_version, bump_type],
            capture_output=True,
            text=True,
        )
        return result

    def test_zero_version_components(self, script_path):
        """Test bumping when some components are zero."""
        test_cases = [
            ("v0.0.1", "patch", "v0.0.2"),
            ("v0.1.0", "minor", "v0.2.0"),
            ("v1.0.0", "major", "v2.0.0"),
            ("v0.0.0", "patch", "v0.0.1"),
        ]

        for current, bump_type, expected in test_cases:
            result = self.run_script(script_path, current, bump_type)
            assert result.returncode == 0
            assert result.stdout.strip() == expected, (
                f"Failed for {current} + {bump_type}: "
                f"expected {expected}, got {result.stdout.strip()}"
            )

    def test_single_digit_versions(self, script_path):
        """Test all single-digit version combinations."""
        result = self.run_script(script_path, "v1.2.3", "patch")
        assert result.returncode == 0
        assert result.stdout.strip() == "v1.2.4"

    def test_double_digit_versions(self, script_path):
        """Test double-digit version numbers."""
        result = self.run_script(script_path, "v10.20.30", "patch")
        assert result.returncode == 0
        assert result.stdout.strip() == "v10.20.31"

    def test_triple_digit_versions(self, script_path):
        """Test triple-digit version numbers."""
        result = self.run_script(script_path, "v100.200.300", "minor")
        assert result.returncode == 0
        assert result.stdout.strip() == "v100.201.0"

    def test_case_sensitive_bump_type(self, script_path):
        """Test that bump type is case-sensitive."""
        invalid_cases = ["Patch", "PATCH", "Minor", "MINOR", "Major", "MAJOR"]

        for invalid_type in invalid_cases:
            result = self.run_script(script_path, "v1.2.3", invalid_type)
            assert result.returncode != 0, f"Should fail for {invalid_type}"
            assert "Invalid bump type" in result.stdout


class TestVersionBumpIntegration:
    """Integration tests for version bumping scenarios."""

    @pytest.fixture
    def script_path(self):
        """Get path to bump-version.sh script."""
        return Path(__file__).parent.parent / "scripts" / "bump-version.sh"

    def run_script(self, script_path, current_version, bump_type):
        """Helper to run the bump-version.sh script."""
        result = subprocess.run(
            [str(script_path), current_version, bump_type],
            capture_output=True,
            text=True,
        )
        return result

    def test_sequential_patch_bumps(self, script_path):
        """Test multiple sequential patch bumps."""
        versions = ["v1.0.0", "v1.0.1", "v1.0.2", "v1.0.3"]

        for i in range(len(versions) - 1):
            result = self.run_script(script_path, versions[i], "patch")
            assert result.returncode == 0
            assert result.stdout.strip() == versions[i + 1]

    def test_mixed_bump_sequence(self, script_path):
        """Test realistic sequence of version bumps."""
        sequence = [
            ("v1.0.0", "minor", "v1.1.0"),
            ("v1.1.0", "patch", "v1.1.1"),
            ("v1.1.1", "patch", "v1.1.2"),
            ("v1.1.2", "minor", "v1.2.0"),
            ("v1.2.0", "major", "v2.0.0"),
        ]

        for current, bump_type, expected in sequence:
            result = self.run_script(script_path, current, bump_type)
            assert result.returncode == 0
            assert result.stdout.strip() == expected, (
                f"Failed at {current} + {bump_type}: "
                f"expected {expected}, got {result.stdout.strip()}"
            )

    def test_output_format_consistency(self, script_path):
        """Test that output format is consistent."""
        test_cases = [
            ("v1.2.3", "patch"),
            ("v0.0.1", "minor"),
            ("v10.20.30", "major"),
        ]

        for version, bump_type in test_cases:
            result = self.run_script(script_path, version, bump_type)
            assert result.returncode == 0

            # Check stdout has only the version (and newline)
            output_lines = result.stdout.strip().split("\n")
            assert len(output_lines) == 1, "Output should be single line"

            # Check version starts with 'v'
            assert output_lines[0].startswith("v"), "Version should start with 'v'"

            # Check version has exactly 3 parts
            version_parts = output_lines[0][1:].split(".")
            assert len(version_parts) == 3, "Version should have 3 parts"

            # Check all parts are numeric
            for part in version_parts:
                assert part.isdigit(), f"Version part {part} should be numeric"

    def test_stderr_logging(self, script_path):
        """Test that stderr contains logging information."""
        result = self.run_script(script_path, "v1.2.3", "patch")

        assert result.returncode == 0
        assert result.stderr != "", "stderr should contain logging"
        assert "Bumped" in result.stderr
        assert "v1.2.3" in result.stderr
        assert "v1.2.4" in result.stderr
        assert "patch" in result.stderr


class TestVersionBumpDocumentation:
    """Tests for script documentation and help."""

    @pytest.fixture
    def script_path(self):
        """Get path to bump-version.sh script."""
        return Path(__file__).parent.parent / "scripts" / "bump-version.sh"

    def test_script_has_usage_message(self, script_path):
        """Test that script provides usage information on error."""
        result = subprocess.run(
            [str(script_path)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Usage:" in result.stdout
        assert "bump-version.sh" in result.stdout

    def test_script_shows_valid_bump_types(self, script_path):
        """Test that error message shows valid bump types."""
        result = subprocess.run(
            [str(script_path), "v1.2.3", "invalid"],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Valid types:" in result.stdout or "major, minor, patch" in result.stdout

    def test_script_shows_example_format(self, script_path):
        """Test that usage message includes example."""
        result = subprocess.run(
            [str(script_path)],
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Example:" in result.stdout or "example" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
