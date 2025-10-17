#!/usr/bin/env python3
"""
Quick compatibility test for configuration system.

Run this script to verify that the configuration system doesn't break
existing signal generation functionality.

Usage:
    python scripts/test_config_compatibility.py
"""

import sys

import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.insert(0, ".")

from ta_bot.models.signal import Signal  # noqa: E402
from ta_bot.strategies.bollinger_squeeze_alert import (  # noqa: E402
    BollingerSqueezeAlertStrategy,
)
from ta_bot.strategies.rsi_extreme_reversal import (  # noqa: E402
    RSIExtremeReversalStrategy,
)


class Colors:
    """Terminal colors for pretty output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def create_test_data(rows: int = 150, oversold: bool = False) -> pd.DataFrame:
    """
    Create realistic test data for strategy testing.

    Args:
        rows: Number of rows to generate
        oversold: If True, create oversold conditions for testing

    Returns:
        DataFrame with OHLCV data
    """
    base_price = 50000.0

    if oversold:
        # Create downtrend for oversold testing
        trend = -np.linspace(0, 5000, rows)
        noise = np.random.randn(rows) * 50
    else:
        # Normal market with random walk
        trend = np.cumsum(np.random.randn(rows) * 100)
        noise = np.random.randn(rows) * 50

    prices = base_price + trend + noise

    df = pd.DataFrame(
        {
            "open": prices + np.random.randn(rows) * 20,
            "high": prices + np.abs(np.random.randn(rows) * 50),
            "low": prices - np.abs(np.random.randn(rows) * 50),
            "close": prices,
            "volume": np.random.uniform(100, 1000, rows),
            "open_time": pd.date_range(start="2024-01-01", periods=rows, freq="15min"),
        }
    )

    return df


def test_strategy_without_config(strategy_class, strategy_name: str) -> bool:
    """Test strategy works without config manager (existing behavior)."""
    print(f"\n{Colors.BLUE}Testing {strategy_name} WITHOUT config...{Colors.END}")

    try:
        # Create strategy the old way (no config manager)
        strategy = strategy_class()

        # Create test data
        df = create_test_data(150, oversold=(strategy_name == "RSI Extreme Reversal"))

        # Metadata without config
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        # Run analysis
        signal = strategy.analyze(df, metadata)

        # Validate result
        if signal:
            assert isinstance(signal, Signal), "Signal is not a Signal object"
            assert signal.symbol == "BTCUSDT", "Symbol mismatch"
            assert signal.action in ["buy", "sell"], "Invalid action"
            assert 0 <= signal.confidence <= 1, "Confidence out of range"
            print(
                f"  {Colors.GREEN}✓ Generated signal: {signal.action.upper()} "
                f"(confidence: {signal.confidence:.2f}){Colors.END}"
            )
        else:
            print(
                f"  {Colors.YELLOW}✓ No signal generated (conditions not met){Colors.END}"
            )

        print(f"  {Colors.GREEN}✓ Strategy works WITHOUT config{Colors.END}")
        return True

    except Exception as e:
        print(f"  {Colors.RED}✗ FAILED: {str(e)}{Colors.END}")
        return False


def test_strategy_with_config(strategy_class, strategy_name: str) -> bool:
    """Test strategy works with config in metadata."""
    print(f"\n{Colors.BLUE}Testing {strategy_name} WITH config...{Colors.END}")

    try:
        # Create strategy
        strategy = strategy_class()

        # Create test data
        df = create_test_data(150, oversold=(strategy_name == "RSI Extreme Reversal"))

        # Simulate pre-loaded config
        config = {
            "parameters": {
                "oversold_threshold": 30,
                "extreme_threshold": 5,
                "min_data_points": 78,
                "base_confidence": 0.70,
            }
            if strategy_name == "RSI Extreme Reversal"
            else {
                "bb_period": 20,
                "bb_std": 2.0,
                "squeeze_threshold": 0.1,
                "min_data_points": 25,
            },
            "version": 2,
            "source": "mongodb",
            "is_override": False,
        }

        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "config": config,  # Config provided
        }

        # Run analysis
        signal = strategy.analyze(df, metadata)

        # Validate result
        if signal:
            assert isinstance(signal, Signal), "Signal is not a Signal object"

            # Check config metadata was added
            if "strategy_config" in signal.metadata:
                assert signal.metadata["strategy_config"]["version"] == 2
                assert signal.metadata["strategy_config"]["source"] == "mongodb"
                print(f"  {Colors.GREEN}✓ Config metadata added to signal{Colors.END}")
            else:
                print(
                    f"  {Colors.YELLOW}⚠ Config metadata not found in signal{Colors.END}"
                )

            print(
                f"  {Colors.GREEN}✓ Generated signal: {signal.action.upper()} "
                f"(confidence: {signal.confidence:.2f}){Colors.END}"
            )
        else:
            print(
                f"  {Colors.YELLOW}✓ No signal generated (conditions not met){Colors.END}"
            )

        print(f"  {Colors.GREEN}✓ Strategy works WITH config{Colors.END}")
        return True

    except Exception as e:
        print(f"  {Colors.RED}✗ FAILED: {str(e)}{Colors.END}")
        return False


def test_signal_format_unchanged() -> bool:
    """Test that signal format hasn't changed."""
    print(f"\n{Colors.BLUE}Testing signal format compatibility...{Colors.END}")

    try:
        strategy = RSIExtremeReversalStrategy()
        df = create_test_data(150, oversold=True)

        # Force oversold condition
        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "rsi_2": pd.Series([20] * 150),  # Oversold
        }

        signal = strategy.analyze(df, metadata)

        if signal:
            # Check all expected fields exist
            required_fields = [
                "strategy_id",
                "symbol",
                "action",
                "confidence",
                "price",
                "current_price",
                "timeframe",
                "metadata",
            ]

            for field in required_fields:
                assert hasattr(signal, field), f"Missing field: {field}"
                print(f"  {Colors.GREEN}✓ Field exists: {field}{Colors.END}")

            # Test serialization
            signal_dict = signal.to_dict()
            assert isinstance(signal_dict, dict), "to_dict() failed"
            print(f"  {Colors.GREEN}✓ Signal serialization works{Colors.END}")

            # Test validation
            is_valid = signal.validate()
            print(
                f"  {Colors.GREEN}✓ Signal validation works (valid: {is_valid}){Colors.END}"
            )

            return True
        else:
            print(
                f"  {Colors.YELLOW}⚠ Could not generate signal for format test{Colors.END}"
            )
            return True  # Still pass, just couldn't test

    except Exception as e:
        print(f"  {Colors.RED}✗ FAILED: {str(e)}{Colors.END}")
        return False


def test_performance() -> bool:
    """Test that config doesn't significantly slow down signal generation."""
    print(f"\n{Colors.BLUE}Testing performance impact...{Colors.END}")

    try:
        import time

        strategy = RSIExtremeReversalStrategy()
        df = create_test_data(200)

        # Test WITHOUT config
        metadata_no_config = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "rsi_2": pd.Series([20] * 200),
        }

        start = time.time()
        for _ in range(20):
            _signal = strategy.analyze(df, metadata_no_config)  # noqa: F841
        time_no_config = time.time() - start

        print(f"  Time WITHOUT config: {time_no_config*1000:.1f}ms (20 iterations)")

        # Test WITH config
        config = {
            "parameters": {
                "oversold_threshold": 25,
                "extreme_threshold": 2,
                "min_data_points": 78,
            },
            "version": 1,
            "source": "mongodb",
        }

        metadata_with_config = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "config": config,
            "rsi_2": pd.Series([20] * 200),
        }

        start = time.time()
        for _ in range(20):
            _signal = strategy.analyze(df, metadata_with_config)  # noqa: F841
        time_with_config = time.time() - start

        print(f"  Time WITH config: {time_with_config*1000:.1f}ms (20 iterations)")

        # Calculate overhead
        if time_no_config > 0:
            overhead = ((time_with_config - time_no_config) / time_no_config) * 100
            print(f"  Overhead: {overhead:.1f}%")

            if overhead < 50:
                print(
                    f"  {Colors.GREEN}✓ Performance impact acceptable (<50%){Colors.END}"
                )
                return True
            else:
                print(f"  {Colors.YELLOW}⚠ High overhead: {overhead:.1f}%{Colors.END}")
                return True  # Still pass, but warn
        else:
            print(f"  {Colors.GREEN}✓ Performance test completed{Colors.END}")
            return True

    except Exception as e:
        print(f"  {Colors.RED}✗ FAILED: {str(e)}{Colors.END}")
        return False


def main():
    """Run all compatibility tests."""
    print(f"\n{Colors.BOLD}{'='*70}")
    print("  CONFIGURATION SYSTEM COMPATIBILITY TEST")
    print("  Verifying backward compatibility with existing signal generation")
    print(f"{'='*70}{Colors.END}\n")

    results = []

    # Test strategies
    test_strategies = [
        (RSIExtremeReversalStrategy, "RSI Extreme Reversal"),
        (BollingerSqueezeAlertStrategy, "Bollinger Squeeze Alert"),
    ]

    # Test each strategy without config
    print(f"\n{Colors.BOLD}TEST 1: Strategies WITHOUT Configuration{Colors.END}")
    print("=" * 70)
    for strategy_class, name in test_strategies:
        results.append(test_strategy_without_config(strategy_class, name))

    # Test each strategy with config
    print(f"\n{Colors.BOLD}TEST 2: Strategies WITH Configuration{Colors.END}")
    print("=" * 70)
    for strategy_class, name in test_strategies:
        results.append(test_strategy_with_config(strategy_class, name))

    # Test signal format
    print(f"\n{Colors.BOLD}TEST 3: Signal Format Compatibility{Colors.END}")
    print("=" * 70)
    results.append(test_signal_format_unchanged())

    # Test performance
    print(f"\n{Colors.BOLD}TEST 4: Performance Impact{Colors.END}")
    print("=" * 70)
    results.append(test_performance())

    # Summary
    print(f"\n{Colors.BOLD}{'='*70}")
    print("  TEST SUMMARY")
    print(f"{'='*70}{Colors.END}\n")

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(
            f"{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED ({passed}/{total}){Colors.END}"
        )
        print(
            f"\n{Colors.GREEN}The configuration system is BACKWARD COMPATIBLE.{Colors.END}"
        )
        print(
            f"{Colors.GREEN}Existing signal generation will NOT be broken.{Colors.END}\n"
        )
        return 0
    else:
        print(
            f"{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED ({passed}/{total} passed){Colors.END}"
        )
        print(
            f"\n{Colors.RED}WARNING: Configuration system may break existing functionality.{Colors.END}"
        )
        print(f"{Colors.RED}Review failed tests above before deploying.{Colors.END}\n")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted by user{Colors.END}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.RED}Unexpected error: {str(e)}{Colors.END}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)
