import pytest
from unittest.mock import MagicMock
from agents.react.controller import NeuralActionController, PlannedTurn


def test_multi_step_reasoning():
    controller = NeuralActionController()
    # Mock the internal plan to return an action then a reply
    controller.plan = MagicMock(
        side_effect=[
            PlannedTurn(
                mode="action",
                source="model",
                action_payload={
                    "thought": "Search",
                    "action": "web.search",
                    "args": {"query": "test"},
                    "safety_level": "low",
                },
            ),
            PlannedTurn(mode="reply", source="model", reply_text="Found it."),
        ]
    )

    # We expect plan_iterative to exist and return a list of PlannedTurn
    result = controller.plan_iterative(message="test", max_steps=2)
    assert len(result) == 2
    assert result[0].mode == "action"
    assert result[1].mode == "reply"
    assert result[1].reply_text == "Found it."
