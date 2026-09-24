#data/sql/fallback.py
"""
Fælles fallback-logik for kampdata (data/csv/kampe_fallback.csv).

Reglen alle sider skal følge: fallback-CSV'en UDFYLDER KUN manglende (NaN)
værdier i liveresultater fra Snowflake - den overskriver aldrig værdier der
allerede kom fra Snowflake, og den erstatter aldrig HELE resultatet. Det kræver
at den underliggende SQL rent faktisk lader manglende stats stå som NULL/NaN
(ikke COALESCE'r dem til 0 for tidligt) - ellers er der ingen huller at fylde.

Der findes to varianter, fordi siderne har to forskellige tabel-layouts:
- fill_gaps_side_aware: én række pr. kamp med separate HOME_-/AWAY_-kolonner
  (bruges af teams.py's hent_hoved_stats).
- fill_gaps_team_row: én række pr. hold pr. kamp (bruges af kampe.py's
  load_match_level_data).
"""
import os
import pandas as pd
import streamlit as st

FALLBACK_FILE = "data/csv/kampe_fallback.csv"


def _load_fallback(fallback_file: str = FALLBACK_FILE):
    if not os.path.exists(fallback_file):
        return None
    try:
        fb = pd.read_csv(fallback_file)
        fb.columns = [str(c).upper() for c in fb.columns]
        return fb
    except Exception as e:
        st.warning(f"Kunne ikke indlæse {fallback_file}: {e}")
        return None


def fill_gaps_side_aware(df: pd.DataFrame, col_mapping: dict,
                          match_col: str = "MATCH_OPTAUUID",
                          home_uuid_col: str = "CONTESTANTHOME_OPTAUUID",
                          away_uuid_col: str = "CONTESTANTAWAY_OPTAUUID",
                          fallback_file: str = FALLBACK_FILE) -> pd.DataFrame:
    """
    Til dataframes med ÉN række pr. kamp og separate HOME_-/AWAY_-kolonner.

    col_mapping: {CSV_KOLONNE: KOLONNE_STAMME}, fx {"POSSESSIONPERCENTAGE": "POSSESSION"}
    udfylder HOME_POSSESSION eller AWAY_POSSESSION, afhængig af om CSV-rækkens
    TEAM_OPTAUUID matcher home_uuid_col eller away_uuid_col for den pågældende kamp.
    """
    if df is None or df.empty:
        return df
    fb = _load_fallback(fallback_file)
    if fb is None or "MATCH_OPTAUUID" not in fb.columns:
        return df

    df = df.copy()
    for _, fb_row in fb.iterrows():
        match_uuid = str(fb_row["MATCH_OPTAUUID"]).strip()
        mask = df[match_col].astype(str).str.strip() == match_uuid
        if not mask.any():
            continue

        team_uuid = fb_row.get("TEAM_OPTAUUID")
        if pd.isna(team_uuid):
            continue
        team_uuid = str(team_uuid).strip()

        h_id = str(df.loc[mask, home_uuid_col].values[0]).strip()
        a_id = str(df.loc[mask, away_uuid_col].values[0]).strip()

        if team_uuid == h_id:
            prefix = "HOME_"
        elif team_uuid == a_id:
            prefix = "AWAY_"
        else:
            continue

        for csv_col, col_stem in col_mapping.items():
            df_col = f"{prefix}{col_stem}"
            if csv_col not in fb_row or df_col not in df.columns:
                continue
            val = fb_row[csv_col]
            if pd.isna(val):
                continue
            still_missing = mask & df[df_col].isna()
            if still_missing.any():
                df.loc[still_missing, df_col] = pd.to_numeric(val, errors="coerce")

    return df


def fill_gaps_team_row(df: pd.DataFrame, col_mapping: dict,
                        match_col: str = "MATCH_OPTAUUID",
                        team_col: str = "TEAM_OPTAUUID",
                        fallback_file: str = FALLBACK_FILE) -> pd.DataFrame:
    """
    Til dataframes med ÉN række pr. hold pr. kamp (allerede filtreret til ét hold).

    col_mapping: {CSV_KOLONNE: DF_KOLONNE} - direkte 1:1, ingen hjemme/ude-logik.
    """
    if df is None or df.empty:
        return df
    fb = _load_fallback(fallback_file)
    if fb is None or "MATCH_OPTAUUID" not in fb.columns:
        return df

    df = df.copy()
    for _, fb_row in fb.iterrows():
        match_uuid = str(fb_row["MATCH_OPTAUUID"]).strip()
        mask = df[match_col].astype(str).str.strip() == match_uuid

        if team_col in df.columns and "TEAM_OPTAUUID" in fb_row:
            fb_team = fb_row.get("TEAM_OPTAUUID")
            if pd.notna(fb_team):
                mask = mask & (df[team_col].astype(str).str.strip() == str(fb_team).strip())

        if not mask.any():
            continue

        for csv_col, df_col in col_mapping.items():
            if csv_col not in fb_row or df_col not in df.columns:
                continue
            val = fb_row[csv_col]
            if pd.isna(val):
                continue
            still_missing = mask & df[df_col].isna()
            if still_missing.any():
                df.loc[still_missing, df_col] = pd.to_numeric(val, errors="coerce")

    return df
