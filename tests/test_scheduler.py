from datetime import date

import pytest

from construction_ai.scheduler import ScheduleError, Task, build_schedule, default_residential_tasks, project_finish


def test_sequence_and_critical_path():
    tasks = [Task("A", "a", 2), Task("B", "b", 3, ("A",)), Task("C", "c", 1, ("A",)), Task("D", "d", 2, ("B", "C"))]
    s = {t.id: t for t in build_schedule(tasks, date(2026, 1, 5), weekend_days=())}  # Monday
    assert s["A"].start == date(2026, 1, 5) and s["A"].end == date(2026, 1, 6)
    assert s["B"].start == date(2026, 1, 7)
    assert s["D"].start == date(2026, 1, 10)
    assert s["B"].critical and not s["C"].critical and s["C"].slack_days == 2


def test_sunday_is_skipped():
    s = build_schedule([Task("A", "a", 7)], date(2026, 1, 5))  # Mon..Sat + Mon
    assert s[0].end == date(2026, 1, 12)


def test_blocked_dates_delay_finish():
    t = [Task("A", "a", 3)]
    normal = project_finish(build_schedule(t, date(2026, 1, 5), weekend_days=()))
    delayed = project_finish(build_schedule(t, date(2026, 1, 5), weekend_days=(), blocked_dates=[date(2026, 1, 6)]))
    assert delayed > normal


def test_cycle_unknown_dep_and_bad_duration():
    with pytest.raises(ScheduleError):
        build_schedule([Task("A", "a", 1, ("B",)), Task("B", "b", 1, ("A",))], date(2026, 1, 5))
    with pytest.raises(ScheduleError):
        build_schedule([Task("A", "a", 1, ("Z",))], date(2026, 1, 5))
    with pytest.raises(ScheduleError):
        build_schedule([Task("A", "a", 0)], date(2026, 1, 5))


def test_default_template_is_valid():
    s = build_schedule(default_residential_tasks(), date(2026, 1, 5))
    assert any(x.critical for x in s) and project_finish(s) > date(2026, 1, 5)
