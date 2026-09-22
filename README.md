# ttll-p5

Reproduction code for the administrative-rescaling and jurisdictional-exposure analysis in the former Thu Duc City, Ho Chi Minh City.

This repository contains **code and documentation only**. It does not contain the manuscript, survey microdata, interview transcripts, names, contact details, exact addresses, identifiable job information, or the invalid post-reform interview workbook.

## What the code does

`analyse_paper5.py`:

1. links the restricted 23-record public-sector subset to the original survey export by timestamp;
2. verifies selected fields character-for-character;
3. produces aggregate position and neighbourhood-assessment tables;
4. calculates jurisdictional-exposure ratios for the 34 former and 12 successor wards;
5. performs temporal and spatial fitness-for-purpose diagnostics for OpenStreetMap;
6. generates two maps and five charts/diagrams.

The script does not estimate causal reform effects or treat OSM as an authoritative facility census.

## Required inputs

The repository does not distribute these inputs. Authorized users must supply paths to:

- a cleaned authority survey workbook;
- the original authority survey export;
- the public/derived aggregate CSV tables used by the study;
- former Thu Duc ward boundaries in GeoJSON;
- a Vietnam outline GeoJSON for the locator inset;
- an EPSG:4326 OpenStreetMap POI GeoPackage;
- original public spatial sources obtained under their respective licences.

## Command-line use

```bash
python analyse_paper5.py \
  --clean-authorities /restricted/QData_Authorities.xlsx \
  --raw-authorities "/restricted/Authority survey_Truong Tho Living Lab (Responses).xlsx" \
  --legacy-tables /public-or-authorized/tables \
  --ward-geojson /public/ThuDucCity_ward.geojson \
  --vietnam-geojson /public/vietnam_adm0.geojson \
  --poi-gpkg /public/osm_2026_pois.gpkg \
  --output-dir outputs
```

The same workflow is available in `reproduce_paper5.ipynb`.

## Confidentiality

The broader Truong Tho Independent Fieldwork Campaign 2023 involved residents, business owners, local experts and public-sector practitioners. Raw participant-level data are restricted because participants were assured confidentiality. Do not commit survey workbooks or any row-level extracts to this repository.

## Open-data attribution

OpenStreetMap-derived inputs remain subject to ODbL attribution requirements: © OpenStreetMap contributors. GHS-POP and other external inputs retain their original licences. Users are responsible for obtaining and documenting source versions.

## Archive and DOI

After pushing the repository to GitHub, follow `HOW_TO_DOI.md` to create an immutable Zenodo release. Insert the final repository URL and DOI into the manuscript only after both resolve publicly.
