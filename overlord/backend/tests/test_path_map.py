from integrations.path_map import resolve_file_path


def test_resolve_file_path_from_label():
    mapping = {"auth": "src/auth/"}
    assert resolve_file_path(components=[], labels=["auth"], mapping=mapping) == "src/auth/"


def test_resolve_file_path_prefers_body_path():
    mapping = {"auth": "src/auth/"}
    assert (
        resolve_file_path(
            components=[],
            labels=["auth"],
            mapping=mapping,
            description="Change src/user.py please",
        )
        == "src/user.py"
    )
