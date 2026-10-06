"""Build publication figures from the archived aggregate sources.

The map colours *former* ward geometries by legal successor. Split former
wards are hatched and intentionally are not drawn as successor polygons.
"""
from __future__ import annotations

import json
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch

from sensitivity import MERGE, key

FIG = Path("outputs")
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 12,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "pdf.fonttype": 42,
})


def save(fig, stem: str) -> None:
    fig.savefig(FIG / f"{stem}.pdf", bbox_inches="tight", pad_inches=.14)
    fig.savefig(FIG / f"{stem}.png", dpi=240, bbox_inches="tight", pad_inches=.14)
    plt.close(fig)


def make_map(ward_geojson: Path, locator_geojson: Path | None = None) -> None:
    import geopandas as gpd
    geo = gpd.read_file(ward_geojson).to_crs(4326)
    dest = {}
    for new, olds in MERGE.items():
        for old in olds:
            dest.setdefault(key(old.rstrip("*")), []).append(new)
    assert len(dest) == len(geo) == 34
    names = list(MERGE)
    cmap = plt.get_cmap("tab20", 12)
    colors = {name: cmap(i) for i, name in enumerate(names)}
    geo["old_key"] = geo["Ten"].str.replace("Phường ", "", regex=False).map(key)
    assert set(geo.old_key) == set(dest)
    fig, ax = plt.subplots(figsize=(8.7, 9.2))
    for _, row in geo.iterrows():
        recipients = dest[row.old_key]
        is_split = len(recipients) > 1
        geo.loc[[row.name]].plot(ax=ax, facecolor="#eeeeee" if is_split else colors[recipients[0]],
                                 edgecolor="white", linewidth=.75, hatch="////" if is_split else None)
    # A label in each successor's largest wholly allocated old polygon is a
    # visual locator only; it is not a successor centroid or boundary.
    for successor in names:
        candidates = geo[geo.old_key.map(lambda old: dest[old] == [successor])]
        if candidates.empty:
            continue
        sample = candidates.to_crs(3405).assign(a=lambda x: x.area).sort_values("a").iloc[-1]
        xy = sample.geometry.representative_point()
        xy = gpd.GeoSeries([xy], crs=3405).to_crs(4326).iloc[0]
        label = successor.replace(" ", "\n") if len(successor) > 11 else successor
        ax.text(xy.x, xy.y, label, ha="center", va="center", fontsize=10.3,
                color="#17212b", weight="bold", path_effects=[])
    handles = [Patch(facecolor=colors[n], edgecolor="none", label=n) for n in names]
    handles.append(Patch(facecolor="#eeeeee", hatch="////", edgecolor="#777777", label="Split former ward"))
    ax.legend(handles=handles, title="Legal successor assignment", frameon=False,
              loc="lower left", bbox_to_anchor=(1.01, .01), ncol=1, fontsize=10)
    ax.set_title("Thu Duc ward assignments, 2025", loc="left", fontsize=16, weight="bold", pad=12)
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.set_aspect("equal")
    ax.grid(alpha=.12)
    # Geodesic 5 km scale at the map's southern edge (geographic CRS).
    from pyproj import Geod
    west, south, east, north = geo.total_bounds
    x0 = west + .04 * (east - west)
    y0 = south + .035 * (north - south)
    x1, _, _ = Geod(ellps="WGS84").fwd(x0, y0, 90, 5000)
    ax.plot([x0, x1], [y0, y0], color="#101820", lw=3, solid_capstyle="butt", zorder=10)
    ax.plot([x0, x0], [y0-.003, y0+.003], color="#101820", lw=1.5, zorder=10)
    ax.plot([x1, x1], [y0-.003, y0+.003], color="#101820", lw=1.5, zorder=10)
    ax.text((x0+x1)/2, y0+.005, "5 km", ha="center", va="bottom", fontsize=9,
            weight="bold", color="#101820")
    if locator_geojson:
        country = gpd.read_file(locator_geojson).to_crs(4326)
        inset = fig.add_axes([.78, .73, .12, .17])
        country.plot(ax=inset, facecolor="#e4e8ec", edgecolor="#677584", linewidth=.55)
        inset.scatter([geo.geometry.union_all().centroid.x], [geo.geometry.union_all().centroid.y],
                      s=34, color="#b42318", zorder=5)
        inset.set_xlim(101, 111); inset.set_ylim(8, 24)
        inset.set_aspect("equal"); inset.set_xticks([]); inset.set_yticks([])
        inset.set_title("Viet Nam", fontsize=9, weight="bold")
    save(fig, "Figure1_legal_allocation_map")


def make_framework() -> None:
    fig, ax = plt.subplots(figsize=(10.6, 3.8))
    ax.set_xlim(0, 10.6); ax.set_ylim(0, 3.8); ax.axis("off")
    boxes = [
        (0.2, "1  LEGAL MANDATE", "Who has authority?\nLaw and functions", "Observed", "#dcebf5", "#1d4f70"),
        (3.72, "2  EXPOSURE", "What is assigned?\nPeople, area, objects", "Estimated", "#dbeee9", "#16675a"),
        (7.24, "3  CAPACITY", "Can it act?\nStaff, records, routines", "Plans, not outcomes", "#f5e7d9", "#8d4d1a"),
    ]
    for x, head, body, status, fill, edge in boxes:
        ax.add_patch(FancyBboxPatch((x, 1.0), 3.05, 2.05, boxstyle="round,pad=.08,rounding_size=.08",
                                    linewidth=1.5, edgecolor=edge, facecolor=fill))
        ax.text(x+.18, 2.7, head, fontsize=13, weight="bold", color=edge, va="top")
        ax.text(x+.18, 2.25, body, fontsize=13.5, color="#182333", va="top", linespacing=1.4)
        ax.text(x+.18, 1.2, status.upper(), fontsize=11, weight="bold", color=edge)
    for x in (3.33, 6.85):
        ax.add_patch(FancyArrowPatch((x, 2.05), (x+.32, 2.05), arrowstyle="-|>", mutation_scale=22,
                                     linewidth=2.2, color="#536473", zorder=6))
    ax.text(5.3, 3.5, "A sequential audit of administrative rescaling", ha="center", fontsize=17, weight="bold")
    ax.text(5.3, .45, "Legal assignment and spatial exposure do not identify service quality or reform effects.",
            ha="center", fontsize=11, color="#384656")
    save(fig, "Figure2_three_step_framework")


def make_intervals(results_json: Path) -> None:
    data = json.loads(results_json.read_text(encoding="utf-8"))["ratios"]
    labels = [
        ("Population (modelled)", "population", "Core"), ("Area", "area_km2", "Core"),
        ("Road length", "road_km", "OSM"), ("Shops", "shop", "OSM"),
        ("Food outlets", "food_outlet", "OSM"), ("Public spaces", "public_space", "OSM"),
        ("Education", "education", "OSM"), ("Health", "health", "OSM"),
        ("Religious premises", "religious_premises", "OSM"), ("Marketplaces", "marketplace", "OSM"),
    ]
    fig, ax = plt.subplots(figsize=(9.6, 6.7))
    ys = np.arange(len(labels))[::-1]
    for y, (label, metric, typ) in zip(ys, labels):
        v = data[metric]
        c = "#1b5e85" if typ == "Core" else "#bb6a2b"
        ax.plot([v["min"], v["max"]], [y, y], color=c, lw=3.1, solid_capstyle="round")
        ax.scatter([v["equal_split"]], [y], marker="D", s=42, color=c, zorder=3, edgecolor="white", linewidth=.5)
        ax.text(v["max"]+.07, y, f'{v["min"]:.2f}–{v["max"]:.2f}', va="center", fontsize=11, color="#293441")
    ax.axvline(1, color="#777777", lw=1, ls="--")
    ax.set_yticks(ys, [x[0] for x in labels]); ax.set_xlim(.75, 7.35)
    ax.set_xlabel("Ratio of median successor ward to median former ward")
    ax.set_title("Exposure increases across split-allocation scenarios", loc="left", fontsize=16, weight="bold", pad=12)
    ax.grid(axis="x", alpha=.17)
    ax.legend(handles=[Line2D([0],[0], color="#1b5e85", lw=3, marker="D", label="Modelled population / area"),
                       Line2D([0],[0], color="#bb6a2b", lw=3, marker="D", label="OSM mapped stock")],
              frameon=False, loc="lower right", fontsize=10)
    save(fig, "Figure3_scenario_envelopes")


def make_osm_quality(wards_before: Path, osm_counts: Path) -> None:
    osm = pd.read_csv(osm_counts)
    latest = osm.loc[osm.date.eq(osm.date.max())]
    wards = pd.read_csv(wards_before)
    lookup = {key(x): x for x in wards.Ward}
    classes = [("Health", "health"), ("Food outlets", "food_outlet"),
               ("Education", "education"), ("Public spaces", "public_space"),
               ("Religious sites", "religious_premises"), ("Shops", "shop"),
               ("Marketplaces", "marketplace"), ("Roads", "road_km")]
    zero = []
    for label, metric in classes:
        selected = latest[latest.metric.eq(metric)]
        vals = {key(r.ward): float(r.value) for _, r in selected.iterrows()}
        assert set(vals).issubset(lookup)
        zero.append((label, sum(vals.get(k, 0) == 0 for k in lookup), len(lookup)))
    pd.DataFrame(zero, columns=["class", "zero_mapped_wards", "former_wards"]).to_csv(FIG / "Figure4_zero_counts.csv", index=False)
    fig, ax = plt.subplots(figsize=(8.3, 4.9))
    labels = [r[0] for r in zero]
    vals = [100*r[1]/r[2] for r in zero]
    yy = np.arange(len(zero))[::-1]
    ax.barh(yy, vals, color=["#aa4b3b" if v >= 20 else "#b88640" for v in vals], height=.67)
    for y, (label, n, total), val in zip(yy, zero, vals):
        ax.text(val+.7, y, f"{n}/{total}", va="center", fontsize=11)
    ax.set_yticks(yy, labels); ax.set_xlim(0, max(vals)+10)
    ax.set_xlabel("Former wards with zero mapped features (%)")
    ax.set_title("OSM coverage varies by feature class", loc="left", fontsize=16, weight="bold", pad=12)
    ax.grid(axis="x", alpha=.15)
    save(fig, "Figure4_osm_sparsity")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wards-before", type=Path, required=True)
    parser.add_argument("--osm-counts", type=Path, required=True)
    parser.add_argument("--results-json", type=Path, required=True)
    parser.add_argument("--ward-geojson", type=Path, help="Optional former-ward boundaries for Figure 1")
    parser.add_argument("--locator-geojson", type=Path, help="Optional Viet Nam outline for Figure 1 locator inset")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    FIG = args.output_dir
    FIG.mkdir(parents=True, exist_ok=True)
    if args.ward_geojson:
        make_map(args.ward_geojson, args.locator_geojson)
    make_framework()
    make_intervals(args.results_json)
    make_osm_quality(args.wards_before, args.osm_counts)
    print("Created figures in", FIG)
