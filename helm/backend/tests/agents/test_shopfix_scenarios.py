from agents.shopfix_scenarios import load_assignments, load_work_assignments


def test_disjoint_n4_has_four_unique_files():
    work = load_work_assignments("disjoint", agent_count=4)
    first_per_agent = {}
    for item in work:
        if item.agent_id not in first_per_agent:
            first_per_agent[item.agent_id] = item.primary_file
    paths = list(first_per_agent.values())
    assert len(paths) == 4
    assert len(set(paths)) == 4


def test_contention_n2_hotspot_tasks_share_auth_file():
    work = load_work_assignments("contention", agent_count=2)
    hotspot = [w for w in work if w.task_id in {"t08", "t09", "t10"}]
    assert len(hotspot) >= 2
    assert hotspot[0].primary_file == hotspot[1].primary_file
    assert "auth" in hotspot[0].primary_file


def test_load_assignments_returns_one_per_agent():
    assignments = load_assignments("contention", agent_count=2)
    assert len(assignments) == 2
