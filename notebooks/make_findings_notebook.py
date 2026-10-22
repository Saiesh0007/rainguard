"""Build and execute notebooks/01_findings.ipynb: the EDA and evaluation, readable top to bottom.

    pip install nbformat nbclient ipykernel     # notebook-only extras, not needed for the pipeline
    python notebooks/make_findings_notebook.py

The notebook only READS data/processed/ (written by analysis/run_pipeline.py); it computes nothing new,
so its numbers are the same ones the app and docs/ show.
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent

CELLS: list[tuple[str, str]] = [
    ("md", """# RainGuard: findings and evaluation

Every number here is read from `data/processed/`, produced by `python analysis/run_pipeline.py`.
Rebuild this notebook with `python notebooks/make_findings_notebook.py`.

Evidence kinds follow the app: **observed** (IMD rain), **historical** (official 2026 lists, BMC ward map),
**estimated** (models, geocodes, terrain), **forecast** (third-party)."""),
    ("code", """import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

PROC = Path.cwd().parent / "data" / "processed"
findings = {f["id"]: f for f in json.loads((PROC / "eda_findings.json").read_text(encoding="utf8"))}
wards = pd.read_csv(PROC / "ward_stats.csv")
evaluation = json.loads((PROC / "evaluation.json").read_text())
outlook = json.loads((PROC / "outlook.json").read_text())
allocation = json.loads((PROC / "allocation.json").read_text())
sens = json.loads((PROC / "score_sensitivity.json").read_text())
for f in findings.values():
    print(f"{f['id']}: {f['title']}")"""),
    ("md", """## F1: recorded ward incidents mostly follow population

Finding → evidence → so what: the incident map is a reporting/exposure signal, so the app labels it
"mostly follows population" and offers a population-adjusted alternative in the score."""),
    ("code", """fig, ax = plt.subplots(figsize=(6, 4))
ax.scatter(wards.population_2011 / 1e5, wards.incident_class, color="#2a78d6")
for r in wards.itertuples():
    ax.annotate(r.ward, (r.population_2011 / 1e5, r.incident_class), fontsize=8, xytext=(3, 2), textcoords="offset points")
ax.set_xlabel("Population 2011 (lakh)"); ax.set_ylabel("Incident class (1-7)")
rho = evaluation["ward_level"]["spearman_population_vs_class"]["rho"]
ax.set_title(f"Ward incident class vs population (Spearman rho = {rho})", loc="left", fontsize=10)
plt.show()
pd.DataFrame(evaluation["ward_level"]["models"]).T[["loo_mae_classes", "loo_spearman", "permutation_p_value"]]"""),
    ("md", """## F2: the three official lists barely overlap

So what: disagreement between agencies is itself an action item (the `list_gap` label)."""),
    ("code", """pd.Series(findings["F2"]["numbers"]["by_source_combination"]).sort_values(ascending=False).to_frame("places")"""),
    ("md", "## F3: the monsoon concentrates the rain"),
    ("code", """clim = pd.read_csv(PROC / "rainfall_monthly_climatology.csv")
ax = clim.plot.bar(x="month", y="mean", legend=False, color="#2a78d6", figsize=(6, 3))
ax.set_ylabel("mm"); ax.set_title("Mean monthly rain, IMD 1901-2021", loc="left", fontsize=10); plt.show()"""),
    ("md", """## F4: terrain shows no significant signal (a null result)

So what: terrain weight is 0 by default."""),
    ("code", """pd.DataFrame({k: {"n": v["n"], **v["tpi_pct_in_ward"]} for k, v in evaluation["location_terrain_case_control"].items()}).T"""),
    ("md", "## F5: pump coverage of BMC-listed spots"),
    ("code", """findings["F5"]["numbers"]"""),
    ("md", """## F6 and the heavy-rain outlook: chronological test

Target: tomorrow is a heavy-rain day (IMD >= 64.5 mm in either Mumbai cell). Trained on early years,
chosen on a validation block, tested once on the latest years. This is a rain outlook, not a
waterlogging forecast."""),
    ("code", """om = outlook["observed_model"]
print("split:", om["split_years"], "chosen:", om["chosen_on_validation"])
pd.DataFrame(om["test"]).T"""),
    ("code", """rel = pd.DataFrame(om["test_reliability_chosen"])
fig, ax = plt.subplots(figsize=(4.5, 4.5))
ax.plot([0, 1], [0, 1], ls="--", color="#8a8984")
ax.scatter(rel.mean_predicted, rel.observed_share, s=rel.n / rel.n.max() * 300, color="#2a78d6")
ax.set_xlabel("Mean predicted chance"); ax.set_ylabel("Observed heavy share")
ax.set_title("Reliability on test years (dot size = days)", loc="left", fontsize=10); plt.show()
rel"""),
    ("code", """fc = outlook["forecast_track_record"]
print(fc["period"], "|", fc["forecast_ge_64_5mm"])
pd.DataFrame(fc["by_forecast_amount"])"""),
    ("md", """## Inspection plan: how stable is it?

The plan's membership depends on value judgements (weights). The diagnosis labels do not."""),
    ("code", """print("score top-20 Jaccard vs random weights:", sens["top20_jaccard_default_vs_random_weights"])
print("population-adjusted alternative:", {k: v for k, v in sens["population_adjusted_alternative"].items() if k != "weights"})
print({k: allocation[k] for k in ("k", "cap_per_ward", "wards_in_default_plan", "wards_in_uncapped_top_k", "plan_jaccard_vs_default")})
print("stable core:", allocation["stable_core"])"""),
]


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src) for kind, src in CELLS]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    NotebookClient(nb, timeout=120, kernel_name="python3", resources={"metadata": {"path": str(HERE)}}).execute()
    out = HERE / "01_findings.ipynb"
    nbf.write(nb, out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
