"""Milestone 3 / Activity 3.3: Task scheduling with dependencies and critical path."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable


@dataclass(frozen=True)
class Task:
    id: str
    name: str
    duration_days: int
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScheduledTask:
    id: str
    name: str
    duration_days: int
    start: date
    end: date
    slack_days: int
    critical: bool
    depends_on: tuple[str, ...] = field(default_factory=tuple)


class ScheduleError(ValueError):
    pass


def default_residential_tasks() -> list[Task]:
    return [
        Task("T1", "Site clearing & layout marking", 4),
        Task("T2", "Excavation", 6, ("T1",)),
        Task("T3", "Footing & foundation", 14, ("T2",)),
        Task("T4", "Plinth beam & backfilling", 10, ("T3",)),
        Task("T5", "Columns & slab (ground floor)", 21, ("T4",)),
        Task("T6", "Brickwork & masonry", 18, ("T5",)),
        Task("T7", "Electrical & plumbing rough-in", 12, ("T6",)),
        Task("T8", "Plastering", 15, ("T7",)),
        Task("T9", "Flooring & tiling", 14, ("T8",)),
        Task("T10", "Doors, windows & carpentry", 10, ("T8",)),
        Task("T11", "Painting & finishing", 12, ("T9", "T10")),
        Task("T12", "Final inspection & handover", 3, ("T11",)),
    ]


def _calendar(start: date, weekend_days: set[int], blocked: set[date]):
    """Yield working dates beginning on/after `start`."""
    d = start
    while True:
        if d.weekday() not in weekend_days and d not in blocked:
            yield d
        d += timedelta(days=1)


def build_schedule(
    tasks: Iterable[Task],
    start: date,
    weekend_days: Iterable[int] = (6,),          # Sunday off (Mon=0 ... Sun=6)
    blocked_dates: Iterable[date] = (),          # holidays / rain days
) -> list[ScheduledTask]:
    tasks = list(tasks)
    by_id = {t.id: t for t in tasks}
    if len(by_id) != len(tasks):
        raise ScheduleError("Duplicate task ids.")
    for t in tasks:
        if t.duration_days < 1:
            raise ScheduleError(f"Task {t.id}: duration must be at least 1 day.")
        for dep in t.depends_on:
            if dep not in by_id:
                raise ScheduleError(f"Task {t.id} depends on unknown task '{dep}'.")
            if dep == t.id:
                raise ScheduleError(f"Task {t.id} cannot depend on itself.")

    # topological order (Kahn) - also detects cycles
    indeg = {t.id: len(t.depends_on) for t in tasks}
    succ: dict[str, list[str]] = {t.id: [] for t in tasks}
    for t in tasks:
        for dep in t.depends_on:
            succ[dep].append(t.id)
    queue = [i for i, n in indeg.items() if n == 0]
    order: list[str] = []
    while queue:
        cur = queue.pop(0)
        order.append(cur)
        for nxt in succ[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(tasks):
        raise ScheduleError("Circular dependency detected between tasks.")

    # forward pass on working-day indices (finish index inclusive)
    es: dict[str, int] = {}
    ef: dict[str, int] = {}
    for tid in order:
        t = by_id[tid]
        es[tid] = max((ef[d] + 1 for d in t.depends_on), default=0)
        ef[tid] = es[tid] + t.duration_days - 1
    project_end = max(ef.values())

    # backward pass
    lf: dict[str, int] = {}
    ls: dict[str, int] = {}
    for tid in reversed(order):
        t = by_id[tid]
        lf[tid] = min((ls[s] - 1 for s in succ[tid]), default=project_end)
        ls[tid] = lf[tid] - t.duration_days + 1

    # map working-day index -> calendar date
    cal = _calendar(start, set(weekend_days), set(blocked_dates))
    dates = [next(cal) for _ in range(project_end + 1)]

    return [
        ScheduledTask(
            id=t.id, name=t.name, duration_days=t.duration_days,
            start=dates[es[t.id]], end=dates[ef[t.id]],
            slack_days=ls[t.id] - es[t.id], critical=ls[t.id] == es[t.id],
            depends_on=t.depends_on,
        )
        for t in tasks
    ]


def project_finish(schedule: list[ScheduledTask]) -> date:
    return max(s.end for s in schedule)
