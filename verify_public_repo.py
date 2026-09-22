"""Fail if the public-code folder contains manuscripts or restricted data."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent
forbidden_suffixes={'.docx','.pdf','.tex','.xlsx','.xls','.csv','.gpkg','.shp','.dbf','.shx','.tif','.tiff','.pbf'}
allowed_geojson=set()  # Code-only release: no spatial data are bundled.
violations=[]
for p in ROOT.rglob('*'):
    if not p.is_file() or '.git' in p.parts:
        continue
    if p.suffix.lower() in forbidden_suffixes:
        violations.append(str(p.relative_to(ROOT)))
    if p.suffix.lower()=='.geojson' and p.name not in allowed_geojson:
        violations.append(str(p.relative_to(ROOT)))
    if any(token in p.name.lower() for token in ['manuscript','paper5_revised','interview transcript']):
        violations.append(str(p.relative_to(ROOT)))

notebook=json.loads((ROOT/'reproduce_paper5.ipynb').read_text(encoding='utf-8'))
assert all(not c.get('outputs') for c in notebook['cells'] if c['cell_type']=='code')
assert not violations, f'Files not permitted in code-only release: {violations}'
print('PASS: code-only repository contains no manuscript or restricted-data file types.')
