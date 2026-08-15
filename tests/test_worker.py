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


class StopAfterTwoWaits:
    def __init__(self) -> None:
        self.wait_count = 0

    def is_set(self) -> bool:
        return self.wait_count >= 2

    def wait(self, seconds: int) -> bool:
        self.wait_count += 1
        return self.is_set()


def test_worker_records_cycle_error_and_continues_to_next_interval() -> None:
    stopped = StopAfterTwoWaits()
    attempts: list[int] = []
    errors: list[Exception] = []

    def cycle() -> None:
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            raise RuntimeError("parser failed")

    run_scheduled_loop(
        enabled=True,
        interval_seconds=60,
        stopped=stopped,
        run_cycle=cycle,
        on_cycle_error=errors.append,
    )

    assert attempts == [1, 2]
    assert [str(error) for error in errors] == ["parser failed"]
