"""Single-flight generation lock and live progress stages."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from typing import Literal

Stage = Literal[
    "idle",
    "analyzing",
    "preparing",
    "redesigning",
    "refining",
    "ready",
    "failed",
    "busy",
]

STAGE_LABELS: dict[str, str] = {
    "idle": "Ready",
    "analyzing": "Analyzing your room",
    "preparing": "Preparing your design",
    "redesigning": "Redesigning the interior",
    "refining": "Refining your room",
    "ready": "Design ready",
    "failed": "Generation could not complete",
    "busy": "Another redesign is already in progress",
}

USER_RESOURCE_ERROR = (
    "Local generation couldn't complete with the available system resources."
)
USER_GENERIC_ERROR = "Local generation couldn't complete. Please retry."
USER_BUSY_ERROR = "Another redesign is already in progress. Please wait and retry."


@dataclass
class GenerationProgress:
    stage: Stage = "idle"
    label: str = STAGE_LABELS["idle"]
    busy: bool = False
    step: int | None = None
    total_steps: int | None = None
    started_at: float | None = None
    updated_at: float | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class GenerationGate:
    """Ensure only one local diffusion job runs at a time on this machine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._progress = GenerationProgress()
        self._progress_lock = threading.Lock()

    def try_begin(self) -> bool:
        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            self.set_stage("busy", error=USER_BUSY_ERROR)
            return False
        now = time.time()
        with self._progress_lock:
            self._progress = GenerationProgress(
                stage="analyzing",
                label=STAGE_LABELS["analyzing"],
                busy=True,
                started_at=now,
                updated_at=now,
            )
        return True

    def end(self, *, failed: bool = False, error: str | None = None) -> None:
        with self._progress_lock:
            now = time.time()
            if failed:
                self._progress.stage = "failed"
                self._progress.label = STAGE_LABELS["failed"]
                self._progress.error = error or USER_GENERIC_ERROR
            else:
                self._progress.stage = "ready"
                self._progress.label = STAGE_LABELS["ready"]
                self._progress.error = None
            self._progress.busy = False
            self._progress.updated_at = now
        if self._lock.locked():
            self._lock.release()

    def set_stage(
        self,
        stage: Stage,
        *,
        step: int | None = None,
        total_steps: int | None = None,
        error: str | None = None,
    ) -> None:
        with self._progress_lock:
            self._progress.stage = stage
            self._progress.label = STAGE_LABELS.get(stage, stage)
            self._progress.updated_at = time.time()
            if step is not None:
                self._progress.step = step
            if total_steps is not None:
                self._progress.total_steps = total_steps
            if error is not None:
                self._progress.error = error

    def snapshot(self) -> GenerationProgress:
        with self._progress_lock:
            return GenerationProgress(**asdict(self._progress))


generation_gate = GenerationGate()
