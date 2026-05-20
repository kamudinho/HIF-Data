import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime
import time

# IMPORT AF DINE EGNE FORBINDELSER
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", 
    "PLAYER_OPTAUUID", "COMPETITION_WYID", "COMPETITION_OPTAUUID"
]

# --- HJÆLPEFUNKTIONER ---
def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            return content, data['sha']
    except Exception as e:
        st.error(f"GitHub Hent Fejl: {e}")
    return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
    }
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- NY FUNKTION: HENT DATA DIREKTE PÅ SIDEN ---
def get_all_needed_data():
    """Henter både CSV fra GitHub og alle spillere fra Snowflake"""
    # 1. Hent CSV fra GitHub
    csv_content, csv_sha = get_github_file(FILE_PATH)
    df_1div = pd.read_csv(StringIO(csv_content)) if csv_content else pd.DataFrame(columns=COL_ORDER)
    
    # 2. Hent ALLE spillere direkte fra Snowflake (så vi kan finde 3. div osv.)
    conn = _get_snowflake_conn()
    # Vi henter kun de nødvendige kolonner for at optimere hastigheden
    query = """
        SELECT PLAYER_WYID, FIRSTNAME, LASTNAME, SHORTNAME, ROLECODE3 
        FROM WYSCOUT_PLAYERS
    """
    df_sql = conn.query(query, ttl=3600) # Cache i 1 time
    
    return df_1div, df_sql, csv_sha

# --- HOVEDSIDE ---
def vis_side(): # Ingen 'dp' påkrævet længere
    st.info("Henter spillerdatabase fra Snowflake... Vent venligst.")
    
    # Hent data direkte her på siden
    df_1div, df_sql, csv_sha = get_all_needed_data()

    unique_players = {}
    
    # 1. Byg puljen fra SQL (hvide cirkler)
    for _, r in df_sql.iterrows():
        p_id = rens_id(r.get('PLAYER_WYID'))
        if not p_id: continue
        
        f = str(r.get('FIRSTNAME', '')).strip()
        l = str(r.get('LASTNAME', '')).strip()
        full_navn = f"{f} {l}".strip() if (f or l) else str(r.get('SHORTNAME', 'Ukendt'))
        
        unique_players[p_id] = {
            "label": f"⚪ {full_navn} (Database)",
            "data": {"n": full_navn, "id": p_id, "pos": r.get('ROLECODE3', ""), "klub": "Ikke i 1. div", "opta": ""}
        }

    # 2. Overskriv/Marker dem fra 1. div filen (grønne cirkler)
    for _, r in df_1div.iterrows():
        p_id = rens_id(r.get('PLAYER_WYID'))
        if p_id:
            unique_players[p_id] = {
                "label": f"🟢 {r['NAVN']} ({r['KLUB']})",
                "data": {"n": r['NAVN'], "id": p_id, "pos": r['POSITION'], "klub": r['KLUB'], "opta": r.get('PLAYER_OPTAUUID', "")}
            }

    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI ---
    st.subheader("Trupplanlægning & Transfers")
    
    sel_id = st.selectbox("Søg efter navn eller Wyscout ID", [""] + options_list, 
                          format_func=lambda x: unique_players[x]["label"] if x else "Start med at skrive navn...")

    if sel_id:
        p_info = unique_players[sel_id]["data"]
        
        col1, col2 = st.columns([1, 4])
        with col1:
            st.image(f"https://cdn5.wyscout.com/photos/players/public/{sel_id}.png", width=100)
        with col2:
            st.markdown(f"### {p_info['n']}")
            st.caption(f"ID: {sel_id} | Position: {p_info['pos']}")

        with st.form("transfer_form"):
            c1, c2 = st.columns(2)
            # Vi definerer klubberne manuelt her eller tager dem fra din liste
            klubber = sorted(df_1div['KLUB'].unique().tolist())
            valgt_klub = c1.selectbox("Vælg hold i 1. Division", klubber)
            valgt_pos = c2.text_input("Position", value=p_info['pos'])
            
            valgt_opta = st.text_input("PLAYER_OPTAUUID (Valgfri / 3. div)", value=p_info['opta'])
            
            if st.form_submit_button("GEM SPILLER PÅ HOLDLISTE", use_container_width=True):
                ny_række = {
                    "KLUB": valgt_klub, "NAVN": p_info['n'], "POSITION": valgt_pos,
                    "PLAYER_WYID": int(sel_id), "PLAYER_OPTAUUID": valgt_opta if valgt_opta else None,
                    "COMPETITION_WYID": 328, "COMPETITION_OPTAUUID": "6ifaeunfdelecgticvxanikzu"
                }

                df_final = df_1div[df_1div['PLAYER_WYID'].astype(str) != str(sel_id)].copy()
                df_final = pd.concat([df_final, pd.DataFrame([ny_række])], ignore_index=True)
                df_final = df_final.sort_values(by=['KLUB', 'NAVN'])
                
                csv_str = df_final[COL_ORDER].to_csv(index=False)
                res = push_to_github(FILE_PATH, f"Transfer: {p_info['n']}", csv_str, csv_sha)
                
                if res in [200, 201]:
                    st.success("Gemt!")
                    time.sleep(1)
                    st.rerun()

    with st.expander("Se nuværende holdlister"):
        st.dataframe(df_1div.sort_values(['KLUB', 'NAVN']), use_container_width=True, hide_index=True)
