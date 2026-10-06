"""Describe variation among the twelve successor wards across split scenarios."""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from sensitivity import MERGE, key


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wards-before", type=Path, default=Path("data/table13b_wards_before.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    before = pd.read_csv(args.wards_before)
    values = {key(r.Ward): (float(r.Pop_2025), float(r.area_km2)) for _, r in before.iterrows()}
    recipients: dict[str, list[str]] = {}
    for successor, former in MERGE.items():
        for old in former:
            recipients.setdefault(key(old.rstrip("*")), []).append(successor)
    if len(before) != 34 or set(values) != set(recipients):
        raise ValueError("Input must contain the 34 former wards in the legal crosswalk")
    splits = sorted(k for k, v in recipients.items() if len(v) == 2)
    records = []
    for shares in itertools.product((0, .25, .5, .75, 1), repeat=len(splits)):
        share = dict(zip(splits, shares))
        assigned = {name: [0., 0.] for name in MERGE}
        for old, dests in recipients.items():
            for i, dest in enumerate(dests):
                weight = 1 if len(dests) == 1 else (share[old] if i == 0 else 1-share[old])
                for m in (0, 1):
                    assigned[dest][m] += values[old][m] * weight
        scenario = ";".join(f"{k}={v:g}" for k, v in share.items())
        for ward, (population, area) in assigned.items():
            records.append({"scenario": scenario, "ward": ward, "population": population,
                            "area_km2": area, "density_per_km2": population / area})
    all_scenarios = pd.DataFrame(records)
    equal_key = ";".join(f"{k}=0.5" for k in splits)
    equal = all_scenarios[all_scenarios.scenario.eq(equal_key)].drop(columns="scenario").copy()
    equal["population"] = equal.population.round().astype(int)
    equal["area_km2"] = equal.area_km2.round(2)
    equal["density_per_km2"] = equal.density_per_km2.round().astype(int)
    equal["area_km2_per_10000_people"] = (10000 * equal.area_km2 / equal.population).round(2)
    equal.sort_values("ward").to_csv(args.output_dir / "ward_exposure_equal_share.csv", index=False)
    ranges = all_scenarios.groupby("ward").agg(pop_min=("population", "min"), pop_max=("population", "max"),
        area_min=("area_km2", "min"), area_max=("area_km2", "max"),
        density_min=("density_per_km2", "min"), density_max=("density_per_km2", "max")).round(2)
    ranges.to_csv(args.output_dir / "ward_exposure_ranges.csv")
    scenario_correlations = all_scenarios.groupby("scenario").apply(
        lambda frame: frame.population.corr(frame.area_km2, method="spearman"),
        include_groups=False)
    summary = {
        "scenarios": all_scenarios.scenario.nunique(),
        "mean_ratio_identity": 34 / 12,
        "population_min_max": [int(equal.population.min()), int(equal.population.max())],
        "area_min_max_km2": [float(equal.area_km2.min()), float(equal.area_km2.max())],
        "density_min_max_per_km2": [int(equal.density_per_km2.min()), int(equal.density_per_km2.max())],
        "population_cv": round(float(equal.population.std(ddof=0) / equal.population.mean()), 3),
        "area_cv": round(float(equal.area_km2.std(ddof=0) / equal.area_km2.mean()), 3),
        "population_area_spearman": round(float(equal.population.corr(equal.area_km2, method="spearman")), 3),
        "population_area_spearman_scenario_range": [round(float(scenario_correlations.min()), 3),
                                                     round(float(scenario_correlations.max()), 3)],
        "highest_population_ward": str(equal.loc[equal.population.idxmax(), "ward"]),
        "largest_area_ward": str(equal.loc[equal.area_km2.idxmax(), "ward"]),
        "lowest_density_ward": str(equal.loc[equal.density_per_km2.idxmin(), "ward"]),
        "highest_density_ward": str(equal.loc[equal.density_per_km2.idxmax(), "ward"]),
    }
    (args.output_dir / "ward_heterogeneity_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fig, ax = plt.subplots(figsize=(8.7, 6.2))
    ax.scatter(equal.area_km2, equal.population / 1000, s=70, color="#226184")
    for _, row in equal.iterrows():
        ax.annotate(row.ward, (row.area_km2, row.population / 1000), xytext=(4, 4),
                    textcoords="offset points", fontsize=9)
    ax.set(xlabel="Successor ward area (km²)", ylabel="Modelled population (thousands)",
           title="Successor wards differ in territorial and population exposure")
    ax.grid(alpha=.18)
    fig.tight_layout()
    for suffix in ("pdf", "png"):
        fig.savefig(args.output_dir / f"Figure5_successor_heterogeneity.{suffix}", dpi=240)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
