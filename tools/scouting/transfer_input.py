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
    328: "Betinia Liga", 
    329: "2. div", 
    43319: "3. div", 
    1305: "U19 Liga"
}

AGE_LIMITS = { 1305: 19 }

COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", "PLAYER_OPTAUUID", 
    "COMPETITION_WYID", "COMPETITION_OPTAUUID", "SENESTE_KLUB", 
    "KONTRAKT_START", "KONTRAKT_UDLOEB", "KILDE", "KOMMENTAR", "TIMESTAMP", "UDLANDET"
]

# --- HJÆLPEFUNKTIONER ---
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

# --- HOVEDSIDE ---
def vis_side():
    from data.data_load import _get_snowflake_conn
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"

    csv_content, csv_sha = get_github_file(FILE_PATH)
    df_csv = pd.read_csv(StringIO(csv_content)) if csv_content else pd.DataFrame(columns=COL_ORDER)
    df_csv['PLAYER_WYID'] = df_csv['PLAYER_WYID'].apply(rens_id)
    
    for col in ["TIMESTAMP", "UDLANDET"]:
        if col not in df_csv.columns: df_csv[col] = ""

    col_left, col_right = st.columns([1, 1], gap="large")

    df_alle_hold = conn.query(f"SELECT DISTINCT t.TEAMNAME, t.COMPETITION_WYID FROM {DB}.WYSCOUT_TEAMS t JOIN {DB}.WYSCOUT_SEASONS s ON t.SEASON_WYID = s.SEASON_WYID WHERE s.SEASONNAME = '2025/2026'")

    # --- VENSTRE SIDE: TRANSFER CENTER ---
    with col_left:
        st.caption("Transfers")
        
        # Hent spillere fra SQL
        sql_players_q = f"""
            SELECT DISTINCT p.PLAYER_WYID, 
                   CONCAT(p.FIRSTNAME, ' ', p.LASTNAME) AS NAVN, 
                   t.TEAMNAME AS KLUB, p.ROLECODE3 AS POSITION, 
                   p.IMAGEDATAURL, p.BIRTHDATE 
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
                search_options[p_id] = {"label": f"{r['NAVN']} ({aktuel_klub})", "data": r.to_dict(), "aktuel_klub": aktuel_klub}
        
        sel_id = st.selectbox("Søg på spiller...", [""] + sorted(search_options.keys(), key=lambda x: search_options[x]["label"]), format_func=lambda x: search_options[x]["label"] if x else "Vælg spiller...")

        # Vis kun billede og info hvis spiller er valgt - ellers intet (fjernet st.info)
        if sel_id:
            entry = search_options[sel_id]
            p = entry["data"]; alder = beregn_alder(p['BIRTHDATE'])
            c1, c2 = st.columns([0.25, 0.75])
            with c1: st.image(p['IMAGEDATAURL'] if p['IMAGEDATAURL'] else "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png", width=70)
            with c2:
                st.write(f"**{p['NAVN']}**")
                st.caption(f"Nuværende: {entry['aktuel_klub']} | Alder: {alder if alder else '?'}")

        # FORMULAREN VISES ALTID
        with st.form("full_transfer_form", clear_on_submit=True):
            is_disabled = not sel_id
            
            # --- NYT: Checkbokse på samme linje ---
            c1, c2 = st.columns(2)
            skift_udland = c1.checkbox("Skifter til udlandet", disabled=is_disabled)
            skift_klubloes = c2.checkbox("Ukendt", disabled=is_disabled)
            
            hold_liste = sorted(df_alle_hold['TEAMNAME'].tolist()) if df_alle_hold is not None else []
            ny_klub = st.selectbox("Ny klub", hold_liste, disabled=(is_disabled or skift_udland or skift_klubloes))
            
            d1, d2 = st.columns(2)
            k_start = d1.date_input("Kontraktstart", value=datetime.now(), disabled=is_disabled)
            k_udloeb = d2.date_input("Kontraktudløb", value=None, disabled=is_disabled)
            
            kilde = st.text_input("Kilde (Link)", disabled=is_disabled)
            kommentar = st.text_area("Kommentar", disabled=is_disabled)

            submit = st.form_submit_button("REGISTRER TRANSFER", disabled=is_disabled)

            if submit and sel_id:
                now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                entry = search_options[sel_id]
                p = entry["data"]
                
                if skift_udland:
                    final_klub = "Udlandet"; final_liga = 0; is_udland = "True"
                elif skift_klubloes: # NY LOGIK
                    final_klub = "Klubløs"; final_liga = 0; is_udland = "False"
                else:
                    match_liga = df_alle_hold[df_alle_hold['TEAMNAME'] == ny_klub]['COMPETITION_WYID'].values
                    final_klub = ny_klub
                    final_liga = int(match_liga[0]) if len(match_liga) > 0 else 0
                    is_udland = "False"

                ny_data = {
                    "KLUB": final_klub, "NAVN": p['NAVN'], "POSITION": p['POSITION'],
                    "PLAYER_WYID": sel_id, "COMPETITION_WYID": final_liga,
                    "SENESTE_KLUB": entry['aktuel_klub'], "KONTRAKT_START": k_start.strftime('%Y-%m-%d'),
                    "KONTRAKT_UDLOEB": k_udloeb.strftime('%Y-%m-%d') if k_udloeb else "",
                    "KILDE": kilde, "KOMMENTAR": kommentar, 
                    "TIMESTAMP": now_ts, "UDLANDET": is_udland
                }
                
                df_csv = df_csv[df_csv['PLAYER_WYID'].astype(str) != str(sel_id)]
                df_csv = pd.concat([df_csv, pd.DataFrame([ny_data])], ignore_index=True)
                push_to_github(FILE_PATH, f"Transfer: {p['NAVN']}", df_csv[COL_ORDER].to_csv(index=False), csv_sha)
                st.success(f"Transfer registreret for {p['NAVN']}")
                time.sleep(1)
                st.rerun()

    with col_right:
        st.caption("Holdlister")
        
        # Saml dem under "Andet"
        faner = list(COMP_MAP.values()) + ["Øvrige"] 
        liga_valg = st.segmented_control("Vælg liga", faner, default="Betinia Liga")

        if liga_valg == "Øvrige":
            st.caption("###### Øvrige")
            
            # Filtrer for spillere der enten er i udlandet ELLER er klubløse
            trup_andet = df_csv[(df_csv['KLUB'] == "Klubløs") | (df_csv['UDLANDET'].astype(str) == "True")].copy()
            
            if not trup_andet.empty:
                # Opret den kombinerede status-tekst (Udlandet/Klubløs)
                trup_andet['STATUS_TEXT'] = trup_andet.apply(
                    lambda x: "Udlandet" if str(x['UDLANDET']) == "True" else x['KLUB'], axis=1
                )
                
                # Opret din ønskede overgangs-kolonne
                trup_andet['Skifte'] = (
                    trup_andet['SENESTE_KLUB'].fillna('?') + " ➔ " + trup_andet['STATUS_TEXT']
                )
                
                # Vælg og omdøb kolonner - PLAYER_WYID er nu rykket frem
                vis_trup = trup_andet[['NAVN', 'POSITION', 'PLAYER_WYID', 'Skifte']].sort_values(by="NAVN")
                
                # Vis tabellen
                st.dataframe(vis_trup, hide_index=True, use_container_width=True)
            else:
                st.info("Ingen spillere registreret i 'Øvrige' kategorien.")
            
            trup_udland = df_csv[df_csv['UDLANDET'].astype(str) == "True"][['NAVN', 'POSITION', 'PLAYER_WYID', 'SENESTE_KLUB', 'TIMESTAMP']]
            
        elif liga_valg == "Betinia Ligaen":
            df_csv_vis = df_csv[df_csv['UDLANDET'].astype(str) != "True"]
            hold_i_csv = sorted(df_csv_vis[df_csv_vis['COMPETITION_WYID'] == 328]['KLUB'].unique().tolist())
            valgt_hold = st.selectbox("Vælg hold", hold_i_csv)
            if valgt_hold:
                trup = df_csv_vis[(df_csv_vis['KLUB'] == valgt_hold) & (df_csv_vis['COMPETITION_WYID'] == 328)][['NAVN', 'POSITION', 'PLAYER_WYID']]
                # hide_index=True fjerner de grå numre
                st.dataframe(trup.sort_values(by="NAVN"), hide_index=True, use_container_width=True)

        else:
            valgt_liga_id = int([k for k, v in COMP_MAP.items() if v == liga_valg][0])
            df_csv_vis = df_csv[df_csv['UDLANDET'].astype(str) != "True"]
            
            sql_q = f"""
                SELECT DISTINCT CONCAT(p.FIRSTNAME, ' ', p.LASTNAME) AS NAVN, 
                       p.ROLECODE3 AS POSITION, p.PLAYER_WYID, t.TEAMNAME AS KLUB 
                FROM {DB}.WYSCOUT_TEAMS t 
                JOIN {DB}.WYSCOUT_SEASONS s ON t.SEASON_WYID = s.SEASON_WYID 
                JOIN {DB}.WYSCOUT_PLAYERS p ON (p.CURRENTTEAM_WYID = t.TEAM_WYID AND p.SEASON_WYID = s.SEASON_WYID) 
                WHERE t.COMPETITION_WYID = {valgt_liga_id} AND s.SEASONNAME = '2025/2026' AND p.STATUS = 'active'
            """
            sql_trup = conn.query(sql_q)
            if sql_trup is not None:
                sql_trup.columns = [c.upper() for c in sql_trup.columns]
                sql_trup['PLAYER_WYID'] = sql_trup['PLAYER_WYID'].apply(rens_id)
                klubber = sorted(sql_trup['KLUB'].unique().tolist())
                v_hold = st.selectbox("Vælg hold", klubber)
                if v_hold:
                    csv_ids = df_csv['PLAYER_WYID'].unique().tolist()
                    sql_f = sql_trup[(sql_trup['KLUB'] == v_hold) & (~sql_trup['PLAYER_WYID'].isin(csv_ids))]
                    csv_f = df_csv_vis[(df_csv_vis['COMPETITION_WYID'] == valgt_liga_id) & (df_csv_vis['KLUB'] == v_hold)]
                    vis_trup = pd.concat([sql_f[['NAVN', 'POSITION', 'PLAYER_WYID']], csv_f[['NAVN', 'POSITION', 'PLAYER_WYID']]], ignore_index=True)
                    # hide_index=True fjerner de grå numre
                    st.dataframe(vis_trup.sort_values(by="NAVN"), hide_index=True, use_container_width=True)

if __name__ == "__main__":
    vis_side()
