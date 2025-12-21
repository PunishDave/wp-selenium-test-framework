import os
import subprocess
from pathlib import Path
from typing import Iterable

def run_pytest(
    repo_root: Path,
    targets: Iterable[str],
    env_overrides: dict[str, str] | None = None,
) -> tuple[int, str]:
    repo_root = repo_root.resolve()
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    cmd = ["pytest", "-q", *targets]
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output

