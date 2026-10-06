"""Check that no restricted data or manuscripts are staged for publication."""
from pathlib import Path
import csv
import json
import subprocess

ROOT = Path(__file__).resolve().parent
forbidden_suffixes = {'.docx', '.pdf', '.tex', '.xlsx', '.xls', '.csv', '.gpkg', '.shp', '.dbf', '.shx', '.tif', '.tiff', '.pbf', '.geojson'}
allowed_csv = {
    'data/table13b_wards_before.csv': {'Ward', 'Pop_2025', 'area_km2'},
    'data/osm_ward_year_counts.csv': {'date', 'year', 'snapshot', 'ward', 'metric', 'value'},
    'data/successor_proposal_2025.csv': {'ward', 'area_km2', 'proposal_population', 'proposed_staff', 'city_reassigned', 'inherited_officials', 'inherited_civil_servants'},
}
listed = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT)
paths = [ROOT / p.decode('utf-8') for p in listed.split(b'\0') if p]
violations = []
for path in paths:
    if not path.is_file():
        continue
    relative = path.relative_to(ROOT).as_posix()
    if path.suffix.lower() in forbidden_suffixes and relative not in allowed_csv:
        violations.append(str(path.relative_to(ROOT)))
    if relative in allowed_csv:
        with path.open(encoding='utf-8-sig', newline='') as handle:
            rows = csv.DictReader(handle)
            if set(rows.fieldnames or ()) != allowed_csv[relative]:
                violations.append(f'{relative}: unexpected columns')
            if not any(True for _ in rows):
                violations.append(f'{relative}: empty table')
    if any(token in path.name.lower() for token in ('manuscript', 'paper5_revised', 'interview transcript')):
        violations.append(str(path.relative_to(ROOT)))
    if path.suffix.lower() == '.ipynb':
        notebook = json.loads(path.read_text(encoding='utf-8'))
        if any(cell.get('outputs') for cell in notebook.get('cells', []) if cell.get('cell_type') == 'code'):
            violations.append(f'{path.relative_to(ROOT)}: saved outputs')
if violations:
    raise SystemExit(f'BLOCKED: restricted or manuscript files: {violations}')
print('PASS: only the three approved ward aggregate CSVs; no restricted data, generated outputs or manuscript files.')
