import json
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Public Funding Risk Triage", layout="wide")
st.title("Public Funding Risk Triage (MVP)")

st.caption(
    "Identifies CRA-linked entities with public funding signals and weak financial reporting continuity. "
    "This is a triage tool for review, not a determination of wrongdoing."
)

DATA_PATH = Path("Data/general/entity_golden_records.jsonl")
MAX_ROWS = 50_000


def _is_populated(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, str)):
        return len(value) > 0
    return True


def _safe_year_from_text(value: str):
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) >= 4:
        for i in range(len(digits) - 3):
            candidate = int(digits[i : i + 4])
            if 1900 <= candidate <= 2100:
                return candidate
    return None


def _has_recent_cra_filing_info(cra_profile, min_year: int = 2022) -> bool:
    if not isinstance(cra_profile, dict) or not cra_profile:
        return False

    for key, value in cra_profile.items():
        key_l = str(key).lower()
        if any(token in key_l for token in ["fpe", "filing", "fiscal", "year", "date"]):
            if isinstance(value, int) and value >= min_year:
                return True
            if isinstance(value, str):
                year = _safe_year_from_text(value)
                if year is not None and year >= min_year:
                    return True
    return False


def _clean_scalar(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _build_risk_fields(row: pd.Series):
    fed_profile = row.get("fed_profile")
    ab_profile = row.get("ab_profile")
    cra_profile = row.get("cra_profile")
    status_raw = row.get("status")
    status = str(status_raw or "").strip().lower()

    has_public_funding = _is_populated(fed_profile) or _is_populated(ab_profile)
    has_cra_profile = _is_populated(cra_profile)
    has_recent_cra = _has_recent_cra_filing_info(cra_profile)

    weak_status = status not in {"active", "good_standing", "good standing"}

    reasons = []

    if has_public_funding and not has_cra_profile:
        reasons.append(
            "Public funding detected, but this entity is not linked to a CRA charity profile. "
            "This is treated as an unmatched entity signal, not a zombie-recipient flag."
        )

    if has_public_funding and has_cra_profile and weak_status:
        reasons.append(
            f"CRA-linked funded entity has status '{status_raw}', which may indicate inactivity or weak standing."
        )

    if has_public_funding and has_cra_profile and not has_recent_cra:
        reasons.append(
            "This CRA-linked organization shows evidence of public funding but lacks a recent CRA filing signal "
            "in available records, suggesting a potential gap in reporting continuity."
        )

    potential_zombie = (
        has_public_funding
        and has_cra_profile
        and (weak_status or not has_recent_cra)
    )

    if has_public_funding and has_cra_profile and not has_recent_cra:
        risk_summary = "Funded charity + weak recent filing signal"
    elif has_public_funding and has_cra_profile and weak_status:
        risk_summary = "Funded charity + weak entity status"
    elif has_public_funding and not has_cra_profile:
        risk_summary = "Funded entity not linked to CRA charity profile"
    else:
        risk_summary = "No major MVP flag"

    why_flagged = (
        " ".join(reasons)
        if reasons
        else "No material risk signals identified under MVP rules."
    )

    return pd.Series(
        {
            "has_public_funding": has_public_funding,
            "has_cra_profile": has_cra_profile,
            "has_recent_cra_info": has_recent_cra,
            "potential_zombie": potential_zombie,
            "risk_summary": risk_summary,
            "why_flagged": why_flagged,
        }
    )


@st.cache_data(show_spinner=True)
def load_entities(path: str, max_rows: int):
    rows = []
    selected = [
        "id",
        "canonical_name",
        "entity_type",
        "bn_root",
        "bn_variants",
        "dataset_sources",
        "source_summary",
        "cra_profile",
        "fed_profile",
        "ab_profile",
        "confidence",
        "status",
    ]

    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_rows:
                break
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue

            row = {col: raw.get(col) for col in selected}
            rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["dataset_sources"] = df["dataset_sources"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
    df["dataset_sources_text"] = df["dataset_sources"].apply(lambda x: ", ".join(x))

    df["has_fed"] = df["dataset_sources"].apply(lambda x: "fed" in x)
    df["has_cra"] = df["dataset_sources"].apply(lambda x: "cra" in x)

    df = df[df["has_fed"] | df["has_cra"]].copy()

    risk_df = df.apply(_build_risk_fields, axis=1)
    df = pd.concat([df, risk_df], axis=1)

    return df


if not DATA_PATH.exists():
    st.error(f"Missing dataset: {DATA_PATH}")
    st.stop()


with st.spinner("Loading first 50,000 rows from golden records..."):
    entities = load_entities(str(DATA_PATH), MAX_ROWS)

if entities.empty:
    st.warning("No eligible fed/cra records found in the first 50,000 rows.")
    st.stop()


st.caption(f"Loaded {len(entities):,} fed/cra records from first {MAX_ROWS:,} rows.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Potential Review Flags", int(entities["potential_zombie"].sum()))
col2.metric("Has Public Funding", int(entities["has_public_funding"].sum()))
col3.metric("Has CRA Profile", int(entities["has_cra_profile"].sum()))
col4.metric(
    "Unmatched Funded Entities",
    int(((entities["has_public_funding"]) & (~entities["has_cra_profile"])).sum()),
)

st.info(
    "This MVP reduces a pool of 17,000+ publicly funded entities to a focused CRA-linked review list "
    "based on reporting-continuity signals."
)


st.subheader("Search & Filter")

search_text = st.text_input("Search canonical name", value="")

source_filter = st.multiselect(
    "Dataset source filter",
    options=["fed", "cra"],
    default=["fed", "cra"],
)

zombie_only = st.checkbox("Show CRA-linked review flags only", value=True)
show_unmatched = st.checkbox("Show unmatched funded entities", value=False)
organizations_only = st.checkbox("Organizations only", value=True)

status_filter = st.multiselect(
    "Status filter",
    options=sorted([s for s in entities["status"].dropna().unique()]),
    default=[],
)

filtered = entities.copy()

if search_text.strip():
    q = search_text.strip().lower()
    filtered = filtered[
        filtered["canonical_name"].fillna("").str.lower().str.contains(q, regex=False)
    ]

if source_filter:
    filtered = filtered[
        filtered["dataset_sources"].apply(lambda src: any(s in src for s in source_filter))
    ]

if organizations_only:
    filtered = filtered[
        filtered["entity_type"].isin(["organization", "charity", "charitable_org"])
    ]

if zombie_only:
    filtered = filtered[filtered["potential_zombie"]]

if show_unmatched:
    filtered = filtered[
        (filtered["has_public_funding"]) & (~filtered["has_cra_profile"])
    ]

if status_filter:
    filtered = filtered[filtered["status"].isin(status_filter)]


st.write(f"Showing {len(filtered):,} records")

display_cols = [
    "id",
    "canonical_name",
    "entity_type",
    "bn_root",
    "dataset_sources_text",
    "confidence",
    "status",
    "has_public_funding",
    "has_cra_profile",
    "has_recent_cra_info",
    "potential_zombie",
    "risk_summary",
    "why_flagged",
]

st.dataframe(
    filtered[display_cols],
    use_container_width=True,
    hide_index=True,
)


st.subheader("Top 3 Review Candidates")

top_candidates = entities[
    (entities["potential_zombie"])
    & (entities["has_public_funding"])
    & (entities["has_cra_profile"])
    & (entities["entity_type"].isin(["organization", "charity", "charitable_org"]))
].copy()

top_candidates = top_candidates.sort_values(
    by=["confidence", "has_recent_cra_info"],
    ascending=[False, True],
).head(3)

if top_candidates.empty:
    st.info("No top review candidates found under current MVP rules.")
else:
    for _, candidate in top_candidates.iterrows():
        st.markdown(f"### {candidate['canonical_name']}")
        st.write(candidate["why_flagged"])
        st.write(
            {
                "id": int(candidate["id"]) if pd.notna(candidate["id"]) else None,
                "entity_type": candidate["entity_type"],
                "bn_root": candidate["bn_root"],
                "dataset_sources": candidate["dataset_sources"],
                "confidence": _clean_scalar(candidate["confidence"]),
                "status": candidate["status"],
                "risk_summary": candidate["risk_summary"],
            }
        )
        st.divider()


st.subheader("Entity Details")

if filtered.empty:
    st.info("No entities match the current filters.")
else:
    selection_options = (
        filtered["id"].astype(str)
        + " | "
        + filtered["canonical_name"].fillna("")
    )

    selection_map = dict(zip(selection_options, filtered.index))
    selected_label = st.selectbox("Select one entity", options=selection_options.tolist())
    selected_row = filtered.loc[selection_map[selected_label]]

    st.markdown("### Audit Triage Note")
    st.write(selected_row["why_flagged"])

    st.write(
        {
            "id": int(selected_row["id"]) if pd.notna(selected_row["id"]) else None,
            "canonical_name": selected_row["canonical_name"],
            "entity_type": selected_row["entity_type"],
            "bn_root": selected_row["bn_root"],
            "bn_variants": selected_row["bn_variants"],
            "dataset_sources": selected_row["dataset_sources"],
            "confidence": _clean_scalar(selected_row["confidence"]),
            "status": selected_row["status"],
            "has_public_funding": bool(selected_row["has_public_funding"]),
            "has_cra_profile": bool(selected_row["has_cra_profile"]),
            "has_recent_cra_info": bool(selected_row["has_recent_cra_info"]),
            "potential_zombie": bool(selected_row["potential_zombie"]),
            "risk_summary": selected_row["risk_summary"],
            "why_flagged": selected_row["why_flagged"],
        }
    )

    with st.expander("CRA Profile (raw)"):
        st.json(selected_row["cra_profile"])

    with st.expander("FED Profile (raw)"):
        st.json(selected_row["fed_profile"])

    with st.expander("AB Profile (raw)"):
        st.json(selected_row["ab_profile"])

    with st.expander("Source Summary (raw)"):
        st.json(selected_row["source_summary"])