"""Explicit source locations for read-only native regression tests.

PLAYERBOT_TEST_CORE_PATHS may name a JSON object mapping classic/tbc/wotlk
to checkout directories. This never substitutes one era's source for another.
"""
import json,os
from pathlib import Path

def core_eras(default=('classic','tbc','wotlk')):
    configured=os.environ.get('PLAYERBOT_TEST_NATIVE_ERAS')
    if not configured:return default
    selected=tuple(configured.split(','))
    if not selected or any(era not in ('classic','tbc','wotlk') for era in selected):
        raise ValueError('Invalid native regression era selection')
    return tuple(era for era in default if era in selected)

def core_path(era,default):
    config=os.environ.get('PLAYERBOT_TEST_CORE_PATHS')
    if not config:return Path(default)
    paths=json.loads(Path(config).read_text())
    root=Path(paths[era]).resolve()
    if not (root/'src/game/Entities/Creature.h').is_file():
        raise FileNotFoundError(f'{era} native source unavailable: {root}')
    return root
