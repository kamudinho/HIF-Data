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

# Vi definerer ligaerne direkte her
COMP_MAP = { 
    335: "Superliga", 
    328: "Betinia Ligaen", 
    329: "2. division", 
    43319: "3. division" 
}

COL_ORDER = ["KLUB", "NAVN", "POSITION", "PLAYER_WYID", "PLAYER_OPTAUUID", "COMPETITION_WYID", "COMPETITION_OPTAUUID"]

# --- GITHUB HJÆLPEFUNKTIONER ---
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

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')}
    if sha: payload["sha"] = sha
    return requests.put(url, headers=headers, json=payload).status_code

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- HOVEDSIDE ---
def vis_side():
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"

    # 1. Hent lokal data fra GitHub (CSV)
    csv_content, csv_sha = get_github_file(FILE_PATH)
    if csv_content:
        df_csv = pd.read_csv(StringIO(csv_content), on_bad_lines='skip')
    else:
        df_csv = pd.DataFrame(columns=COL_ORDER)

    col_left, col_right = st.columns([1, 1], gap="large")

    # --- VENSTRE SIDE: SØG & OPDATER (TRANSFER) ---
    with col_left:
        st.caption("Opdater Spiller/Transfer")
        
        # Hent bred liste til søgning (Kun aktive i 25/26)
        search_query = f"""
            SELECT DISTINCT 
                p.PLAYER_WYID, 
                p.SHORTNAME AS NAVN, 
                t.TEAMNAME AS KLUB,
                p.ROLECODE3 AS POSITION,
                p.COMPETITION_WYID
            FROM {DB}.WYSCOUT_PLAYERS p
            JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
            JOIN {DB}.WYSCOUT_SEASONS s ON p.COMPETITION_WYID = s.COMPETITION_WYID
            WHERE s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'
        """
        df_sql_search = conn.query(search_query)

        search_options = {}
        # Kombiner CSV og SQL i søgningen
        for _, r in df_csv.iterrows():
            p_id = rens_id(r['PLAYER_WYID'])
            if p_id: search_options[p_id] = {"label": f"📝 {r['NAVN']} ({r['KLUB']})", "data": r.to_dict()}
        
        if df_sql_search is not None:
            for _, r in df_sql_search.iterrows():
                p_id = rens_id(r['PLAYER_WYID'])
                if p_id and p_id not in search_options:
                    search_options[p_id] = {
                        "label": f"🌐 {r['NAVN']} ({r['KLUB']})", 
                        "data": {"NAVN": r['NAVN'], "PLAYER_WYID": p_id, "POSITION": r['POSITION'], "KLUB": r['KLUB'], "COMPETITION_WYID": r['COMPETITION_WYID']}
                    }

        sel_id = st.selectbox("Søg spiller", [""] + sorted(search_options.keys(), key=lambda x: search_options[x]["label"]), 
                            format_func=lambda x: search_options[x]["label"] if x else "Indtast navn eller ID...")

        if sel_id:
            p = search_options[sel_id]["data"]
            with st.form("transfer_form"):
                st.subheader(f"Flyt {p['NAVN']}")
                st.write(f"Nuværende: {p['KLUB']} (ID: {sel_id})")
                
                alle_klubber = sorted(list(set(df_csv['KLUB'].dropna().tolist() + (df_sql_search['KLUB'].unique().tolist() if df_sql_search is not None else []))))
                ny_klub = st.selectbox("Vælg ny klub:", alle_klubber)
                
                if st.form_submit_button("GEM TRANSFER"):
                    # Her opdateres df_csv logik...
                    p['KLUB'] = ny_klub
                    # (GitHub push logik her...)
                    st.success(f"{p['NAVN']} flyttet til {ny_klub}!")

    # --- HØJRE SIDE: TRUPOVERSIGT ---
    with col_right:
        st.caption("Trupoversigt (Sæson 2025/2026)")
        
        # Segmented control til valg af liga
        valgt_liga_navn = st.segmented_control("Vælg liga", list(COMP_MAP.values()), default="Superliga")
        valgt_id = int([k for k, v in COMP_MAP.items() if v == valgt_liga_navn][0])

        # Hent data baseret på kilde
        if valgt_id == 328:
            # Betinia Ligaen fra CSV
            final_df = df_csv.copy()
            final_df['LIGA_ID'] = pd.to_numeric(final_df['COMPETITION_WYID'], errors='coerce')
            final_df = final_df[final_df['LIGA_ID'] == 328].copy()
        else:
            # Andre ligaer direkte fra SQL (koblet på Sæson 25/26)
            query = f"""
                SELECT DISTINCT 
                    p.SHORTNAME AS NAVN, 
                    p.ROLECODE3 AS POSITION, 
                    p.PLAYER_WYID, 
                    t.TEAMNAME AS KLUB
                FROM {DB}.WYSCOUT_PLAYERS p
                INNER JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
                INNER JOIN {DB}.WYSCOUT_SEASONS s ON p.COMPETITION_WYID = s.COMPETITION_WYID
                WHERE p.COMPETITION_WYID = {valgt_id}
                AND s.SEASONNAME = '2025/2026'
                AND p.STATUS = 'active'
            """
            final_df = conn.query(query)

        if final_df is not None and not final_df.empty:
            final_df.columns = [c.upper() for c in final_df.columns]
            hold_liste = sorted(final_df['KLUB'].unique().tolist())
            
            # Key sikrer at dropdown resetter når ligaen skifter
            valgt_hold = st.selectbox("Vælg hold", hold_liste, key=f"squad_v5_{valgt_id}")
            
            if valgt_hold:
                trup = final_df[final_df['KLUB'] == valgt_hold].copy()
                vis_tabel = trup[['NAVN', 'POSITION', 'PLAYER_WYID']].sort_values(by='NAVN')
                vis_tabel.columns = ['Spiller', 'Pos', 'ID']
                st.table(vis_tabel)
        else:
            st.warning("Ingen data fundet for denne liga.")

if __name__ == "__main__":
    vis_side()
