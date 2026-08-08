from __future__ import annotations

from tenderpulse.worker import run_scheduled_loop


class StopAfterWait:
    def __init__(self) -> None:
        self.stopped = False
        self.waited_seconds: list[int] = []

    def is_set(self) -> bool:
        return self.stopped

    def wait(self, seconds: int) -> bool:
        self.waited_seconds.append(seconds)
        self.stopped = True
        return True


def test_enabled_worker_runs_cycle_immediately_then_waits() -> None:
    stopped = StopAfterWait()
    calls: list[str] = []

    run_scheduled_loop(
        enabled=True,
        interval_seconds=600,
        stopped=stopped,
        run_cycle=lambda: calls.append("cycle"),
    )

    assert calls == ["cycle"]
    assert stopped.waited_seconds == [600]


def test_disabled_worker_does_not_call_external_cycle() -> None:
    stopped = StopAfterWait()
    calls: list[str] = []

    run_scheduled_loop(
        enabled=False,
        interval_seconds=600,
        stopped=stopped,
        run_cycle=lambda: calls.append("cycle"),
    )

    assert calls == []
    assert stopped.waited_seconds == [600]
