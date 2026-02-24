"""
Tests for collect-baseline-metrics.sh script.

This script requires Prometheus access and Kubernetes cluster connectivity,
so tests focus on script structure, syntax validation, and function definitions
rather than end-to-end execution.
"""

import stat
import subprocess
from pathlib import Path

import pytest


class TestCollectBaselineMetricsScript:
    """Tests for collect-baseline-metrics.sh script."""

    @pytest.fixture
    def script_path(self):
        """Get path to collect-baseline-metrics.sh script."""
        return Path(__file__).parent.parent / "scripts" / "collect-baseline-metrics.sh"

    def test_script_exists(self, script_path):
        """Test that collect-baseline-metrics.sh script exists."""
        assert script_path.exists(), f"Script not found at {script_path}"
        assert script_path.is_file(), "Script path is not a file"

    def test_script_is_executable(self, script_path):
        """Test that script has executable permissions."""
        st = script_path.stat()
        assert st.st_mode & stat.S_IXUSR, "Script is not executable"

    def test_script_syntax_is_valid(self, script_path):
        """Test that script has valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Script syntax error: {result.stderr}"

    def test_script_has_shebang(self, script_path):
        """Test that script starts with shebang."""
        with open(script_path) as f:
            first_line = f.readline()
        assert first_line.startswith("#!/bin/bash"), (
            "Script should start with #!/bin/bash"
        )

    def test_script_has_required_functions(self, script_path):
        """Test that script defines required functions."""
        with open(script_path) as f:
            content = f.read()

        # Check for key functions
        assert "url_encode()" in content, "Script should define url_encode() function"
        assert "query_prometheus()" in content, (
            "Script should define query_prometheus() function"
        )
        assert "query_sum()" in content, "Script should define query_sum() function"

    def test_script_handles_division_by_zero(self, script_path):
        """Test that script includes division by zero checks."""
        with open(script_path) as f:
            content = f.read()

        # Check for division by zero protection
        assert 'TOTAL_24H != "0"' in content or 'TOTAL_24H" != "0' in content, (
            "Script should check for zero before division"
        )

    def test_script_has_url_encoding(self, script_path):
        """Test that script includes URL encoding for Prometheus queries."""
        with open(script_path) as f:
            content = f.read()

        # Check for URL encoding function
        assert "url_encode" in content, "Script should use URL encoding for queries"
        assert "urllib.parse.quote" in content or "url_encode" in content, (
            "Script should encode query strings"
        )

    def test_script_has_error_handling(self, script_path):
        """Test that script includes error handling."""
        with open(script_path) as f:
            content = f.read()

        # Check for error handling patterns
        assert "set -e" in content or "set -o errexit" in content, (
            "Script should exit on error"
        )
        assert "|| echo" in content or "|| true" in content, (
            "Script should handle command failures gracefully"
        )

    def test_script_outputs_to_file(self, script_path):
        """Test that script writes output to a file."""
        with open(script_path) as f:
            content = f.read()

        # Check for output file redirection
        assert '>> "$OUTPUT_FILE"' in content or '> "$OUTPUT_FILE"' in content, (
            "Script should write output to file"
        )

    def test_script_checks_prometheus_availability(self, script_path):
        """Test that script checks for Prometheus availability."""
        with open(script_path) as f:
            content = f.read()

        # Check for Prometheus pod check
        assert "PROMETHEUS_POD" in content, "Script should check for Prometheus pod"
        assert "kubectl get pods" in content or "monitoring" in content, (
            "Script should verify Prometheus is available"
        )


class TestCollectBaselineMetricsScriptDocumentation:
    """Tests for script documentation and usage."""

    @pytest.fixture
    def script_path(self):
        """Get path to collect-baseline-metrics.sh script."""
        return Path(__file__).parent.parent / "scripts" / "collect-baseline-metrics.sh"

    def test_script_has_usage_comments(self, script_path):
        """Test that script includes usage documentation."""
        with open(script_path) as f:
            content = f.read()

        # Check for documentation comments
        assert "Purpose:" in content or "Usage:" in content, (
            "Script should include usage documentation"
        )

    def test_script_describes_output_format(self, script_path):
        """Test that script describes output format."""
        with open(script_path) as f:
            content = f.read()

        # Check for output description
        assert "OUTPUT_FILE" in content or "baseline" in content.lower(), (
            "Script should describe output format"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
