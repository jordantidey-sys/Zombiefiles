# Public Funding Risk Triage (hackathon MVP)

A Streamlit prototype that cross-references Alberta public payment disclosure against
entity records, to surface organisations receiving public funds while showing weak
financial-reporting continuity.

It is a triage aid for human review, **not** a determination of wrongdoing. Every
signal it shows is drawn from published open data and can be wrong, stale, or the
result of an entity having legitimately changed name, structure, or filing schedule.

Built as a hackathon entry, April 2026. Not maintained.

## This repository does not run as cloned

Both copies of the app open a dataset that is not committed here:

```python
DATA_PATH = Path("Data/general/entity_golden_records.jsonl")   # not in this repo
```

Starting it produces `Missing dataset: Data/general/entity_golden_records.jsonl`.
`peek.py` likewise reads `Data/fed/grants_contributions.jsonl`, also absent.

What *is* committed is one source extract:

| Path | Contents |
| --- | --- |
| `Zombie MVP/Data/ab/ab_contracts.jsonl` | Alberta government payment disclosure — recipient, amount, ministry, fiscal year. Corporate recipients; no personal data. |

Building `entity_golden_records.jsonl` from that extract was done outside this
repository during the event and the step was never committed. Anyone reviving this
would need to write it.

## Layout

| Path | Notes |
| --- | --- |
| `app.py` | The Streamlit app. |
| `Zombie MVP/app.py` | **Byte-identical duplicate** of `app.py`. One of the two should go. |
| `Zombie MVP/Data/ab/ab_contracts.jsonl` | The one committed dataset. |
| `peek.py` | Ad-hoc inspection script; reads files not present here. |
| `inspect_files.py`, `schema_check.py` | Empty files. |
| `streamlit-app-2026-04-29-11-49-12.webm` | Screen recording of the working demo, 9.4 MB — about 77% of this repository's size. |

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

`requirements.txt` pins `streamlit` and `pandas` but leaves `sqlalchemy`,
`psycopg2-binary`, `python-dotenv` and `google-genai` unpinned, and nothing in the
committed code imports those four.

## Licence

None. Without a licence file, default copyright applies and no one has permission to
use, copy, or modify this — worth fixing if it is meant as a portfolio piece.
