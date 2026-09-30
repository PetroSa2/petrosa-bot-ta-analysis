import ast
from pathlib import Path

TA_BOT_ROOT = Path(__file__).parents[1] / "ta_bot"


def test_logger_messages_do_not_end_with_newline():
    violations = []
    for source_path in TA_BOT_ROOT.rglob("*.py"):
        tree = ast.parse(source_path.read_text(), filename=str(source_path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue
            if node.func.attr not in {
                "debug",
                "info",
                "warning",
                "error",
                "exception",
                "critical",
            }:
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            message = node.args[0].value
            if isinstance(message, str) and message.endswith("\n"):
                violations.append(f"{source_path}:{node.lineno}")

    assert violations == []
