"""bot-ta-analysis subsystem evaluator (P2.7, petrosa_k8s#697 AC4 / #248).

Adopts the shared `petrosa_otel.evaluators` framework (P2.1) so bot-ta-analysis
publishes a structured health verdict on ``evaluator.bot-ta-analysis.verdict``,
closing one of the five "silent service" gaps that keep FR17 / FR23 / FR32 at
YELLOW.
"""

from ta_bot.evaluators.health_evaluator import (
    BotTaAnalysisHealthEvaluator,
    build_bot_ta_analysis_health_evaluator,
)

__all__ = [
    "BotTaAnalysisHealthEvaluator",
    "build_bot_ta_analysis_health_evaluator",
]
