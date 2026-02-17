#tools/scout_input.py
import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid
from io import StringIO
from data.data_load import write_log

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"

def save_to_github(new_row_df):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()
        old_df = pd.read_csv(StringIO(base64.b64decode(content['content']).decode('utf-8')))
        # Sikrer at vi kan tilføje den nye kolonne 'Scout' til gamle filer
        updated_df = pd.concat([old_df, new_row_df], ignore_index=True, sort=False)
        sha = content['sha']
    else:
        updated_df = new_row_df
        sha = None

    payload = {
        "message": f"Scouting: {new_row_df['Navn'].values[0]}",
        "content": base64.b64encode(updated_df.to_csv(index=False).encode('utf-8')).decode('utf-8'),
        "sha": sha if sha else ""
    }
    return requests.put(url, json=payload, headers=headers).status_code

def vis_side(df_players, df_stats_all=None):
    st.write("#### Scoutrapport")
    
    # ... (Samme logik til valg af spiller som i din kode) ...
    # Antager vi har variablerne: p_id, navn, klub, pos_val
    
    with st.form("scout_form", clear_on_submit=True):
        # ... (Dine sliders og text_areas) ...
        
        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn:
                avg = round(sum([beslut, fart, aggres, att, udhold, leder, teknik, intel]) / 8, 1)
                logged_in_scout = st.session_state.get("user", "Ukendt")
                
                ny_df = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), navn, klub, pos_val, 
                    avg, status, potentiale, styrker, vurdering,
                    beslut, fart, aggres, att, udhold, leder, teknik, intel,
                    logged_in_scout
                ]], columns=[
                    "PLAYER_WYID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", 
                    "Status", "Potentiale", "Styrker", "Vurdering", 
                    "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", 
                    "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens",
                    "Scout"
                ])
                
                if save_to_github(ny_df) in [200, 201]:
                    write_log("Oprettede scoutrapport", target=navn)
                    st.success(f"Rapport gemt af {logged_in_scout}!")
                    st.rerun()
