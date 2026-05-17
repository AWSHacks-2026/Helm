from agents.shopfix_scenarios import load_assignments


def test_disjoint_n4_has_four_unique_files():
    assignments = load_assignments("disjoint", agent_count=4)
    assert len(assignments) == 4
    paths = [a.primary_file for a in assignments]
    assert len(set(paths)) == 4


def test_contention_n2_same_auth_file():
    assignments = load_assignments("contention", agent_count=2)
    assert len(assignments) == 2
    assert assignments[0].primary_file == assignments[1].primary_file
