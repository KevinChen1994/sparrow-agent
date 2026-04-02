from __future__ import annotations

from sparrow_agent.schemas.models import LoopState, LLMResponse


class HaltPolicy:
    def __init__(self, max_iterations: int = 40) -> None:
        self.max_iterations = max_iterations

    def should_stop(self, loop_state: LoopState, response: LLMResponse | None = None) -> tuple[bool, str | None]:
        if loop_state.stop_requested:
            return True, "stop requested"
        if loop_state.iteration >= self.max_iterations:
            return True, f"max iterations ({self.max_iterations}) reached"
        if response is not None and not response.has_tool_calls:
            return True, None
        return False, None
