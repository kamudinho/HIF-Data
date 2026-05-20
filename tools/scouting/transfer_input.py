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

    # Hent CSV til 1. division (328)
    csv_content, _ = get_github_file(FILE_PATH)
    df_csv = pd.read_csv(StringIO(csv_content)) if csv_content else pd.DataFrame(columns=COL_ORDER)

    col_left, col_right = st.columns([1, 1], gap="large")

    # --- VENSTRE SIDE: SØG & TRANSFER ---
    with col_left:
        st.caption("Opdater Spiller/Transfer")
        
        # SQL-søgning (Bred, kun 25/26 aktive)
        search_q = f"""
            SELECT DISTINCT p.PLAYER_WYID, p.SHORTNAME AS NAVN, t.TEAMNAME AS KLUB, p.ROLECODE3 AS POSITION
            FROM {DB}.WYSCOUT_PLAYERS p
            JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON p.COMPETITION_WYID = s.COMPETITION_WYID
            WHERE s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'
        """
        df_search = conn.query(search_q)
        
        search_options = {}
        for _, r in df_csv.iterrows():
            p_id = rens_id(r['PLAYER_WYID'])
            if p_id: search_options[p_id] = {"label": f"📝 {r['NAVN']} ({r['KLUB']})", "data": r.to_dict()}
        if df_search is not None:
            for _, r in df_search.iterrows():
                p_id = rens_id(r['PLAYER_WYID'])
                if p_id and p_id not in search_options:
                    search_options[p_id] = {"label": f"🌐 {r['NAVN']} ({r['KLUB']})", "data": r.to_dict()}

        sel_id = st.selectbox("Søg spiller", [""] + sorted(search_options.keys(), key=lambda x: search_options[x]["label"]),
                            format_func=lambda x: search_options[x]["label"] if x else "Vælg spiller...")
        
        if sel_id:
            st.info(f"Valgt: {search_options[sel_id]['label']}")
            # Form-logik her...

    # --- HØJRE SIDE: TRUPOVERSIGT (12 HOLD LOGIK) ---
    with col_right:
        st.caption("Trupoversigt (Kun 2025/2026 hold)")
        valgt_liga_navn = st.segmented_control("Vælg liga", list(COMP_MAP.values()), default="Superliga")
        valgt_id = int([k for k, v in COMP_MAP.items() if v == valgt_liga_navn][0])

        if valgt_id == 328:
            final_df = df_csv.copy()
            final_df['L_ID'] = pd.to_numeric(final_df['COMPETITION_WYID'], errors='coerce')
            final_df = final_df[final_df['L_ID'] == 328].copy()
        else:
            # DEN NYE QUERY:
            # 1. Vi finder kun de hold der har en aktiv relation til den valgte liga i denne sæson.
            # 2. Vi Joiner spillere på de specifikke hold.
            query = f"""
                WITH CurrentTeams AS (
                    SELECT DISTINCT t.TEAM_WYID, t.TEAMNAME
                    FROM {DB}.WYSCOUT_TEAMS t
                    JOIN {DB}.WYSCOUT_SEASONS s ON t.COMPETITION_WYID = s.COMPETITION_WYID
                    WHERE t.COMPETITION_WYID = {valgt_id}
                    AND s.SEASONNAME = '2025/2026'
                )
                SELECT DISTINCT 
                    p.SHORTNAME AS NAVN, 
                    p.ROLECODE3 AS POSITION, 
                    p.PLAYER_WYID, 
                    ct.TEAMNAME AS KLUB
                FROM {DB}.WYSCOUT_PLAYERS p
                INNER JOIN CurrentTeams ct ON p.CURRENTTEAM_WYID = ct.TEAM_WYID
                WHERE p.COMPETITION_WYID = {valgt_id}
                AND p.STATUS = 'active'
            """
            final_df = conn.query(query)

        if final_df is not None and not final_df.empty:
            final_df.columns = [c.upper() for c in final_df.columns]
            # Her får du nu kun de 12 hold (eller hvor mange der er i s_f)
            hold_liste = sorted(final_df['KLUB'].unique().tolist())
            
            valgt_hold = st.selectbox("Vælg hold", hold_liste, key=f"squad_select_{valgt_id}")
            
            if valgt_hold:
                trup = final_df[final_df['KLUB'] == valgt_hold].copy()
                st.table(trup[['NAVN', 'POSITION', 'PLAYER_WYID']].sort_values(by='NAVN'))
        else:
            st.warning("Ingen hold fundet.")

if __name__ == "__main__":
    vis_side()
