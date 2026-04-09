"""Goal lifecycle placeholder."""


class GoalManager:
    def __init__(self) -> None:
        self._goals: list[str] = []

    def add(self, goal: str) -> None:
        self._goals.append(goal)
