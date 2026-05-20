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

# Kolonner i CSV (KLUB = Ny destination, SENESTE_KLUB = Afsender)
COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", "PLAYER_OPTAUUID", 
    "COMPETITION_WYID", "COMPETITION_OPTAUUID",
    "SENESTE_KLUB", "KONTRAKT_START", "KONTRAKT_UDLOEB", "KILDE", "KOMMENTAR"
]

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

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')}
    if sha: payload["sha"] = sha
    res = requests.put(url, headers=headers, json=payload)
    return res.status_code

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- HOVEDSIDE ---
def vis_side():
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"

    # 1. Hent CSV fra GitHub (Overskrivningslisten)
    csv_content, csv_sha = get_github_file(FILE_PATH)
    if csv_content:
        df_csv = pd.read_csv(StringIO(csv_content))
        for col in COL_ORDER:
            if col not in df_csv.columns: df_csv[col] = ""
    else:
        df_csv = pd.DataFrame(columns=COL_ORDER)

    col_left, col_right = st.columns([1, 1], gap="large")

    # --- VENSTRE SIDE: SØG OG TRANSFER FORM ---
    with col_left:
        st.caption("Transfer")
        
        # Den "Gyldne" SQL: Henter kun aktive spillere fra 25/26 sæsonens hold
        search_q = f"""
            SELECT DISTINCT 
                p.PLAYER_WYID, 
                p.SHORTNAME AS NAVN, 
                t.TEAMNAME AS KLUB, 
                p.ROLECODE3 AS POSITION, 
                p.IMAGEDATAURL, 
                p.COMPETITION_WYID
            FROM {DB}.WYSCOUT_COMPETITIONS c
            JOIN {DB}.WYSCOUT_SEASONS s ON c.COMPETITION_WYID = s.COMPETITION_WYID
            JOIN {DB}.WYSCOUT_TEAMS t ON (t.COMPETITION_WYID = c.COMPETITION_WYID AND t.SEASON_WYID = s.SEASON_WYID)
            JOIN {DB}.WYSCOUT_PLAYERS p ON (p.CURRENTTEAM_WYID = t.TEAM_WYID AND p.SEASON_WYID = s.SEASON_WYID)
            WHERE s.SEASONNAME = '2025/2026' 
            AND p.STATUS = 'active'
        """
        df_sql = conn.query(search_q)

        search_options = {}
        if df_sql is not None:
            for _, r in df_sql.iterrows():
                p_id = rens_id(r['PLAYER_WYID'])
                search_options[p_id] = {
                    "label": f"{r['NAVN']} ({r['KLUB']})",
                    "data": r.to_dict()
                }

        sel_id = st.selectbox("Søg på spillernavn...", [""] + sorted(search_options.keys(), key=lambda x: search_options[x]["label"]),
                            format_func=lambda x: search_options[x]["label"] if x else "Indtast navn...")

        if sel_id:
            p = search_options[sel_id]["data"]
            
            # Præsentation af spiller
            c1, c2 = st.columns([1, 2])
            with c1:
                img = p['IMAGEDATAURL'] if p['IMAGEDATAURL'] else "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
                st.image(img, width=80)
            with c2:
                st.write(f"### {p['NAVN']}")
                st.caption(f"**Fra:** {p['KLUB']}")
                st.caption(f"**Position:** {p['POSITION']}")
                st.caption(f"**ID:** {sel_id}")

            st.divider()

            # Form til transfer-data
            with st.form("transfer_form", clear_on_submit=True):
                st.text_input("Afgående klub", value=p['KLUB'], disabled=True)
                
                # Alle aktive hold fra 25/26 databasen
                alle_klubber = sorted(df_sql['KLUB'].unique().tolist()) if df_sql is not None else []
                ny_klub = st.selectbox("Ny klub (Destination)", alle_klubber)
                
                d1, d2 = st.columns(2)
                k_start = d1.text_input("Kontraktstart")
                k_udloeb = d2.text_input("Kontraktudløb")
                
                kilde = st.text_input("Kilde (Link)")
                kommentar = st.text_area("Kommentar")

                if st.form_submit_button("SEND TRANSFER TIL DATABASEN"):
                    ny_række = {
                        "KLUB": ny_klub,
                        "NAVN": p['NAVN'],
                        "POSITION": p['POSITION'],
                        "PLAYER_WYID": sel_id,
                        "PLAYER_OPTAUUID": "", # Snowflake har ikke Opta-ID her
                        "COMPETITION_WYID": p['COMPETITION_WYID'],
                        "COMPETITION_OPTAUUID": "",
                        "SENESTE_KLUB": p['KLUB'],
                        "KONTRAKT_START": k_start,
                        "KONTRAKT_UDLOEB": k_udloeb,
                        "KILDE": kilde,
                        "KOMMENTAR": kommentar
                    }
                    
                    # Opdater data: Fjern gammel post for spilleren, tilføj den nye
                    df_csv = df_csv[df_csv['PLAYER_WYID'].astype(str) != str(sel_id)]
                    df_csv = pd.concat([df_csv, pd.DataFrame([ny_række])], ignore_index=True)
                    
                    csv_string = df_csv[COL_ORDER].to_csv(index=False)
                    res_code = push_to_github(FILE_PATH, f"Transfer: {p['NAVN']} -> {ny_klub}", csv_string, csv_sha)
                    
                    if res_code in [200, 201]:
                        st.success(f"Gemt: {p['NAVN']} er nu i {ny_klub}")
                        time.sleep(1)
                        st.rerun()

    # --- HØJRE SIDE: TRUPOVERSIGT (12 HOLD TJEK) ---
    with col_right:
        st.caption("Trupoversigt (2025/2026)")
        liga_valg = st.segmented_control("Vælg liga", list(COMP_MAP.values()), default="Superliga")
        liga_id = int([k for k, v in COMP_MAP.items() if v == liga_valg][0])

        # Hent truppen direkte via den relationelle kæde
        query = f"""
            SELECT DISTINCT 
                p.SHORTNAME AS NAVN, p.ROLECODE3 AS POSITION, p.PLAYER_WYID, t.TEAMNAME AS KLUB
            FROM {DB}.WYSCOUT_COMPETITIONS c
            JOIN {DB}.WYSCOUT_SEASONS s ON c.COMPETITION_WYID = s.COMPETITION_WYID
            JOIN {DB}.WYSCOUT_TEAMS t ON (t.COMPETITION_WYID = c.COMPETITION_WYID AND t.SEASON_WYID = s.SEASON_WYID)
            JOIN {DB}.WYSCOUT_PLAYERS p ON (p.CURRENTTEAM_WYID = t.TEAM_WYID AND p.SEASON_WYID = s.SEASON_WYID)
            WHERE c.COMPETITION_WYID = {liga_id} AND s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'
        """
        trup_data = conn.query(query)
        
        if trup_data is not None:
            trup_data.columns = [c.upper() for c in trup_data.columns]
            aktuelle_hold = sorted(trup_data['KLUB'].unique().tolist())
            
            valgt_hold = st.selectbox(f"Vælg hold ({len(aktuelle_hold)} fundet)", aktuelle_hold, key=f"v_final_{liga_id}")
            
            if valgt_hold:
                vis_trup = trup_data[trup_data['KLUB'] == valgt_hold].sort_values(by='NAVN')
                # Vis Navn, Position og PLAYER_WYID helt til højre
                st.table(vis_trup[['NAVN', 'POSITION', 'PLAYER_WYID']])
        else:
            st.warning("Kunne ikke hente trup-data.")

if __name__ == "__main__":
    vis_side()
