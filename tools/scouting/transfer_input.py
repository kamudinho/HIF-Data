import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
import time
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

COMP_MAP = { 
    335: "Superliga", 328: "Betinia Ligaen", 329: "2. division", 
    43319: "3. division", 1305: "U19 Ligaen" 
}

AGE_LIMITS = { 1305: 19, 1306: 17, 1307: 15 }

# Tilføjet TIMESTAMP til kolonneordenen
COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", "PLAYER_OPTAUUID", 
    "COMPETITION_WYID", "COMPETITION_OPTAUUID", "SENESTE_KLUB", 
    "KONTRAKT_START", "KONTRAKT_UDLOEB", "KILDE", "KOMMENTAR", "TIMESTAMP"
]

def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            return base64.b64decode(data['content']).decode('utf-8', errors='replace'), data['sha']
    except: pass
    return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'), "sha": sha}
    return requests.put(url, headers=headers, json=payload).status_code

def rens_id(val):
    return str(val).split('.')[0].strip() if pd.notna(val) and str(val).strip() != "" else ""

def beregn_alder(fodselsdato):
    if not fodselsdato: return None
    try:
        fodt = pd.to_datetime(fodselsdato)
        nu = datetime.now()
        return nu.year - fodt.year - ((nu.month, nu.day) < (fodt.month, fodt.day))
    except: return None

def vis_side():
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"

    csv_content, csv_sha = get_github_file(FILE_PATH)
    df_csv = pd.read_csv(StringIO(csv_content)) if csv_content else pd.DataFrame(columns=COL_ORDER)
    df_csv['PLAYER_WYID'] = df_csv['PLAYER_WYID'].apply(rens_id)
    
    # Sikrer at TIMESTAMP kolonnen eksisterer i den indlæste dataframe
    if "TIMESTAMP" not in df_csv.columns:
        df_csv["TIMESTAMP"] = ""

    col_left, col_right = st.columns([1, 1], gap="large")

    df_alle_hold = conn.query(f"SELECT DISTINCT t.TEAMNAME, t.COMPETITION_WYID FROM {DB}.WYSCOUT_TEAMS t JOIN {DB}.WYSCOUT_SEASONS s ON t.SEASON_WYID = s.SEASON_WYID WHERE s.SEASONNAME = '2025/2026'")

    with col_left:
        st.subheader("Transfer Center")
        
        sql_players_q = f"""
            SELECT DISTINCT p.PLAYER_WYID, p.SHORTNAME AS NAVN, t.TEAMNAME AS KLUB, 
                            p.ROLECODE3 AS POSITION, p.IMAGEDATAURL, p.BIRTHDATE 
            FROM {DB}.WYSCOUT_SEASONS s 
            JOIN {DB}.WYSCOUT_TEAMS t ON t.SEASON_WYID = s.SEASON_WYID 
            JOIN {DB}.WYSCOUT_PLAYERS p ON (p.CURRENTTEAM_WYID = t.TEAM_WYID AND p.SEASON_WYID = s.SEASON_WYID) 
            WHERE s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'
        """
        df_sql_players = conn.query(sql_players_q)
        
        search_options = {}
        if df_sql_players is not None:
            csv_lookup = df_csv.set_index('PLAYER_WYID')['KLUB'].to_dict()
            for _, r in df_sql_players.iterrows():
                p_id = rens_id(r['PLAYER_WYID'])
                aktuel_klub = csv_lookup.get(p_id, r['KLUB'])
                search_options[p_id] = {
                    "label": f"{r['NAVN']} ({aktuel_klub})", 
                    "data": r.to_dict(),
                    "aktuel_klub": aktuel_klub
                }
        
        sel_id = st.selectbox("Søg på spiller...", [""] + sorted(search_options.keys(), key=lambda x: search_options[x]["label"]), 
                            format_func=lambda x: search_options[x]["label"] if x else "Vælg spiller...")

        if sel_id:
            entry = search_options[sel_id]
            p = entry["data"]
            alder = beregn_alder(p['BIRTHDATE'])
            
            c1, c2 = st.columns([0.25, 0.75])
            with c1: st.image(p['IMAGEDATAURL'] if p['IMAGEDATAURL'] else "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png", width=70)
            with c2:
                st.write(f"**{p['NAVN']}**")
                st.caption(f"Nuværende klub: {entry['aktuel_klub']} | Alder: {alder if alder else '?'}")

            with st.form("full_transfer_form", clear_on_submit=True):
                skift_udland = st.checkbox("Skift til udlandet (Fjern fra danske lister)")
                
                hold_liste = sorted(df_alle_hold['TEAMNAME'].tolist()) if df_alle_hold is not None else []
                ny_klub = st.selectbox("Ny klub", hold_liste, disabled=skift_udland)
                
                d1, d2 = st.columns(2)
                k_start = d1.date_input("Kontraktstart", value=datetime.now())
                k_udloeb = d2.date_input("Kontraktudløb", value=None)
                
                kilde = st.text_input("Kilde (Link)")
                kommentar = st.text_area("Kommentar")

                if st.form_submit_button("REGISTRER TRANSFER"):
                    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    if skift_udland:
                        final_klub = "Udlandet"
                        final_liga = 0
                    else:
                        match_liga = df_alle_hold[df_alle_hold['TEAMNAME'] == ny_klub]['COMPETITION_WYID'].values
                        final_klub = ny_klub
                        final_liga = int(match_liga[0]) if len(match_liga) > 0 else 0

                    max_alder = AGE_LIMITS.get(final_liga)
                    if max_alder and alder and alder > max_alder:
                        st.error(f"Spilleren er for gammel ({alder} år) til {COMP_MAP.get(final_liga, 'denne liga')}.")
                    else:
                        ny_data = {
                            "KLUB": final_klub, "NAVN": p['NAVN'], "POSITION": p['POSITION'],
                            "PLAYER_WYID": sel_id, "COMPETITION_WYID": final_liga,
                            "SENESTE_KLUB": entry['aktuel_klub'], 
                            "KONTRAKT_START": k_start.strftime('%Y-%m-%d'),
                            "KONTRAKT_UDLOEB": k_udloeb.strftime('%Y-%m-%d') if k_udloeb else "",
                            "KILDE": kilde, "KOMMENTAR": kommentar,
                            "TIMESTAMP": now_ts # Her gemmes tidsstemplet
                        }
                        df_csv = df_csv[df_csv['PLAYER_WYID'].astype(str) != str(sel_id)]
                        df_csv = pd.concat([df_csv, pd.DataFrame([ny_data])], ignore_index=True)
                        
                        csv_string = df_csv[COL_ORDER].to_csv(index=False)
                        res = push_to_github(FILE_PATH, f"Transfer: {p['NAVN']} -> {final_klub}", csv_string, csv_sha)
                        if res in [200, 201]:
                            st.success("Transfer gennemført")
                            time.sleep(1)
                            st.rerun()

    # --- HØJRE SIDE: TRUPOVERSIGT ---
    with col_right:
        st.subheader("Trupoversigt")
        liga_valg = st.segmented_control("Vælg liga", list(COMP_MAP.values()), default="Betinia Ligaen")
        valgt_liga_id = int([k for k, v in COMP_MAP.items() if v == liga_valg][0])

        if valgt_liga_id == 328:
            hold_i_csv = sorted(df_csv[df_csv['COMPETITION_WYID'] == 328]['KLUB'].unique().tolist())
            valgt_hold = st.selectbox("Vælg hold", hold_i_csv)
            if valgt_hold:
                trup = df_csv[(df_csv['KLUB'] == valgt_hold) & (df_csv['COMPETITION_WYID'] == 328)][['NAVN', 'POSITION', 'PLAYER_WYID']]
                st.table(trup.sort_values(by="NAVN"))
        else:
            sql_q = f"SELECT DISTINCT p.SHORTNAME AS NAVN, p.ROLECODE3 AS POSITION, p.PLAYER_WYID, t.TEAMNAME AS KLUB FROM {DB}.WYSCOUT_TEAMS t JOIN {DB}.WYSCOUT_SEASONS s ON t.SEASON_WYID = s.SEASON_WYID JOIN {DB}.WYSCOUT_PLAYERS p ON (p.CURRENTTEAM_WYID = t.TEAM_WYID AND p.SEASON_WYID = s.SEASON_WYID) WHERE t.COMPETITION_WYID = {valgt_liga_id} AND s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'"
            sql_trup = conn.query(sql_q)
            if sql_trup is not None:
                sql_trup.columns = [c.upper() for c in sql_trup.columns]
                sql_trup['PLAYER_WYID'] = sql_trup['PLAYER_WYID'].apply(rens_id)
                klubber = sorted(sql_trup['KLUB'].unique().tolist())
                v_hold = st.selectbox("Vælg hold", klubber)
                if v_hold:
                    csv_ids = df_csv['PLAYER_WYID'].unique().tolist()
                    sql_f = sql_trup[(sql_trup['KLUB'] == v_hold) & (~sql_trup['PLAYER_WYID'].isin(csv_ids))]
                    csv_f = df_csv[(df_csv['COMPETITION_WYID'] == valgt_liga_id) & (df_csv['KLUB'] == v_hold)]
                    vis_trup = pd.concat([sql_f[['NAVN', 'POSITION', 'PLAYER_WYID']], csv_f[['NAVN', 'POSITION', 'PLAYER_WYID']]], ignore_index=True)
                    st.table(vis_trup.sort_values(by="NAVN"))

if __name__ == "__main__":
    vis_side()
