# Notebooks

Purpose-specific exploratory and development notebooks.

| Notebook | Purpose |
|----------|---------|
| `nhanes_demographics_link_finder.ipynb` | Iteratively developed logic for locating demographics and component file links; metadata parsing evolution. |
| `nhanes_explorer_demo.ipynb` | Basic usage demo of NHANESExplorer class and merging datasets. |
| `nhanes_url_testing.ipynb` | URL pattern diagnostics across cycles/components. |
| `observatory_exploration.ipynb` | Ad-hoc experimentation & prototype transformations. |

Guidelines:
- Keep large data out of version control.
- Convert stable logic into library code (`pophealth_observatory/`).
- Use markdown sections for milestones (Sections 1..N) when iterating parsers.
