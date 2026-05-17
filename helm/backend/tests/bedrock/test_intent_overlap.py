from bedrock.intent_overlap import intent_overlap_score, intents_conflict


def test_disjoint_intents_score_zero():
    assert intent_overlap_score(
        "Billing invoices on app/billing/invoices.py",
        "JWT auth on app/auth/handlers.py",
    ) < 0.1


def test_same_file_similar_intents_score_high():
    score = intent_overlap_score(
        "Implement JWT login token issuance authentication API",
        "Build JWT sign-in session validation authentication API",
    )
    assert score >= 0.25


def test_contradiction_pair_detected():
    assert intents_conflict(
        "Optimize for maximum performance with caching",
        "Minimize dependencies and strip caching utilities",
    )
