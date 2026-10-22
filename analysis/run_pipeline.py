"""Run the full, reproducible RainGuard pipeline in order.

    python analysis/run_pipeline.py            # uses cached geocodes / elevations if present
    python analysis/run_pipeline.py --fetch    # (re)download sources first

Network is only needed for fetch_data.py and for geocode/terrain cache misses.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [
    "verify_transcription.py",   # transcriptions vs source PDFs
    "digitize_ward_incidents.py",  # ward incident map -> ordinal classes (needs --full fetch)
    "geocode.py",                # Nominatim (cached) + precision / ward QC
    "clean_data.py",             # validate, de-duplicate, cross-source match
    "terrain.py",                # DEM elevation + TPI (cached)
    "rainfall.py",               # IMD + ERA5 summaries
    "rain_daily.py",             # IMD daily grids -> Mumbai series + checks (needs fetch_rain_daily.py)
    "features.py",               # ward and location features
    "evaluate.py",               # baselines vs models; terrain case-control
    "score.py",                  # prioritisation score + sensitivity
    "diagnose.py",               # rule-based labels per place (no weights)
    "allocate.py",               # K-place inspection plan with a ward cap + stability
    "predict.py",                # heavy-rain outlook: chronological test + forecast track record
    "eda.py",                    # findings + figures
    "export_app_data.py",        # JSON for the web app
]


def main() -> None:
    steps = [[s] for s in STEPS]
    if "--fetch" in sys.argv:
        steps[:0] = [["fetch_data.py", "--full"], ["fetch_rain_daily.py"]]
    for step in steps:
        print(f"\n=== {' '.join(step)} ===", flush=True)
        subprocess.run([sys.executable, str(HERE / step[0]), *step[1:]], check=True)
    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
