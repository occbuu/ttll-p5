"""Recalculate ward-exposure ranges under unknown split-ward shares.

Inputs are the existing aggregate tables. Four former wards appear in two
successor wards each. Their actual split geometry is unavailable; the sweep
uses shares 0, .25, .5, .75 and 1, with complements assigned to the other
successor. These are allocation scenarios, not confidence intervals.
"""
from __future__ import annotations

import itertools
import json
import unicodedata
import argparse
from pathlib import Path

import pandas as pd

MERGE = {
    "Hiep Binh": ["Hiệp Bình Chánh", "Hiệp Bình Phước", "Linh Đông*"],
    "Thu Duc": ["Bình Thọ", "Linh Chiểu", "Trường Thọ", "Linh Tây*", "Linh Đông*"],
    "Tam Binh": ["Bình Chiểu", "Tam Phú", "Tam Bình"],
    "Linh Xuan": ["Linh Trung", "Linh Xuân", "Linh Tây*"],
    "Tang Nhon Phu": ["Tân Phú", "Hiệp Phú", "Tăng Nhơn Phú A", "Tăng Nhơn Phú B", "Long Thạnh Mỹ*"],
    "Long Binh": ["Long Bình", "Long Thạnh Mỹ*"],
    "Long Phuoc": ["Trường Thạnh", "Long Phước"],
    "Long Truong": ["Phú Hữu", "Long Trường"],
    "Cat Lai": ["Thạnh Mỹ Lợi", "Cát Lái"],
    "Binh Trung": ["Bình Trưng Đông", "Bình Trưng Tây", "An Phú*"],
    "Phuoc Long": ["Phước Bình", "Phước Long A", "Phước Long B"],
    "An Khanh": ["Thủ Thiêm", "An Lợi Đông", "Thảo Điền", "An Khánh", "An Phú*"],
}


def key(value: str) -> str:
    value = unicodedata.normalize("NFD", str(value).lower())
    return "".join(c for c in value if unicodedata.category(c) != "Mn").replace("đ", "d").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wards-before", type=Path, required=True, help="34 former-ward population and area aggregates")
    parser.add_argument("--osm-counts", type=Path, required=True, help="Former-ward OSM category counts by snapshot")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    before = pd.read_csv(args.wards_before)
    osm = pd.read_csv(args.osm_counts)
    if not {"Ward", "Pop_2025", "area_km2"}.issubset(before.columns):
        raise ValueError("wards-before requires Ward, Pop_2025, area_km2 columns")
    if not {"date", "ward", "metric", "value"}.issubset(osm.columns):
        raise ValueError("osm-counts requires date, ward, metric, value columns")
    if before.Ward.map(key).duplicated().any() or len(before) != 34:
        raise ValueError("wards-before must contain 34 unique former wards")
    if (before[["Pop_2025", "area_km2"]].isna().any().any() or
            (before[["Pop_2025", "area_km2"]] < 0).any().any()):
        raise ValueError("Population and area must be nonnegative and complete")
    if osm.empty or osm.value.isna().any() or (osm.value < 0).any():
        raise ValueError("OSM counts must be nonempty and nonnegative")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    latest = osm[osm.date == osm.date.max()].pivot_table(index="ward", columns="metric", values="value", aggfunc="sum").fillna(0)
    values = {}
    for _, row in before.iterrows():
        values[key(row.Ward)] = {"population": float(row.Pop_2025), "area_km2": float(row.area_km2)}
    for ward, row in latest.iterrows():
        if key(ward) not in values:
            raise ValueError(f"OSM ward not found in wards-before: {ward}")
        values[key(ward)].update({str(k): float(v) for k, v in row.items()})
    recipients = {}
    for successor, olds in MERGE.items():
        for old in olds:
            recipients.setdefault(key(old.rstrip("*")), []).append(successor)
    if set(recipients) != set(values):
        raise ValueError("Former-ward names do not match the 2025 legal allocation")
    splits = sorted(k for k, v in recipients.items() if len(v) == 2)
    assert len(splits) == 4
    metrics = ["population", "area_km2", "shop", "food_outlet", "religious_premises", "education", "health", "public_space", "marketplace", "road_km"]
    old_medians = {m: float(pd.Series([v.get(m, 0) for v in values.values()]).median()) for m in metrics}
    if any(v <= 0 for v in old_medians.values()):
        raise ValueError("At least one old-ward median is zero; ratio undefined")
    scenarios = []
    for shares in itertools.product((0, .25, .5, .75, 1), repeat=4):
        allocation = dict(zip(splits, shares))
        new = {n: {m: 0.0 for m in metrics} for n in MERGE}
        for old, dests in recipients.items():
            for i, dest in enumerate(dests):
                frac = 1 if len(dests) == 1 else (allocation[old] if i == 0 else 1 - allocation[old])
                for metric in metrics:
                    new[dest][metric] += values[old].get(metric, 0) * frac
        row = {"scenario": ";".join(f"{k}={v:g}" for k, v in allocation.items())}
        for metric in metrics:
            row[metric] = pd.Series([v[metric] for v in new.values()]).median() / old_medians[metric]
        scenarios.append(row)
    frame = pd.DataFrame(scenarios)
    frame.to_csv(args.output_dir / "split_allocation_scenarios.csv", index=False)
    summary = {metric: {"min": round(float(frame[metric].min()), 3), "max": round(float(frame[metric].max()), 3)} for metric in metrics}
    equal = frame[frame.scenario == ";".join(f"{k}=0.5" for k in splits)].iloc[0]
    for metric in metrics:
        summary[metric]["equal_split"] = round(float(equal[metric]), 3)
    result = {"split_wards": {k: recipients[k] for k in splits}, "scenarios": len(frame), "share_grid": [0, .25, .5, .75, 1], "latest_osm_snapshot": str(osm.date.max()), "ratios": summary}
    (args.output_dir / "sensitivity_results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
