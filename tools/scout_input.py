import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid
from io import StringIO

# --- KONFIGURATION ---
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
        old_csv_raw = base64.b64decode(content['content']).decode('utf-8')
        old_df = pd.read_csv(StringIO(old_csv_raw))
        # Sikrer at eksisterende PLAYER_WYID også behandles som tekst/string
        if 'PLAYER_WYID' in old_df.columns:
            old_df['PLAYER_WYID'] = old_df['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
        
        updated_df = pd.concat([old_df, new_row_df], ignore_index=True)
        updated_csv = updated_df.to_csv(index=False)
    else:
        sha = None
        updated_csv = new_row_df.to_csv(index=False)

    payload = {
        "message": f"Scouting: {new_row_df['Navn'].values[0]}",
        "content": base64.b64encode(updated_csv.encode('utf-8')).decode('utf-8'),
        "sha": sha if sha else ""
    }
    return requests.put(url, json=payload, headers=headers).status_code

def vis_side(df_players, df_stats_all=None):
    st.markdown("""
        <style>
            [data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
            .id-label { font-size: 12px; color: #666; margin-top: -15px; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.write("#### Scoutrapport")
    
    # 1. HENT SCOUTING DB
    try:
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db_scout = pd.read_csv(raw_url)
        db_scout.columns = [c.strip() for c in db_scout.columns]
        # Rens navne og PLAYER_WYID
        db_scout['Navn'] = db_scout['Navn'].astype(str).str.strip()
        if 'PLAYER_WYID' in db_scout.columns:
            db_scout['PLAYER_WYID'] = db_scout['PLAYER_WYID'].astype(str).str.replace('.0', '', regex=False)
        
        scouted_names_df = db_scout[['Navn', 'Klub', 'Position', 'PLAYER_WYID']].drop_duplicates('Navn')
    except:
        scouted_names_df = pd.DataFrame(columns=['Navn', 'Klub', 'Position', 'PLAYER_WYID'])

    # 2. SAML NAVNE FRA ALLE KILDER
    names_system = [str(n).strip() for n in df_players['NAVN'].unique().tolist() if n] if df_players is not None else []
    
    names_stats = []
    if df_stats_all is not None and not df_stats_all.empty:
        if 'FIRSTNAME' in df_stats_all.columns:
            df_stats_all['FULL_NAME'] = df_stats_all['FIRSTNAME'].str.cat(df_stats_all['LASTNAME'], sep=' ').str.strip()
            names_stats = [str(n).strip() for n in df_stats_all['FULL_NAME'].unique().tolist() if n]
    
    names_manual = [str(n).strip() for n in scouted_names_df['Navn'].unique().tolist() if n]
    alle_navne = sorted(list(set(names_system + names_stats + names_manual)))

    kilde_type = st.radio("Metode", ["Find i systemet", "Opret ny spiller"], horizontal=True, label_visibility="collapsed")
    
    p_id, navn, klub, pos_val = "0", "", "", ""
    pos_default, klub_default = "", ""

    # 3. BASIS INFO
    c1, c2, c3 = st.columns([2, 1, 1])
    
    if kilde_type == "Find i systemet":
        with c1:
            valgt_navn = st.selectbox("Vælg Spiller", options=alle_navne)
            navn = valgt_navn
            
            # Find data & ID (PLAYER_WYID)
            if df_stats_all is not None and valgt_navn in names_stats:
                info = df_stats_all[df_stats_all['FULL_NAME'] == valgt_navn].iloc[0]
                raw_id = info.get('PLAYER_WYID', '0')
                p_id = str(int(float(raw_id))) if pd.notnull(raw_id) else "0"
                klub_default = info.get('TEAMNAME', '')
            elif valgt_navn in names_system:
                info = df_players[df_players['NAVN'].str.strip() == valgt_navn].iloc[0]
                raw_id = info.get('PLAYER_WYID', '0')
                p_id = str(int(float(raw_id))) if pd.notnull(raw_id) else "0"
                pos_raw = info.get('POS', '')
                pos_default = POS_MAP.get(int(pos_raw) if str(pos_raw).replace('.0','').isdigit() else 0, str(pos_raw))
                klub_default = info.get('HOLD', 'Hvidovre IF')
            elif valgt_navn in names_manual:
                info = scouted_names_df[scouted_names_df['Navn'] == valgt_navn].iloc[0]
                p_id = str(info['PLAYER_WYID'])
                pos_default, klub_default = info['Position'], info['Klub']
            
            st.markdown(f"<p class='id-label'>PLAYER_WYID: {p_id}</p>", unsafe_allow_html=True)
            
        with c2: pos_val = st.text_input("Position", value=pos_default)
        with c3: klub = st.text_input("Klub", value=klub_default)
        
    else:
        with c1: 
            navn = st.text_input("Spillernavn")
            p_id = f"999{datetime.now().strftime('%H%M%S')}" # Manuelt ID for spillere uden for systemet
            st.markdown(f"<p class='id-label'>Midlertidigt ID: {p_id}</p>", unsafe_allow_html=True)
        with c2: pos_val = st.text_input("Position")
        with c3: klub = st.text_input("Klub")

    # 4. FORMULAR
    with st.form("scout_form", clear_on_submit=True):
        st.write("**Parametre (1-6)**")
        col1, col2, col3, col4 = st.columns(4)
        beslut = col1.select_slider("Beslut.", options=[1,2,3,4,5,6], value=1)
        fart = col2.select_slider("Fart", options=[1,2,3,4,5,6], value=1)
        aggres = col3.select_slider("Aggres.", options=[1,2,3,4,5,6], value=1)
        att = col4.select_slider("Attitude", options=[1,2,3,4,5,6], value=1)
        
        col5, col6, col7, col8 = st.columns(4)
        udhold = col5.select_slider("Udhold.", options=[1,2,3,4,5,6], value=1)
        leder = col6.select_slider("Leder.", options=[1,2,3,4,5,6], value=1)
        teknik = col7.select_slider("Teknik", options=[1,2,3,4,5,6], value=1)
        intel = col8.select_slider("Intel.", options=[1,2,3,4,5,6], value=1)

        st.divider()
        m1, m2, _ = st.columns([1, 1, 2])
        status = m1.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        potentiale = m2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        styrker = st.text_area("Styrker")
        udvikling = st.text_area("Udvikling")
        vurdering = st.text_area("Samlet vurdering")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn:
                avg = round(sum([beslut, fart, aggres, att, udhold, leder, teknik, intel]) / 8, 1)
                
                # Hent den loggede bruger
                logged_in_scout = st.session_state.get("user", "Ukendt")
                
                # Opret række med "Scout" kolonne
                ny_df = pd.DataFrame([[
                    p_id, 
                    datetime.now().strftime("%Y-%m-%d"), 
                    navn, 
                    klub, 
                    pos_val, 
                    avg, 
                    status, 
                    potentiale, 
                    styrker, 
                    vurdering,
                    beslut, fart, aggres, att, udhold, leder, teknik, intel,
                    logged_in_scout  # <--- Autofyld her
                ]], columns=[
                    "PLAYER_WYID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", 
                    "Status", "Potentiale", "Styrker", "Udvikling", "Vurdering", 
                    "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", 
                    "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens",
                    "Scout" # <--- Ny kolonne
                ])
                
                status_code = save_to_github(ny_df)
                if status_code in [200, 201]:
                    # Trigger log-systemet
                    try:
                        from data.data_load import write_log
                        write_log("Oprettede scoutrapport", target=navn)
                    except:
                        pass
                        
                    st.success(f"Rapport gemt af {logged_in_scout}!")
                    st.rerun()
                else:
                    st.error(f"Fejl ved gem: {status_code}")
            else:
                st.error("Navn mangler")
