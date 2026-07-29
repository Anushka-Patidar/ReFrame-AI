"""Single-flight generation lock and live progress stages."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass
from typing import Literal

logger = logging.getLogger(__name__)

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
    "preparing": "Preserving room structure",
    "redesigning": "Applying your design direction",
    "refining": "Finalizing your room",
    "ready": "Design ready",
    "failed": "Generation could not complete",
    "busy": "Another redesign is already in progress",
}

USER_RESOURCE_ERROR = (
    "Local generation couldn't complete with the available system resources."
)
USER_GENERIC_ERROR = "Local generation couldn't complete. Please retry."
USER_BUSY_ERROR = "Another redesign is already in progress. Please wait and retry."
USER_TIMEOUT_ERROR = (
    "Local generation took too long and was stopped. Please retry with Quick Preview or Balanced."
)

# Hard ceilings so a hung CPU job cannot block the product forever.
MAX_GENERATION_SECONDS = 12 * 60
# First ControlNet step on CPU can be slow; allow several minutes before declaring idle.
MAX_IDLE_PROGRESS_SECONDS = 8 * 60


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
    job_id: int | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        # Keep product UI free of internal job ids.
        payload.pop("job_id", None)
        return payload


class GenerationGate:
    """Ensure only one local diffusion job runs at a time on this machine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._progress = GenerationProgress()
        self._progress_lock = threading.Lock()
        self._active_job_id: int | None = None
        self._next_job_id = 1

    def try_begin(self) -> int | None:
        self.recover_if_stale()
        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            self.set_stage("busy", error=USER_BUSY_ERROR)
            return None
        now = time.time()
        with self._progress_lock:
            job_id = self._next_job_id
            self._next_job_id += 1
            self._active_job_id = job_id
            self._progress = GenerationProgress(
                stage="analyzing",
                label=STAGE_LABELS["analyzing"],
                busy=True,
                started_at=now,
                updated_at=now,
                job_id=job_id,
            )
        return job_id

    def end(
        self,
        job_id: int | None = None,
        *,
        failed: bool = False,
        error: str | None = None,
    ) -> None:
        with self._progress_lock:
            if job_id is not None and self._active_job_id is not None and job_id != self._active_job_id:
                # A previous timed-out / force-reset job finished late — ignore.
                logger.info("Ignoring stale generation end for job_id=%s", job_id)
                return
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
            self._progress.job_id = None
            self._active_job_id = None
        if self._lock.locked():
            try:
                self._lock.release()
            except RuntimeError:
                pass

    def force_reset(self, *, error: str | None = None) -> None:
        """Release a stuck generation lock so the user can retry."""
        message = error or USER_TIMEOUT_ERROR
        logger.warning("Force-resetting generation gate: %s", message)
        with self._progress_lock:
            now = time.time()
            self._progress = GenerationProgress(
                stage="failed",
                label=STAGE_LABELS["failed"],
                busy=False,
                started_at=self._progress.started_at,
                updated_at=now,
                error=message,
                job_id=None,
            )
            self._active_job_id = None
        if self._lock.locked():
            try:
                self._lock.release()
            except RuntimeError:
                pass

    def set_stage(
        self,
        stage: Stage,
        *,
        step: int | None = None,
        total_steps: int | None = None,
        error: str | None = None,
        job_id: int | None = None,
    ) -> None:
        with self._progress_lock:
            if job_id is not None and self._active_job_id is not None and job_id != self._active_job_id:
                return
            # Ignore progress updates from a hung worker after force-reset.
            if stage in {"analyzing", "preparing", "redesigning", "refining"}:
                if not self._progress.busy or self._active_job_id is None:
                    return
            self._progress.stage = stage
            self._progress.label = STAGE_LABELS.get(stage, stage)
            self._progress.updated_at = time.time()
            if step is not None:
                self._progress.step = step
            if total_steps is not None:
                self._progress.total_steps = total_steps
            if error is not None:
                self._progress.error = error

    def recover_if_stale(self) -> bool:
        """Auto-clear hung jobs that never finished or never advanced."""
        with self._progress_lock:
            if not self._progress.busy:
                return False
            now = time.time()
            started = self._progress.started_at or now
            updated = self._progress.updated_at or started
            age = now - started
            idle = now - updated
            stale = age >= MAX_GENERATION_SECONDS or idle >= MAX_IDLE_PROGRESS_SECONDS
            if not stale:
                return False
        self.force_reset(
            error=(
                "A previous redesign was stuck and has been cleared. "
                "Please retry generation."
            )
        )
        return True

    def snapshot(self) -> GenerationProgress:
        self.recover_if_stale()
        with self._progress_lock:
            return GenerationProgress(**asdict(self._progress))


generation_gate = GenerationGate()
