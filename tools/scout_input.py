import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid
from io import StringIO

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"

POS_MAP = {
    1: "MM", 2: "HB", 3: "CB", 4: "CB", 5: "VB", 
    6: "DM", 8: "CM", 7: "Højre kant", 11: "Venstre kant", 
    9: "Angriber", 10: "Offensiv midtbane"
}

def save_to_github(new_row_df):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()
        sha = content['sha']
        old_df = pd.read_csv(StringIO(base64.b64decode(content['content']).decode('utf-8')))
        updated_csv = pd.concat([old_df, new_row_df], ignore_index=True).to_csv(index=False)
    else:
        sha, updated_csv = None, new_row_df.to_csv(index=False)

    payload = {"message": f"Scouting: {new_row_df['Navn'].values[0]}", "content": base64.b64encode(updated_csv.encode('utf-8')).decode('utf-8'), "sha": sha if sha else ""}
    return requests.put(url, json=payload, headers=headers).status_code

def vis_side(df_players, df_stats_all=None): # Vi tager imod begge kilder
    st.write("#### Scoutrapport")
    
    # 1. Hent eksisterende scouting data
    try:
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db_scout = pd.read_csv(raw_url)
        db_scout['Navn'] = db_scout['Navn'].astype(str).str.strip()
        scouted_names_df = db_scout[['Navn', 'Klub', 'Position', 'ID']].drop_duplicates('Navn')
    except:
        scouted_names_df = pd.DataFrame(columns=['Navn', 'Klub', 'Position', 'ID'])

    # 2. Saml alle mulige navne (System, Stats og Manuel Database)
    names_system = df_players['NAVN'].dropna().str.strip().tolist() if df_players is not None else []
    names_stats = []
    if df_stats_all is not None and not df_stats_all.empty:
        # Flet Fornavn og Efternavn hvis det er Snowflake data
        if 'FIRSTNAME' in df_stats_all.columns:
            df_stats_all['FULL_NAME'] = df_stats_all['FIRSTNAME'].str.cat(df_stats_all['LASTNAME'], sep=' ').str.strip()
            names_stats = df_stats_all['FULL_NAME'].unique().tolist()
            
    names_manual = scouted_names_df['Navn'].unique().tolist()
    
    # Flet alt og fjern dubletter
    alle_navne = sorted(list(set(names_system + names_stats + names_manual)))

    kilde_type = st.radio("Metode", ["Find i systemet", "Opret ny spiller"], horizontal=True, label_visibility="collapsed")
    
    if kilde_type == "Find i systemet":
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            valgt_navn = st.selectbox("Vælg Spiller", options=alle_navne)
            
            # Opslags-logik
            p_id, pos_default, klub_default = "0", "", ""
            
            # Tjek 1: Er det en vi har scoutet før?
            if valgt_navn in names_manual:
                row = scouted_names_df[scouted_names_df['Navn'] == valgt_navn].iloc[0]
                p_id, pos_default, klub_default = row['ID'], row['Position'], row['Klub']
            # Tjek 2: Er det en fra truppen?
            elif valgt_navn in names_system:
                row = df_players[df_players['NAVN'].str.strip() == valgt_navn].iloc[0]
                p_id = str(row.get('PLAYER_WYID', '0')).split('.')[0]
                pos_raw = row.get('POS', '')
                pos_default = POS_MAP.get(int(pos_raw) if str(pos_raw).isdigit() else 0, str(pos_raw))
                klub_default = row.get('HOLD', 'Hvidovre IF')
            # Tjek 3: Find i alle stats (Konrad-check)
            elif valgt_navn in names_stats:
                row = df_stats_all[df_stats_all['FULL_NAME'] == valgt_navn].iloc[0]
                p_id = str(row.get('PLAYER_WYID', '0'))
                pos_default = "" # Stats-tabellen har ofte ikke position
                klub_default = row.get('TEAMNAME', '')

            st.markdown(f"<p style='font-size:12px; color:gray;'>ID: {p_id}</p>", unsafe_allow_html=True)
        
        with c2: pos_val = st.text_input("Position", value=pos_default)
        with c3: klub = st.text_input("Klub", value=klub_default)

    # ... Resten af din form-kode (Sliders, text_areas osv.) er uændret ...
    # Husk at bruge 'valgt_navn' og 'p_id' når du gemmer!
