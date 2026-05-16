// Overlord coordination policies — upload to AgentCore Policy Engine.
// context.input is populated by agentcore_policy.build_policy_context().

forbid(
  principal,
  action == AgentCore::Action::"Overlord___proposed_write",
  resource
)
when {
  context.input has action_type &&
  context.input.action_type == "delete_file" &&
  context.input has peer_recently_added_same_file &&
  context.input.peer_recently_added_same_file == true
};

forbid(
  principal,
  action == AgentCore::Action::"Overlord___proposed_write",
  resource
)
when {
  context.input has file_overlap &&
  context.input.file_overlap == true
};

forbid(
  principal,
  action == AgentCore::Action::"Overlord___proposed_write",
  resource
)
when {
  context.input has intent_contradiction &&
  context.input.intent_contradiction == true
};

permit(
  principal,
  action == AgentCore::Action::"Overlord___proposed_write",
  resource
);
