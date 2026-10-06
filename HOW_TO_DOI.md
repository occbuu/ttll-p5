# Archiving the revised code

The DOI `10.5281/zenodo.22885665` is specific to historical release `v1.0.0` and must not be cited as the archive of the revised 625-scenario analysis.

1. Run the commands in `README.md` with the article's aggregate inputs. Confirm the expected proposal and sensitivity results and all five figures (Figure 1 requires the external former-ward geometry).
2. Run `python verify_public_repo.py` and review `git diff --cached` for anything beyond the three approved ward-level aggregate CSVs, manuscripts and personal information.
3. Commit and push the revised code, then create a **new versioned GitHub release** (suggested `v2.0.0`).
4. Confirm Zenodo created a *new version DOI* for that release. Record the DOI in `CITATION.cff`, `.zenodo.json`, the README and the paper's data/code statement. Do not reuse the `v1.0.0` version DOI.
5. If Zenodo is unavailable, cite the GitHub release tag and its commit SHA in the paper, with the repository URL and access date.
