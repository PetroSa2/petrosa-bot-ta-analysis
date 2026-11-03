from prometheus_client import REGISTRY

from ta_bot.health import (
    TARGETED_RUNTIME_WARNING,
    TARGETED_ZERO_DIVISION,
    record_targeted_exception,
    record_targeted_runtime_warning,
)


def _value(error_type: str) -> float:
    return (
        REGISTRY.get_sample_value(
            "ta_analysis_targeted_errors_total", {"error_type": error_type}
        )
        or 0.0
    )


def test_records_only_exact_scalar_divide_warning():
    before = _value(TARGETED_RUNTIME_WARNING)

    record_targeted_runtime_warning(
        RuntimeWarning("invalid value encountered in scalar divide")
    )
    record_targeted_runtime_warning(
        RuntimeWarning("invalid value encountered in divide")
    )

    assert _value(TARGETED_RUNTIME_WARNING) == before + 1


def test_records_zero_division_without_recording_other_exceptions():
    before = _value(TARGETED_ZERO_DIVISION)

    record_targeted_exception(ZeroDivisionError("division by zero"))
    record_targeted_exception(ValueError("configuration error"))

    assert _value(TARGETED_ZERO_DIVISION) == before + 1
