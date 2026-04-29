print("PEEK SCRIPT STARTED")

import json

files = [
    "Data/fed/grants_contributions.jsonl",
    "Data/cra/cra_financial_general.jsonl",
    "Data/cra/cra_financial_details.jsonl",
    "Data/general/entity_golden_records.jsonl",
    "Data/general/entity_source_links.jsonl",
]

for p in files:
    print(f"\n--- {p} ---")
    with open(p, encoding="utf-8") as f:
        row = json.loads(f.readline())
        print(list(row.keys())[:100])
        print(row)

print("PEEK SCRIPT FINISHED")
import json

files = [
    "Data/fed/grants_contributions.jsonl",
    "Data/cra/cra_financial_general.jsonl",
    "Data/cra/cra_financial_details.jsonl",
    "Data/general/entity_golden_records.jsonl",
    "Data/general/entity_source_links.jsonl",
]

for p in files:
    print(f"\n--- {p} ---")
    try:
        with open(p, encoding="utf-8") as f:
            row = json.loads(f.readline())
            print("KEYS:", list(row.keys())[:100])
            print("SAMPLE:", row)
    except Exception as e:
        print("ERROR:", e)
        