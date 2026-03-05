import streamlit as st
import pandas as pd
import uuid
from datetime import datetime
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    st.title("Ny Scouting Rapport")
    
    # HENT DATA
    df_local = dp.get("players", pd.DataFrame())     
    df_sql = dp.get("sql_players", pd.DataFrame())   
    
    # Denne ordbog oversætter WYID -> NAVN (f.eks. 7490 -> "Hvidovre")
    hold_map = {info["team_wyid"]: name for name, info in TEAMS.items() if "team_wyid" in info}
    
    spiller_options = {}

    def add_to_options(df, source_label):
        if df is None or df.empty:
            return
        
        # Sørg for at vi rammer de store bogstaver fra Snowflake
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        for _, r in df.iterrows():
            # 1. PLAYER_WYID (ID)
            p_id = str(r.get('PLAYER_WYID', '')).split('.')[0].strip()
            if not p_id or p_id in ['nan', 'None']: continue
            
            # 2. NAVN (Bruger PLAYER_NAME fra din SQL query)
            navn = r.get('PLAYER_NAME') 
            if not navn:
                navn = f"{r.get('FIRSTNAME', '')} {r.get('LASTNAME', '')}".strip()
            if not navn or navn == "":
                navn = r.get('NAVN', 'Ukendt')
            
            # 3. POSITION (ROLECODE3 fra din SQL)
            pos = r.get('ROLECODE3') or r.get('POS', '??')
            
            # 4. KLUB (Her sker oversættelsen fra ID til TEAMNAME)
            t_id = r.get('TEAM_WYID') or r.get('CURRENTTEAM_WYID')
            try:
                # Vi slår ID'et op i hold_map for at få det læsbare navn
                klub = hold_map.get(int(float(t_id)), "Ukendt klub") if pd.notnull(t_id) else "Ukendt klub"
            except:
                klub = "Ukendt klub"
            
            # 5. Lav den label som brugeren ser i dropdown
            label = f"{navn} ({klub}) [{pos}] - {source_label}"
            
            spiller_options[label] = {
                "n": navn, 
                "id": p_id, 
                "pos": pos, 
                "klub": klub
            }

    # Kør indlæsningen
    add_to_options(df_local, "HIF")
    add_to_options(df_sql, "Wyscout")

    # --- VISNING ---
    metode = st.radio("Metode", ["Søg system", "Manuel"], horizontal=True)
    
    if metode == "Søg system":
        options_list = sorted(list(spiller_options.keys()))
        sel = st.selectbox("Vælg spiller", [""] + options_list)
        data = spiller_options.get(sel, {"n": "", "id": "", "pos": "", "klub": ""})
    else:
        c1, c2 = st.columns(2)
        n = c1.text_input("Navn")
        tid = f"M-{str(uuid.uuid4().int)[:6]}"
        data = {"n": n, "id": tid, "pos": "", "klub": c2.text_input("Klub")}

    # Vis formen hvis der er valgt en spiller
    if data["n"]:
        with st.form("rapport_form"):
            st.subheader(f"Vurdering af {data['n']} ({data['klub']})")
            # ... (dine sliders og text_areas)
            
            if st.form_submit_button("Gem Rapport"):
                # Din gemme logik her
                st.success(f"Rapport gemt for {data['n']} fra {data['klub']}!")
