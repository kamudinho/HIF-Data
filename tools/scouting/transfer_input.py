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

def vis_side():
    # 1. FORBINDELSER & DATA
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"

    # Hent lokal CSV
    csv_content, csv_sha = get_github_file(FILE_PATH)
    df_csv = pd.read_csv(StringIO(csv_content)) if csv_content else pd.DataFrame(columns=COL_ORDER)

    # 2. HENT SQL DATA TIL SØGNING (Kun aktive spillere 25/26)
    # Vi henter en bred liste her til venstre side
    search_query = f"""
        SELECT DISTINCT 
            p.PLAYER_WYID, 
            p.SHORTNAME AS NAVN, 
            p.ROLECODE3 AS POSITION, 
            t.TEAMNAME AS KLUB,
            p.COMPETITION_WYID
        FROM {DB}.WYSCOUT_PLAYERS p
        JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
        JOIN {DB}.WYSCOUT_SEASONS s ON p.COMPETITION_WYID = s.COMPETITION_WYID
        WHERE s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'
    """
    df_sql_search = conn.query(search_query)

    col_left, col_right = st.columns([1, 1], gap="large")

    # --- VENSTRE SIDE: SØG & OPDATER (TRANSFER) ---
    with col_left:
        st.caption("Opdater Spiller/Transfer")
        search_options = {}

        # Tilføj fra CSV
        for _, r in df_csv.iterrows():
            p_id = rens_id(r['PLAYER_WYID'])
            if p_id:
                search_options[p_id] = {"label": f"📝 {r['NAVN']} ({r['KLUB']})", "data": r.to_dict()}
        
        # Tilføj fra SQL Search
        if df_sql_search is not None:
            for _, r in df_sql_search.iterrows():
                p_id = rens_id(r['PLAYER_WYID'])
                if p_id and p_id not in search_options:
                    search_options[p_id] = {
                        "label": f"🌐 {r['NAVN']} ({r['KLUB']})", 
                        "data": {"NAVN": r['NAVN'], "PLAYER_WYID": p_id, "POSITION": r['POSITION'], "KLUB": r['KLUB'], "COMPETITION_WYID": r['COMPETITION_WYID']}
                    }

        sel_id = st.selectbox("Søg spiller", [""] + sorted(search_options.keys(), key=lambda x: search_options[x]["label"]), 
                            format_func=lambda x: search_options[x]["label"] if x else "Indtast navn...")

        if sel_id:
            p = search_options[sel_id]["data"]
            with st.form("edit_form"):
                st.write(f"Valgt spiller: **{p['NAVN']}** (ID: {sel_id})")
                
                # Liste over alle klubber i systemet til transfer
                alle_klubber = sorted(list(set(df_csv['KLUB'].dropna().tolist() + (df_sql_search['KLUB'].unique().tolist() if df_sql_search is not None else []))))
                ny_klub = st.selectbox("Flyt spiller til:", ["--- UÆNDRET ---"] + alle_klubber)
                
                if st.form_submit_button("GEM ÆNDRING"):
                    # Her indsætter du din eksisterende logik til at pushe til GitHub
                    st.success(f"Gemmer transfer for {p['NAVN']}...")

    # --- HØJRE SIDE: TRUPOVERSIGT ---
    with col_right:
        st.caption("Trupoversigt (2025/2026)")
        liga_navne = list(COMP_MAP.values())
        valgt_liga_navn = st.segmented_control("Vælg liga", liga_navne, default="Superliga")
        valgt_id = str([k for k, v in COMP_MAP.items() if v == valgt_liga_navn][0])

        if valgt_id == "328":
            # Betinia / 1. div fra CSV
            kilde_df = df_csv.copy()
            kilde_df['LIGA_ID'] = kilde_df['COMPETITION_WYID'].astype(str).str.split('.').str[0]
            final_df = kilde_df[kilde_df['LIGA_ID'] == "328"].copy()
        else:
            # Andre ligaer direkte fra Snowflake (kun for den valgte liga)
            liga_query = f"""
                SELECT DISTINCT p.SHORTNAME AS NAVN, p.ROLECODE3 AS POSITION, p.PLAYER_WYID, t.TEAMNAME AS KLUB
                FROM {DB}.WYSCOUT_PLAYERS p
                JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
                JOIN {DB}.WYSCOUT_SEASONS s ON p.COMPETITION_WYID = s.COMPETITION_WYID
                WHERE p.COMPETITION_WYID = {valgt_id}
                AND s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'
            """
            final_df = conn.query(liga_query)

        if final_df is not None and not final_df.empty:
            final_df.columns = [c.upper() for c in final_df.columns]
            hold_liste = sorted(final_df['KLUB'].unique().tolist())
            valgt_hold = st.selectbox("Vælg hold", hold_liste, key=f"squad_{valgt_id}")
            
            if valgt_hold:
                trup = final_df[final_df['KLUB'] == valgt_hold].copy()
                st.table(trup[['NAVN', 'POSITION', 'PLAYER_WYID']].sort_values(by='NAVN').rename(columns={'NAVN': 'Spiller', 'POSITION': 'Pos', 'PLAYER_WYID': 'ID'}))
        else:
            st.info("Ingen data fundet.")

if __name__ == "__main__":
    vis_side()
