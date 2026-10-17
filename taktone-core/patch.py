"""Build taktone from supported stock or modified Digitakt firmware."""
from pathlib import Path
import runpy
import sys

if __name__ == '__main__':
    internal = Path(__file__).resolve().parent / 'internal'
    sys.path.insert(0, str(internal))
    if '--release' in sys.argv:
        sys.argv.remove('--release')
        target = 'patch.py'  # Historical pinned stock-1.53 TT1A release.
    else:
        target = 'convert.py'
    runpy.run_path(str(internal / target), run_name='__main__')
