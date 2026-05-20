import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime, date
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# Den præcise rækkefølge vi ønsker fremover
COL_ORDER = [
    "KLUB", "NAVN", "POSITION", "PLAYER_WYID", 
    "PLAYER_OPTAUUID", "CONTRACT_EXPIRY", "TRANSFER_DATE", "PREVIOUS_CLUB"
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
    st.title("🏟️ Transfer & Trup Management")

    # 1. HENT OG REPARER CSV
    csv_content, csv_sha = get_github_file(FILE_PATH)
    
    if csv_content:
        # Læs filen - vi bruger 'on_bad_lines' for at undgå crash ved skæve rækker
        df_raw = pd.read_csv(StringIO(csv_content), on_bad_lines='skip')
        
        # REPARATION: Vi tvinger de nye kolonner ind, hvis de mangler
        # .reindex sikrer at vi har alle kolonner i COL_ORDER, og fjerner dem vi ikke skal bruge
        df_1div = df_raw.reindex(columns=COL_ORDER)
        
        # Sørg for at PLAYER_WYID er string for nemmere match
        df_1div['PLAYER_WYID'] = df_1div['PLAYER_WYID'].astype(str).apply(rens_id)
    else:
        df_1div = pd.DataFrame(columns=COL_ORDER)

    # Konverter datoer sikkert
    df_1div['TRANSFER_DATE'] = pd.to_datetime(df_1div['TRANSFER_DATE'], errors='coerce').dt.date
    today = date.today()

    # Hent database (Snowflake)
    import data.HIF_load as hif_load
    try:
        dp = hif_load.get_scouting_package()
        df_sql = dp.get("wyscout_players", pd.DataFrame())
    except:
        df_sql = pd.DataFrame()

    # 2. LAYOUT
    col_left, col_right = st.columns([1, 1], gap="large")

    # --- VENSTRE SIDE: REDIGERING ---
    with col_left:
        st.subheader("🔄 Opdater Spiller / Transfer")
        
        unique_players = {}
        csv_ids = set(df_1div['PLAYER_WYID'].tolist())

        # Eksisterende i CSV
        for _, r in df_1div.iterrows():
            p_id = r['PLAYER_WYID']
            if p_id and p_id != "":
                unique_players[p_id] = {
                    "label": f"🟢 {r['NAVN']} ({r['KLUB']})",
                    "data": r.to_dict()
                }

        # Fra SQL Database
        if not df_sql.empty:
            for _, r in df_sql.iterrows():
                p_id = rens_id(r.get('PLAYER_WYID'))
                if not p_id or p_id in csv_ids: continue
                
                f, l = str(r.get('FIRSTNAME', '')).strip(), str(r.get('LASTNAME', '')).strip()
                navn = f"{f} {l}".strip() if (f or l) else str(r.get('PLAYER_NAME', 'Ukendt'))
                unique_players[p_id] = {
                    "label": f"⚪ {navn} ({r.get('TEAMNAME', 'DB')})",
                    "data": {"NAVN": navn, "PLAYER_WYID": p_id, "POSITION": r.get('ROLECODE3', ""), "KLUB": r.get('TEAMNAME', ""), "PLAYER_OPTAUUID": r.get('PLAYER_OPTAUUID', "")}
                }

        sel_id = st.selectbox("Søg spiller", [""] + sorted(unique_players.keys(), key=lambda x: unique_players[x]["label"][2:]), 
                              format_func=lambda x: unique_players[x]["label"] if x else "Vælg...")

        if sel_id:
            p = unique_players[sel_id]["data"]
            with st.form("edit_form"):
                st.write(f"Redigerer: **{p['NAVN']}**")
                
                # Klub-liste fra CSV + muligheden for at skrive en ny
                eksisterende_klubber = sorted([k for k in df_1div['KLUB'].unique() if pd.notna(k)])
                ny_klub = st.selectbox("Destination", ["--- UÆNDRET ---", "✈️ Slet / Udlandet"] + eksisterende_klubber)
                
                c1, c2 = st.columns(2)
                exp_date = c1.date_input("Kontraktudløb", value=pd.to_datetime(p.get('CONTRACT_EXPIRY')).date() if pd.notna(p.get('CONTRACT_EXPIRY')) else today)
                eff_date = c2.date_input("Skiftet træder i kraft", value=today)
                
                if st.form_submit_button("GEM ÆNDRING"):
                    # Fjern gammel version
                    df_final = df_1div[df_1div['PLAYER_WYID'] != sel_id].copy()
                    
                    if ny_klub != "✈️ Slet / Udlandet":
                        target_klub = p['KLUB'] if ny_klub == "--- UÆNDRET ---" else ny_klub
                        ny_række = {
                            "KLUB": target_klub,
                            "NAVN": p['NAVN'],
                            "POSITION": p.get('POSITION', ''),
                            "PLAYER_WYID": sel_id,
                            "PLAYER_OPTAUUID": p.get('PLAYER_OPTAUUID'),
                            "CONTRACT_EXPIRY": str(exp_date),
                            "TRANSFER_DATE": str(eff_date),
                            "PREVIOUS_CLUB": p['KLUB'] if ny_klub != "--- UÆNDRET ---" else p.get('PREVIOUS_CLUB')
                        }
                        df_final = pd.concat([df_final, pd.DataFrame([ny_række])], ignore_index=True)
                    
                    # Push til GitHub
                    csv_string = df_final[COL_ORDER].to_csv(index=False)
                    push_to_github(FILE_PATH, f"Opdatering: {p['NAVN']}", csv_string, csv_sha)
                    st.success("Opdateret! Genindlæser...")
                    time.sleep(1)
                    st.rerun()

    # --- HØJRE SIDE: DROPDOWN OG TRUP ---
    with col_right:
        st.subheader("📋 Trupoversigt")
        klubber = sorted([k for k in df_1div['KLUB'].unique() if pd.notna(k)])
        valgt_hold = st.selectbox("Vælg hold", klubber)
        
        if valgt_hold:
            trup = df_1div[df_1div['KLUB'] == valgt_hold].copy()
            
            # Formatering til visning
            vis_df = []
            for _, s in trup.iterrows():
                status = ""
                # Tjek om skiftet er i fremtiden
                if pd.notna(s['TRANSFER_DATE']) and s['TRANSFER_DATE'] > today:
                    status = f"⏳ Tilgår {s['TRANSFER_DATE']}"
                
                vis_df.append({
                    "Spiller": s['NAVN'],
                    "Pos": s['POSITION'],
                    "Udløb": s['CONTRACT_EXPIRY'],
                    "Info": status
                })
            
            st.table(pd.DataFrame(vis_df))

if __name__ == "__main__":
    vis_side()
