"""Run exact research checks using Python 3.10+ and its standard library."""
from pathlib import Path
import argparse
import os
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--quick", action="store_true", help="Skip the full censuses and half-parabola checks")
args = parser.parse_args()
if not __debug__:
    raise SystemExit("Run without -O: these verification scripts use assertions.")
root = Path(__file__).resolve().parent
scripts = [
    "quadratic_modular_barrier.py",
    "independent_geometry.py",
    "verify_lookahead.py",
    "independent_lookahead.py",
    "abstract_relocation_bound.py",
    "equal_pass_mex.py",
    "early_stop_passes.py",
]
if not args.quick:
    scripts += [
        "parabola_half_bound.py",
        "independent_parabola.py",
        "ambiguity_classes.py",
        "verify_relocation.py",
    ]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
for script in scripts:
    print(f"Running {script}", flush=True)
    subprocess.run([sys.executable, "-B", str(root / script)], cwd=root, env=env, check=True)
print("All exact checks passed.", flush=True)
