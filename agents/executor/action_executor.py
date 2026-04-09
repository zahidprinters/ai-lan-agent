"""Safe tool execution adapter."""

from router.dispatch_core import dispatch_agent_action


def execute_action(payload: dict[str, object], confirmed: bool = False) -> dict[str, object]:
    return dispatch_agent_action(payload, confirmed=confirmed).to_dict()
