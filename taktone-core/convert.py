"""Compatibility alias for patch.py: stock/modified Digitakt 1.53 and 1.54."""
from pathlib import Path
import runpy
import sys

if __name__ == '__main__':
    internal = Path(__file__).resolve().parent / 'internal'
    sys.path.insert(0, str(internal))
    runpy.run_path(str(internal / 'convert.py'), run_name='__main__')
