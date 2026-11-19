"""Run the Excel-to-JSON assessment workflow."""
import subprocess
import sys

from export_cases import export_cases
from build_report import ROOT


if __name__ == "__main__":
    export_cases()
    for script in ("build_report.py", "mutation_check.py"):
        subprocess.run([sys.executable, "-u", script], cwd=ROOT, check=True)
