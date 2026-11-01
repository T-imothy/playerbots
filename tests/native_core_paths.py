"""Resolve native fixture checkouts without assuming a particular worktree name."""
from pathlib import Path
import os

def core_root(era):
    sibling=Path(__file__).resolve().parents[2]
    candidates=[]
    if os.environ.get('MANTECH_NATIVE_CORE_ROOT'):
        candidates.append(Path(os.environ['MANTECH_NATIVE_CORE_ROOT'])/era)
    candidates += [sibling/era,sibling/f'mangos-{era}-behavior']
    for candidate in candidates:
        if (candidate/'src/game/AI/ScriptDevAI/scripts').is_dir():
            return candidate
    raise RuntimeError(f'Native {era} fixtures unavailable; set MANTECH_NATIVE_CORE_ROOT to the parent of the core checkouts')
