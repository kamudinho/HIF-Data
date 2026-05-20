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

COMP_MAP = { 335: "Superliga", 328: "Betinia Ligaen", 329: "2. division", 43319: "3. division" }

# Opdateret kolonne-struktur: KLUB er nu destinationen, SENESTE_KLUB er afsenderen
COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", "PLAYER_OPTAUUID", 
    "COMPETITION_WYID", "COMPETITION_OPTAUUID",
    "SENESTE_KLUB", "KONTRAKT_START", "KONTRAKT_UDLOEB", "KILDE", "KOMMENTAR"
]

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

    # 1. Hent og forbered CSV data fra GitHub
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
        st.subheader("Søg & Registrer Transfer")
        
        # Den gyldne SQL Query der finder aktuelle spillere for 25/26
        search_q = f"""
            SELECT DISTINCT 
                p.PLAYER_WYID, p.SHORTNAME AS NAVN, t.TEAMNAME AS KLUB, 
                p.ROLECODE3 AS POSITION, p.IMAGEDATAURL, 
                p.COMPETITION_WYID, p.PLAYER_OPTAUUID, c.COMPETITION_OPTAUUID
            FROM {DB}.WYSCOUT_COMPETITIONS c
            JOIN {DB}.WYSCOUT_SEASONS s ON c.COMPETITION_WYID = s.COMPETITION_WYID
            JOIN {DB}.WYSCOUT_TEAMS t ON (t.COMPETITION_WYID = c.COMPETITION_WYID AND t.SEASON_WYID = s.SEASON_WYID)
            JOIN {DB}.WYSCOUT_PLAYERS p ON (p.CURRENTTEAM_WYID = t.TEAM_WYID AND p.SEASON_WYID = s.SEASON_WYID)
            WHERE s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'
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

        sel_id = st.selectbox("Søg på spiller...", [""] + sorted(search_options.keys(), key=lambda x: search_options[x]["label"]),
                            format_func=lambda x: search_options[x]["label"] if x else "Indtast navn...")

        if sel_id:
            p = search_options[sel_id]["data"]
            
            # Profil-visning
            c1, c2 = st.columns([1, 2])
            with c1:
                img = p['IMAGEDATAURL'] if p['IMAGEDATAURL'] else "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
                st.image(img, width=120)
            with c2:
                st.markdown(f"### {p['NAVN']}")
                st.write(f"**Nuværende klub:** {p['KLUB']}")
                st.write(f"**Position:** {p['POSITION']}")

            st.divider()

            # Transfer Form
            with st.form("transfer_form"):
                # Seneste klub låses til den nuværende klub fra Snowflake
                st.text_input("Seneste klub (Fra)", value=p['KLUB'], disabled=True)
                
                # Ny klub dropdown
                alle_klubber = sorted(df_sql['KLUB'].unique().tolist()) if df_sql is not None else []
                ny_klub = st.selectbox("Ny klub (Til)", alle_klubber)
                
                c_date1, c_date2 = st.columns(2)
                k_start = c_date1.text_input("Kontraktstart")
                k_udloeb = c_date2.text_input("Kontraktudløb")
                
                kilde = st.text_input("Kilde (Link)")
                kommentar = st.text_area("Kommentar")

                if st.form_submit_button("GEM TRANSFER"):
                    ny_række = {
                        "KLUB": ny_klub, # Destinationen gemmes i den primære KLUB kolonne
                        "NAVN": p['NAVN'],
                        "POSITION": p['POSITION'],
                        "PLAYER_WYID": p['PLAYER_WYID'],
                        "PLAYER_OPTAUUID": p.get('PLAYER_OPTAUUID', ''),
                        "COMPETITION_WYID": p['COMPETITION_WYID'],
                        "COMPETITION_OPTAUUID": p.get('COMPETITION_OPTAUUID', ''),
                        "SENESTE_KLUB": p['KLUB'], # Her gemmer vi historikken
                        "KONTRAKT_START": k_start,
                        "KONTRAKT_UDLOEB": k_udloeb,
                        "KILDE": kilde,
                        "KOMMENTAR": kommentar
                    }
                    
                    # Opdater lokalt og push
                    df_csv = df_csv[df_csv['PLAYER_WYID'].astype(str) != str(sel_id)]
                    df_csv = pd.concat([df_csv, pd.DataFrame([ny_række])], ignore_index=True)
                    
                    csv_output = df_csv[COL_ORDER].to_csv(index=False)
                    status = push_to_github(FILE_PATH, f"Transfer: {p['NAVN']} -> {ny_klub}", csv_output, csv_sha)
                    
                    if status in [200, 201]:
                        st.success(f"✅ Registreret: {p['NAVN']} er skiftet til {ny_klub}")
                        time.sleep(1)
                        st.rerun()

    # --- HØJRE SIDE: TRUPOVERSIGT ---
    with col_right:
        st.subheader("Trupoversigt")
        valgt_liga_navn = st.segmented_control("Vælg liga", list(COMP_MAP.values()), default="Superliga")
        valgt_id = int([k for k, v in COMP_MAP.items() if v == valgt_liga_navn][0])

        # Her bruger vi samme gyldne SQL som i sidste turn
        query = f"""
            SELECT DISTINCT 
                p.SHORTNAME AS NAVN, p.ROLECODE3 AS POSITION, p.PLAYER_WYID, t.TEAMNAME AS KLUB
            FROM {DB}.WYSCOUT_COMPETITIONS c
            JOIN {DB}.WYSCOUT_SEASONS s ON c.COMPETITION_WYID = s.COMPETITION_WYID
            JOIN {DB}.WYSCOUT_TEAMS t ON (t.COMPETITION_WYID = c.COMPETITION_WYID AND t.SEASON_WYID = s.SEASON_WYID)
            JOIN {DB}.WYSCOUT_PLAYERS p ON (p.CURRENTTEAM_WYID = t.TEAM_WYID AND p.SEASON_WYID = s.SEASON_WYID)
            WHERE c.COMPETITION_WYID = {valgt_id} AND s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'
        """
        sql_data = conn.query(query)
        
        # Merge SQL og CSV for at vise de opdaterede trupper
        if sql_data is not None:
            # Vi fjerner spillere fra SQL-truppen hvis de er flyttet i CSV
            sql_data.columns = [c.upper() for c in sql_data.columns]
            # (Yderligere merge-logik kan tilføjes her for at vise transfers i oversigten)
            
            hold_liste = sorted(sql_data['KLUB'].unique().tolist())
            valgt_hold = st.selectbox(f"Vælg hold", hold_liste, key=f"squad_view_{valgt_id}")
            
            if valgt_hold:
                trup = sql_data[sql_data['KLUB'] == valgt_hold].sort_values(by='NAVN')
                st.table(trup[['NAVN', 'POSITION', 'PLAYER_WYID']])

if __name__ == "__main__":
    vis_side()
