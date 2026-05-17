from pathlib import Path

from agents.live_matrix.scenarios import assign_work, load_tasks
from agents.shopfix_scenarios import SCENARIO_DIR as SHOPFIX_SCENARIOS
from agents.streamcast_scenarios import SCENARIO_DIR as STREAMCAST_SCENARIOS


def test_shopfix_loads_ten_tasks():
    tasks = load_tasks(SHOPFIX_SCENARIOS)
    assert len(tasks) == 10


def test_disjoint_assignments_use_unique_hotspot_alts():
    tasks = load_tasks(SHOPFIX_SCENARIOS)
    work = assign_work(tasks, "disjoint", 2)
    assert len(work) == 10
    auth_paths = [w.primary_file for w in work if "auth" in w.primary_file]
    assert len(auth_paths) == len(set(auth_paths))


def test_contention_hotspot_shares_primary_file():
    tasks = load_tasks(STREAMCAST_SCENARIOS)
    work = assign_work(tasks, "contention", 2)
    hotspot = [w for w in work if w.task_id in {"t08", "t09", "t10"}]
    assert len(hotspot) >= 2
    assert len({w.primary_file for w in hotspot}) == 1


def test_round_robin_covers_all_tasks():
    tasks = load_tasks(SHOPFIX_SCENARIOS)
    work = assign_work(tasks, "disjoint", 4)
    assert {w.task_id for w in work} == {t.task_id for t in tasks}
