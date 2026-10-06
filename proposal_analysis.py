"""Analyse 2025 successor-ward proposal figures and proposed staff allocations.

These are proposal-era administrative figures and planned positions, not
observed staffing or service outcomes. See data/README.md for sources.
"""
from pathlib import Path
import argparse
import json

import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('data/successor_proposal_2025.csv'))
    parser.add_argument('--output-dir', type=Path, default=Path('outputs'))
    args = parser.parse_args()
    frame = pd.read_csv(args.input)
    if len(frame) != 12 or frame.ward.nunique() != 12 or frame[['area_km2','proposal_population','proposed_staff']].isna().any().any():
        raise ValueError('Expected 12 complete, unique successor ward rows')
    if (frame[['area_km2','proposal_population','proposed_staff']] <= 0).any().any():
        raise ValueError('All source values must be positive')
    args.output_dir.mkdir(parents=True, exist_ok=True)
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
    }
    (args.output_dir / 'successor_proposal_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    fig, ax = plt.subplots(figsize=(9.2, 6.2))
    sizes = frame.proposed_staff * 2.0
    ax.scatter(frame.area_km2, frame.proposal_population / 1000, s=sizes,
               facecolor='#3385aa', edgecolor='#12415a', alpha=.75)
    for _, row in frame.iterrows():
        ax.annotate(row.ward, (row.area_km2, row.proposal_population / 1000),
                    xytext=(5, 3), textcoords='offset points', fontsize=9)
    ax.set(xlabel='Area in 2025 arrangement proposal (km²)',
           ylabel='Population in 2025 arrangement proposal (thousands)',
           title='Successor wards have different population and territorial profiles')
    ax.grid(alpha=.17)
    fig.tight_layout()
    for suffix in ('pdf','png'):
        fig.savefig(args.output_dir / f'Figure5_proposal_ward_profiles.{suffix}', dpi=240)
    plt.close(fig)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
