"""Compatibility entry point: the coordinated AV planner now serves all eras."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('classic_alterac_objectives_regression.py')), run_name='__main__')
