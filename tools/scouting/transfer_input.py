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
    335: "Superliga", 
    328: "Betinia Ligaen", 
    329: "2. division", 
    43319: "3. division",
    1305: "U19 Ligaen",
    1306: "U17 Ligaen",
    1307: "U15 Ligaen"
}

AGE_LIMITS = { 1305: 19, 1306: 17, 1307: 15 }

COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", "PLAYER_OPTAUUID", 
    "COMPETITION_WYID", "COMPETITION_OPTAUUID",
    "SENESTE_KLUB", "KONTRAKT_START", "KONTRAKT_UDLOEB", "KILDE", "KOMMENTAR"
]

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

def beregn_alder(fodselsdato):
    if not fodselsdato: return None
    try:
        fodt = pd.to_datetime(fodselsdato)
        nu = datetime.now()
        return nu.year - fodt.year - ((nu.month, nu.day) < (fodt.month, fodt.day))
    except: return None

# --- HOVEDSIDE ---
def vis_side():
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"

    csv_content, csv_sha = get_github_file(FILE_PATH)
    if csv_content:
        df_csv = pd.read_csv(StringIO(csv_content))
        df_csv['PLAYER_WYID'] = df_csv['PLAYER_WYID'].apply(rens_id)
        if 'COMPETITION_WYID' in df_csv.columns:
            df_csv['COMPETITION_WYID'] = pd.to_numeric(df_csv['COMPETITION_WYID'], errors='coerce')
    else:
        df_csv = pd.DataFrame(columns=COL_ORDER)

    col_left, col_right = st.columns([1, 1], gap="large")

    # Hent ALLE hold til dropdown
    alle_hold_q = f"SELECT DISTINCT t.TEAMNAME, t.COMPETITION_WYID FROM {DB}.WYSCOUT_TEAMS t JOIN {DB}.WYSCOUT_SEASONS s ON t.SEASON_WYID = s.SEASON_WYID WHERE s.SEASONNAME = '2025/2026'"
    df_alle_hold = conn.query(alle_hold_q)
    
    with col_left:
        st.caption("Transfer")
        search_q = f"SELECT DISTINCT p.PLAYER_WYID, p.SHORTNAME AS NAVN, t.TEAMNAME AS KLUB, p.ROLECODE3 AS POSITION, p.IMAGEDATAURL, p.BIRTHDATE FROM {DB}.WYSCOUT_SEASONS s JOIN {DB}.WYSCOUT_TEAMS t ON t.SEASON_WYID = s.SEASON_WYID JOIN {DB}.WYSCOUT_PLAYERS p ON (p.CURRENTTEAM_WYID = t.TEAM_WYID AND p.SEASON_WYID = s.SEASON_WYID) WHERE s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'"
        df_sql_players = conn.query(search_q)

        search_options = {rens_id(r['PLAYER_WYID']): {"label": f"{r['NAVN']} ({r['KLUB']})", "data": r.to_dict()} for _, r in df_sql_players.iterrows()} if df_sql_players is not None else {}
        sel_id = st.selectbox("Søg på spiller...", [""] + sorted(search_options.keys(), key=lambda x: search_options[x]["label"]), format_func=lambda x: search_options[x]["label"] if x else "Vælg spiller...")

        if sel_id:
            p = search_options[sel_id]["data"]
            alder = beregn_alder(p['BIRTHDATE'])
            c1, c2 = st.columns([0.25, 0.75]); c1.image(p['IMAGEDATAURL'] if p['IMAGEDATAURL'] else "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png", width=65)
            c2.write(f"**{p['NAVN']}** ({alder} år)"); c2.caption(f"Fra: {p['KLUB']}")

            with st.form("transfer_form", clear_on_submit=True):
                hold_liste = sorted(df_alle_hold['TEAMNAME'].tolist()) if df_alle_hold is not None else []
                ny_klub = st.selectbox("Vælg ny klub", hold_liste)
                d1, d2 = st.columns(2); k_start = d1.date_input("Start", value=datetime.now()); k_udloeb = d2.date_input("Udløb", value=None)
                kilde = st.text_input("Kilde"); kommentar = st.text_area("Kommentar")

                if st.form_submit_button("SEND TRANSFER"):
                    match_liga = df_alle_hold[df_alle_hold['TEAMNAME'] == ny_klub]['COMPETITION_WYID'].values
                    ny_liga_id = int(match_liga[0]) if len(match_liga) > 0 else 0
                    max_alder = AGE_LIMITS.get(ny_liga_id)
                    if max_alder and alder and alder > max_alder:
                        st.error(f"⚠️ Spilleren er for gammel til denne liga.")
                    else:
                        ny_række = {"KLUB": ny_klub, "NAVN": p['NAVN'], "POSITION": p['POSITION'], "PLAYER_WYID": sel_id, "COMPETITION_WYID": ny_liga_id, "SENESTE_KLUB": p['KLUB'], "KONTRAKT_START": k_start.strftime('%Y-%m-%d'), "KONTRAKT_UDLOEB": k_udloeb.strftime('%Y-%m-%d') if k_udloeb else "", "KILDE": kilde, "KOMMENTAR": kommentar}
                        df_csv = df_csv[df_csv['PLAYER_WYID'].astype(str) != str(sel_id)]
                        df_csv = pd.concat([df_csv, pd.DataFrame([ny_række])], ignore_index=True)
                        push_to_github(FILE_PATH, f"Transfer: {p['NAVN']}", df_csv[COL_ORDER].to_csv(index=False), csv_sha)
                        st.success("Gemt!"); time.sleep(1); st.rerun()

    # --- HØJRE SIDE: TRUPOVERSIGT ---
    with col_right:
        liga_valg = st.segmented_control("Vælg liga", list(COMP_MAP.values()), default="Betinia Ligaen")
        valgt_liga_id = int([k for k, v in COMP_MAP.items() if v == liga_valg][0])

        if valgt_liga_id == 328:
            # DEN ENDELIGE SANDHED: Brug kun CSV for 328
            alle_hold_i_liga = sorted(df_csv[df_csv['COMPETITION_WYID'] == 328]['KLUB'].unique().tolist())
            valgt_hold = st.selectbox("Vælg hold (KUN FRA CSV)", alle_hold_i_liga)
            if valgt_hold:
                final_trup = df_csv[(df_csv['KLUB'] == valgt_hold) & (df_csv['COMPETITION_WYID'] == 328)][['NAVN', 'POSITION', 'PLAYER_WYID']].sort_values(by='NAVN')
                st.table(final_trup)
        else:
            # Standard visning for andre ligaer (Snowflake + CSV overlap)
            sql_q = f"SELECT DISTINCT p.SHORTNAME AS NAVN, p.ROLECODE3 AS POSITION, p.PLAYER_WYID, t.TEAMNAME AS KLUB FROM {DB}.WYSCOUT_TEAMS t JOIN {DB}.WYSCOUT_SEASONS s ON t.SEASON_WYID = s.SEASON_WYID JOIN {DB}.WYSCOUT_PLAYERS p ON (p.CURRENTTEAM_WYID = t.TEAM_WYID AND p.SEASON_WYID = s.SEASON_WYID) WHERE t.COMPETITION_WYID = {valgt_liga_id} AND s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'"
            sql_trup = conn.query(sql_q)
            if sql_trup is not None:
                sql_trup.columns = [c.upper() for c in sql_trup.columns]
                sql_trup['PLAYER_WYID'] = sql_trup['PLAYER_WYID'].apply(rens_id)
                alle_hold_i_liga = sorted(sql_trup['KLUB'].unique().tolist())
                valgt_hold = st.selectbox("Vælg hold", alle_hold_i_liga)
                if valgt_hold:
                    csv_ids = df_csv['PLAYER_WYID'].unique().tolist()
                    sql_filt = sql_trup[(sql_trup['KLUB'] == valgt_hold) & (~sql_trup['PLAYER_WYID'].isin(csv_ids))]
                    csv_filt = df_csv[(df_csv['COMPETITION_WYID'] == valgt_liga_id) & (df_csv['KLUB'].apply(lambda x: str(x).lower() in valgt_hold.lower() or valgt_hold.lower() in str(x).lower()))]
                    final_trup = pd.concat([sql_filt[['NAVN', 'POSITION', 'PLAYER_WYID']], csv_filt[['NAVN', 'POSITION', 'PLAYER_WYID']]], ignore_index=True).sort_values(by='NAVN')
                    st.table(final_trup)

if __name__ == "__main__":
    vis_side()
