import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

COMP_MAP = { 
    335: "Superliga", 
    328: "Betinia Ligaen", 
    329: "2. division", 
    43319: "3. division" 
}

COL_ORDER = ["KLUB", "NAVN", "POSITION", "PLAYER_WYID", "PLAYER_OPTAUUID", "COMPETITION_WYID", "COMPETITION_OPTAUUID"]

# --- GITHUB FUNKTIONER ---
def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            return content, data['sha']
    except: pass
    return None, None

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- HOVEDSIDE ---
def vis_side():
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"

    # 1. Hent lokal CSV data
    csv_content, _ = get_github_file(FILE_PATH)
    df_csv = pd.read_csv(StringIO(csv_content)) if csv_content else pd.DataFrame(columns=COL_ORDER)

    col_left, col_right = st.columns([1, 1], gap="large")

    # --- VENSTRE SIDE: SØGNING & TRANSFER ---
    with col_left:
        st.caption("Opdater Spiller/Transfer")
        # Vi henter en liste over alle spillere til søgning (Sæson 25/26)
        search_q = f"""
            SELECT DISTINCT p.PLAYER_WYID, p.SHORTNAME AS NAVN, t.TEAMNAME AS KLUB
            FROM {DB}.WYSCOUT_PLAYERS p
            JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON t.SEASON_WYID = s.SEASON_WYID
            WHERE s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'
        """
        df_search = conn.query(search_q)
        
        # (Søge- og transfer-logik her...)

    # --- HØJRE SIDE: TRUPOVERSIGT (PRÆCIS CURRENT TEAM LOGIK) ---
    with col_right:
        st.caption("Trupoversigt (Sæson 2025/2026)")
        valgt_liga_navn = st.segmented_control("Vælg liga", list(COMP_MAP.values()), default="Superliga")
        valgt_id = int([k for k, v in COMP_MAP.items() if v == valgt_liga_navn][0])

        if valgt_id == 328:
            # Betinia Ligaen fra CSV
            final_df = df_csv.copy()
            final_df['L_ID'] = pd.to_numeric(final_df['COMPETITION_WYID'], errors='coerce')
            final_df = final_df[final_df['L_ID'] == 328].copy()
        else:
            # SQL LOGIK:
            # 1. Start med at finde de hold der er i den valgte liga i 25/26
            # 2. Join KUN de spillere hvis CURRENTTEAM_WYID matcher holdets ID
            query = f"""
                SELECT DISTINCT 
                    p.SHORTNAME AS NAVN, 
                    p.ROLECODE3 AS POSITION, 
                    p.PLAYER_WYID, 
                    t.TEAMNAME AS KLUB
                FROM {DB}.WYSCOUT_TEAMS t
                JOIN {DB}.WYSCOUT_SEASONS s ON t.SEASON_WYID = s.SEASON_WYID
                INNER JOIN {DB}.WYSCOUT_PLAYERS p ON p.CURRENTTEAM_WYID = t.TEAM_WYID
                WHERE t.COMPETITION_WYID = {valgt_id}
                AND s.SEASONNAME = '2025/2026'
                AND p.STATUS = 'active'
            """
            final_df = conn.query(query)

        if final_df is not None and not final_df.empty:
            final_df.columns = [c.upper() for c in final_df.columns]
            hold_liste = sorted(final_df['KLUB'].unique().tolist())
            
            # Dropdown til at vælge holdet
            valgt_hold = st.selectbox(f"Vælg hold ({len(hold_liste)} fundet)", hold_liste, key=f"squad_v6_{valgt_id}")
            
            if valgt_hold:
                # Her viser vi nu kun spillerne for det valgte hold
                trup = final_df[final_df['KLUB'] == valgt_hold].copy()
                vis_tabel = trup[['NAVN', 'POSITION', 'PLAYER_WYID']].sort_values(by='NAVN')
                vis_tabel.columns = ['Spiller', 'Position', 'ID']
                st.table(vis_tabel)
        else:
            st.info("Ingen hold fundet for denne liga i 2025/2026.")

if __name__ == "__main__":
    vis_side()
