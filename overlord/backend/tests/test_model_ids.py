from bedrock.model_ids import resolve_inference_profile_id


def test_prefixes_anthropic_foundation_id():
    assert (
        resolve_inference_profile_id("anthropic.claude-3-5-haiku-20241022-v1:0")
        == "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    )
    assert (
        resolve_inference_profile_id("anthropic.claude-sonnet-4-6")
        == "us.anthropic.claude-sonnet-4-6"
    )


def test_passes_through_inference_profile():
    assert (
        resolve_inference_profile_id("us.anthropic.claude-sonnet-4-20250514-v1:0")
        == "us.anthropic.claude-sonnet-4-20250514-v1:0"
    )


def test_passes_through_arn():
    arn = "arn:aws:bedrock:us-east-1:123:inference-profile/foo"
    assert resolve_inference_profile_id(arn) == arn
