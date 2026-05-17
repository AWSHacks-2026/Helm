from pathlib import Path

from benchmarks.manifest import load_suite_manifest


def test_load_independent_suite(benchmarks_root: Path):
    manifest_path = benchmarks_root / "suites/independent/manifest.yaml"
    manifest = load_suite_manifest(manifest_path)
    assert manifest.suite == "independent"
    assert len(manifest.assignments) >= 3
    paths = [a.files[0] for a in manifest.assignments]
    assert len(paths) == len(set(paths))


def test_load_conflicting_suite_overlaps(benchmarks_root: Path):
    manifest_path = benchmarks_root / "suites/conflicting/manifest.yaml"
    manifest = load_suite_manifest(manifest_path)
    assert manifest.suite == "conflicting"
    files = [f for a in manifest.assignments for f in a.files]
    assert len(files) != len(set(files))
