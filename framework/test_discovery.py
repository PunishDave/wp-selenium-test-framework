from pathlib import Path

def discover_tests(tests_dir: Path) -> list[str]:
    tests_dir = tests_dir.resolve()
    if not tests_dir.exists():
        return []

    files = sorted(tests_dir.rglob("test_*.py"))
    # Return node-ish targets pytest can run, relative to repo root
    repo_root = tests_dir.parent
    return [str(f.relative_to(repo_root)) for f in files]

