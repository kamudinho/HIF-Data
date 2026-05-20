import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime, date
import time

# IMPORT FRA DINE EGNE MODULER
# Sørg for at disse stier passer til din projektstruktur
try:
    import data.HIF_load as hif_load
except ImportError:
    st.error("Kunne ikke finde hif_load modulet. Tjek dine import-stier.")

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# Den fulde liste over kolonner vi ønsker at vedligeholde
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
    except Exception as e:
        st.error(f"GitHub fejl: {e}")
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

# --- HOVEDSIDE ---
def vis_side():
    # 1. INITIALISERING AF DATA
    csv_content, csv_sha = get_github_file(FILE_PATH)
    
    if csv_content:
        df_1div = pd.read_csv(StringIO(csv_content))
        # AUTO-REPAIR: Tilføj manglende kolonner hvis de ikke findes i den indlæste fil
        for col in COL_ORDER:
            if col not in df_1div.columns:
                df_1div[col] = None
    else:
        df_1div = pd.DataFrame(columns=COL_ORDER)
    
    # Konvertér datoer til datetime.date for sammenligning
    df_1div['TRANSFER_DATE'] = pd.to_datetime(df_1div['TRANSFER_DATE']).dt.date
    today = date.today()

    with st.spinner("Synkroniserer med database..."):
        try:
            dp = hif_load.get_scouting_package()
            df_sql = dp.get("wyscout_players", pd.DataFrame())
        except:
            df_sql = pd.DataFrame()
            st.warning("Kunne ikke hente data fra Snowflake.")

    # 2. LAYOUT: TO KOLONNER
    col_left, col_right = st.columns([1, 1.2], gap="large")

    # --- VENSTRE SIDE: TRANSFER CENTER ---
    with col_left:
        st.subheader("🔄 Transfer Center")
        
        unique_players = {}
        csv_ids = set(df_1div['PLAYER_WYID'].astype(str).apply(rens_id).tolist())

        # Byg dropdown liste (Grønne = Findes i CSV)
        for _, r in df_1div.iterrows():
            p_id = rens_id(r.get('PLAYER_WYID'))
            if p_id:
                unique_players[p_id] = {
                    "label": f"🟢 {r['NAVN']} ({r['KLUB']})",
                    "data": r.to_dict()
                }

        # Tilføj fra SQL (Hvide = Database spillere)
        if not df_sql.empty:
            for _, r in df_sql.iterrows():
                p_id = rens_id(r.get('PLAYER_WYID'))
                if not p_id or p_id in csv_ids: continue
                
                # Navne-logik: First + Last
                f, l = str(r.get('FIRSTNAME', '')).strip(), str(r.get('LASTNAME', '')).strip()
                full_navn = f"{f} {l}".strip() if (f or l) else str(r.get('PLAYER_NAME', 'Ukendt'))
                klub_db = str(r.get('TEAMNAME', 'Database')).strip()
                
                unique_players[p_id] = {
                    "label": f"⚪ {full_navn} ({klub_db})",
                    "data": {
                        "NAVN": full_navn, 
                        "PLAYER_WYID": p_id, 
                        "POSITION": r.get('ROLECODE3', ""), 
                        "KLUB": klub_db,
                        "PLAYER_OPTAUUID": r.get('PLAYER_OPTAUUID', "")
                    }
                }

        # Alfabetisk sortering
        options_list = sorted(unique_players.keys(), key=lambda x: unique_players[x]["label"][2:].lower())
        
        sel_id = st.selectbox(
            "Vælg eller søg spiller", 
            [""] + options_list, 
            format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller..."
        )

        if sel_id:
            p = unique_players[sel_id]["data"]
            st.info(f"**Valgt:** {p['NAVN']} | **Nuværende:** {p['KLUB']}")
            
            with st.form("transfer_form"):
                st.write("📝 **Registrer skifte eller opdater info**")
                
                c1, c2 = st.columns(2)
                alle_eksisterende_klubber = sorted(df_1div['KLUB'].unique().tolist())
                dest_options = ["--- BEHOLD KLUB ---", "✈️ Udlandet / Slet"] + alle_eksisterende_klubber
                
                new_klub = c1.selectbox("Flyt til (Destination)", dest_options)
                new_pos = c2.text_input("Position", value=p.get('POSITION', ''))
                
                d1, d2 = st.columns(2)
                # Kontraktudløb
                try:
                    exp_val = pd.to_datetime(p.get('CONTRACT_EXPIRY')).date() if pd.notna(p.get('CONTRACT_EXPIRY')) else None
                except: exp_val = None
                new_expiry = d1.date_input("Kontraktudløb", value=exp_val)
                
                # Transferdato
                new_trans_date = d2.date_input("Effektueringsdato", value=today)

                if st.form_submit_button("GEM ÆNDRINGER", use_container_width=True):
                    # Rens eksisterende række
                    df_final = df_1div[df_1div['PLAYER_WYID'].astype(str).apply(rens_id) != str(sel_id)].copy()
                    
                    if new_klub != "✈️ Udlandet / Slet":
                        target_klub = p['KLUB'] if new_klub == "--- BEHOLD KLUB ---" else new_klub
                        
                        ny_række = {
                            "KLUB": target_klub,
                            "NAVN": p['NAVN'],
                            "POSITION": new_pos,
                            "PLAYER_WYID": int(sel_id),
                            "PLAYER_OPTAUUID": p.get('PLAYER_OPTAUUID'),
                            "CONTRACT_EXPIRY": str(new_expiry),
                            "TRANSFER_DATE": str(new_trans_date),
                            "PREVIOUS_CLUB": p['KLUB'] if new_klub != "--- BEHOLD KLUB ---" else p.get('PREVIOUS_CLUB')
                        }
                        df_final = pd.concat([df_final, pd.DataFrame([ny_række])], ignore_index=True)
                    
                    # Gem til GitHub
                    final_csv = df_final[COL_ORDER].sort_values(['KLUB', 'NAVN']).to_csv(index=False)
                    res = push_to_github(FILE_PATH, f"Opdatering: {p['NAVN']}", final_csv, csv_sha)
                    
                    if res in [200, 201]:
                        st.success("Opdateret på GitHub!")
                        time.sleep(0.5)
                        st.rerun()

    # --- HØJRE SIDE: TRUPOVERSIGT ---
    with col_right:
        st.subheader("📋 Trup oversigt")
        
        hold_liste = sorted(df_1div['KLUB'].unique().tolist())
        # Sæt standard til Hvidovre IF hvis muligt
        default_idx = hold_liste.index("Hvidovre IF") if "Hvidovre IF" in hold_liste else 0
        
        valgt_hold = st.selectbox("Vælg klub", hold_liste, index=default_idx)
        
        if valgt_hold:
            trup = df_1div[df_1div['KLUB'] == valgt_hold].copy()
            
            visnings_data = []
            for _, sp in trup.iterrows():
                info = ""
                t_date = sp.get('TRANSFER_DATE')
                
                # Check for fremtidig dato
                if pd.notna(t_date) and t_date > today:
                    info = f"⏳ Tilgår {t_date}"
                
                visnings_data.append({
                    "Navn": sp['NAVN'],
                    "Position": sp['POSITION'],
                    "Udløb": sp['CONTRACT_EXPIRY'] if pd.notna(sp['CONTRACT_EXPIRY']) else "-",
                    "Status": info
                })
            
            if visnings_data:
                st.dataframe(
                    pd.DataFrame(visnings_data), 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.write("Ingen spillere fundet i denne klub.")

# Kør siden
if __name__ == "__main__":
    vis_side()
