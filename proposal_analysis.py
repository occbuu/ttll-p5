"""Analyse 2025 successor-ward proposal figures and proposed staff allocations.

These are proposal-era administrative figures and planned positions, not
observed staffing or service outcomes. See data/README.md for sources.
"""
from pathlib import Path
import argparse
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sensitivity import MERGE


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/successor_proposal_2025.csv'))
    parser.add_argument('--output-dir', type=Path, default=Path('outputs'))
    args = parser.parse_args()
    frame = pd.read_csv(args.input)
    source_cols = ['area_km2', 'proposal_population', 'proposed_staff',
                   'city_reassigned', 'inherited_officials', 'inherited_civil_servants']
    if len(frame) != 12 or set(frame.ward) != set(MERGE) or frame[source_cols].isna().any().any():
        raise ValueError('Expected 12 complete, unique successor ward rows')
    if (frame[source_cols] <= 0).any().any():
        raise ValueError('All source values must be positive')
    if not (frame.city_reassigned + frame.inherited_officials +
            frame.inherited_civil_servants == frame.proposed_staff).all():
        raise ValueError('Staffing components must sum to the proposed positions in every ward')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame['predecessor_footprints'] = frame.ward.map(lambda ward: len(MERGE[ward]))
    frame['inherited_pool'] = frame.inherited_officials + frame.inherited_civil_servants
    frame['inherited_share'] = frame.inherited_pool / frame.proposed_staff
    total_staff = int(frame.proposed_staff.sum())
    frame['population_proportional_benchmark'] = (
        frame.proposal_population / frame.proposal_population.sum() * total_staff
    ).round(1)
    frame['density_per_km2'] = (frame.proposal_population / frame.area_km2).round().astype(int)
    frame['residents_per_proposed_staff'] = (frame.proposal_population / frame.proposed_staff).round().astype(int)
    frame['km2_per_proposed_staff'] = (frame.area_km2 / frame.proposed_staff).round(3)
    frame.to_csv(args.output_dir / 'successor_proposal_diagnostics.csv', index=False)
    summary = {
        'wards': 12,
        'population_range': [int(frame.proposal_population.min()), int(frame.proposal_population.max())],
        'area_range_km2': [float(frame.area_km2.min()), float(frame.area_km2.max())],
        'proposed_staff_range': [int(frame.proposed_staff.min()), int(frame.proposed_staff.max())],
        'residents_per_proposed_staff_range': [int(frame.residents_per_proposed_staff.min()), int(frame.residents_per_proposed_staff.max())],
        'km2_per_proposed_staff_range': [float(frame.km2_per_proposed_staff.min()), float(frame.km2_per_proposed_staff.max())],
        'population_area_spearman': round(float(frame.proposal_population.corr(frame.area_km2, method='spearman')), 3),
        'population_staff_spearman': round(float(frame.proposal_population.corr(frame.proposed_staff, method='spearman')), 3),
        'area_staff_spearman': round(float(frame.area_km2.corr(frame.proposed_staff, method='spearman')), 3),
        'staff_predecessor_footprints_spearman': round(float(frame.proposed_staff.corr(frame.predecessor_footprints, method='spearman')), 3),
        'inherited_pool_footprints_spearman': round(float(frame.inherited_pool.corr(frame.predecessor_footprints, method='spearman')), 3),
        'city_reassigned_footprints_spearman': round(float(frame.city_reassigned.corr(frame.predecessor_footprints, method='spearman')), 3),
        'log_staff_log_population_slope': round(float(np.polyfit(np.log(frame.proposal_population), np.log(frame.proposed_staff), 1)[0]), 3),
        'total_proposed_positions': total_staff,
        'city_reassigned_total': int(frame.city_reassigned.sum()),
        'inherited_pool_total': int(frame.inherited_pool.sum()),
        'inherited_pool_share': round(float(frame.inherited_pool.sum() / total_staff), 3),
        'hiep_binh_population_benchmark': float(frame.loc[frame.ward == 'Hiep Binh', 'population_proportional_benchmark'].iloc[0]),
        'long_phuoc_population_benchmark': float(frame.loc[frame.ward == 'Long Phuoc', 'population_proportional_benchmark'].iloc[0]),
    }
    (args.output_dir / 'successor_proposal_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    fig, ax = plt.subplots(figsize=(10.5, 6.7))
    size_for = lambda staff: (staff - 75) * 18 + 80
    sizes = frame.proposed_staff.map(size_for)
    points = ax.scatter(frame.area_km2, frame.proposal_population / 1000, s=sizes,
                        c=frame.inherited_share * 100, cmap='viridis', vmin=40, vmax=70,
                        edgecolor='#23313b', linewidth=.8, alpha=.85, zorder=3)
    for _, row in frame.iterrows():
        ax.annotate(row.ward, (row.area_km2, row.proposal_population / 1000),
                    xytext=(5, 3), textcoords='offset points', fontsize=9)
    ax.set(xlabel='Area in the 2025 arrangement proposal (km²)',
           ylabel='Population in the 2025 arrangement proposal (thousands)',
           title='Population, territory and the composition of planned personnel')
    for staff in (80, 100, 120):
        ax.scatter([], [], s=size_for(staff), facecolor='#94a3ab', edgecolor='#23313b',
                   alpha=.7, label=f'{staff} proposed positions')
    ax.legend(title='Marker area', loc='upper right', frameon=True, fontsize=8.5,
              labelspacing=1.2, borderpad=.7)
    colorbar = fig.colorbar(points, ax=ax, pad=.025, shrink=.83)
    colorbar.set_label('Positions pooled from former wards (%)')
    ax.grid(alpha=.17)
    fig.tight_layout()
    for suffix in ('pdf','png'):
        fig.savefig(args.output_dir / f'Figure5_proposal_ward_profiles.{suffix}', dpi=240)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
