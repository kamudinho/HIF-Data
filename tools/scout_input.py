import streamlit as st
import pandas as pd
import uuid
import time
from datetime import datetime
from io import StringIO

# 1. NYE IMPORTS: Vi henter alt fra team_mapping i stedet for season_show
from data.utils.team_mapping import COMPETITION_NAME, TOURNAMENTCALENDAR_NAME, COMPETITIONS, TEAMS

try:
    from utils.github import get_github_file, push_to_github
except ImportError:
    st.error("Kunne ikke finde github.py i utils mappen.")

def vis_side(dp):
    # --- 1. INITIALISERING AF SESSION STATE ---
    if 'scout_temp_data' not in st.session_state:
        st.session_state.scout_temp_data = {"n": "", "id": "", "pos": "", "klub": ""}
    
    curr_user = st.session_state.get("user", "System").upper()

    # --- 3. DATA HÅNDTERING ---
    # Vi bruger 'players' (vores Snowflake/CSV hybrid) fra datapakken
    df_ps_raw = dp.get("players", pd.DataFrame())
    
    # Vi bygger et hold_map ud fra din TEAMS dict i team_mapping.py
    # Dette sikrer at vi får rigtige klubnavne i stedet for "Ukendt klub"
    hold_map = {info["team_wyid"]: name for name, info in TEAMS.items() if "team_wyid" in info}
    
    # Find WYID for den valgte liga (f.eks. 328 for 1. Division)
    valgt_liga_info = COMPETITIONS.get(COMPETITION_NAME, {})
    valgt_liga_wyid = valgt_liga_info.get("wyid")

    if not df_ps_raw.empty:
        df_ps_raw.columns = [str(c).strip().upper() for c in df_ps_raw.columns]
        
        # Filtrer på den liga og sæson vi har sat i team_mapping.py
        if 'COMPETITION_WYID' in df_ps_raw.columns and valgt_liga_wyid:
            df_ps_raw = df_ps_raw[df_ps_raw['COMPETITION_WYID'] == valgt_liga_wyid]
            
        if 'SEASONNAME' in df_ps_raw.columns:
            df_ps_raw = df_ps_raw[df_ps_raw['SEASONNAME'] == TOURNAMENTCALENDAR_NAME]
            
        df_ps = df_ps_raw.drop_duplicates(subset=['PLAYER_WYID'], keep='first')
    else:
        df_ps = df_ps_raw
        
    # --- 4. DROPDOWN LISTE ---
    spiller_options = {}
    if not df_ps.empty:
        for _, r in df_ps.iterrows():
            try:
                p_id = str(int(float(r['PLAYER_WYID'])))
                # Tjek både CURRENTTEAM_WYID og TEAM_WYID
                t_id_raw = r.get('CURRENTTEAM_WYID') or r.get('TEAM_WYID')
                t_id = int(float(t_id_raw)) if pd.notnull(t_id_raw) else 0
                
                klub_navn = hold_map.get(t_id, "Anden klub")
                
                f_name = str(r.get('FIRSTNAME', "")).strip()
                l_name = str(r.get('LASTNAME', "")).strip()
                full = f"{f_name} {l_name}".strip() or str(r.get('SHORTNAME', 'Ukendt'))
                
                label = f"{full} ({klub_navn})"
                spiller_options[label] = {
                    "n": full, 
                    "id": p_id, 
                    "pos": str(r.get('ROLECODE3', '')).strip().upper(), 
                    "klub": klub_navn
                }
            except: continue

    # --- 5. UI & FORM ---
    metode = st.radio("Vælg spiller via:", ["Søg i systemet", "Manuel oprettelse"], horizontal=True)
    
    if metode == "Søg i systemet":
        sorted_labels = sorted(list(spiller_options.keys()))
        selected = st.selectbox(f"Find spiller i {COMPETITION_NAME}", options=[""] + sorted_labels)
        
        if selected:
            st.session_state.scout_temp_data = spiller_options[selected]
    else:
        c1, c2 = st.columns([3, 1])
        st.session_state.scout_temp_data["n"] = c1.text_input("Navn", value=st.session_state.scout_temp_data.get("n", ""))
        if not st.session_state.scout_temp_data.get("id") or "M-" not in str(st.session_state.scout_temp_data["id"]):
            st.session_state.scout_temp_data["id"] = f"M-{str(uuid.uuid4().int)[:6]}"
        st.session_state.scout_temp_data["id"] = c2.text_input("ID", value=st.session_state.scout_temp_data["id"])

    # ... Resten af din form-logik (Position, Sliders, osv.) er identisk ...
