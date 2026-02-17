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

def vis_side(df_spillere):
    st.markdown("""
        <style>
            [data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
            .stSlider { margin-bottom: -10px !important; }
            .stTextArea textarea { height: 110px !important; }
            .id-label { font-size: 12px; color: #666; margin-top: -15px; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.write("#### Scoutrapport")
    
   # --- 1. HENT EKSISTERENDE SCOUTING DATA ---
try:
    # FILE_PATH er "data/scouting_db.csv"
    raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
    
    # Vi læser filen - her er det vigtigt at definere separatoren, hvis din CSV bruger semikolon
    db_scout = pd.read_csv(raw_url, sep=None, engine='python') 
    
    # Vi sikrer os at kolonnenavnene matcher (fjerner mellemrum og gør dem ens)
    db_scout.columns = [c.strip() for c in db_scout.columns]
    
    # Hent unikke spillere til dropdown-menuen
    scouted_names_df = db_scout[['Navn', 'Klub', 'Position', 'ID']].drop_duplicates('Navn')
except Exception as e:
    # Hvis filen ikke findes i /data/ endnu, opretter vi en tom dataframe
    # st.error(f"Kunne ikke hente {FILE_PATH}: {e}") # Debug linje
    scouted_names_df = pd.DataFrame(columns=['Navn', 'Klub', 'Position', 'ID'])

    kilde_type = st.radio("Metode", ["Find i systemet", "Opret ny spiller"], horizontal=True, label_visibility="collapsed")
    
    p_id, navn, klub, pos_val = "", "", "", ""

    # --- 2. LOGIK FOR VALG AF SPILLER ---
    c1, c2, c3 = st.columns([2, 1, 1])
    
    if kilde_type == "Find i systemet":
        # Navne fra Snowflake (hvis df_spillere ikke er tom)
        system_names = sorted(df_spillere['NAVN'].unique().tolist()) if not df_spillere.empty else []
        # Navne fra vores scouting_db.csv
        manual_names = sorted(scouted_names_df['Navn'].unique().tolist())
        
        # Samlet liste til selectbox
        alle_navne = sorted(list(set(system_names + manual_names)))
        
        with c1:
            valgt_navn = st.selectbox("Vælg Spiller", options=alle_navne)
            navn = valgt_navn
            
            # Tjek om spilleren findes i Snowflake
            if valgt_navn in system_names:
                info = df_spillere[df_spillere['NAVN'] == valgt_navn].iloc[0]
                p_id = str(info['PLAYER_WYID']).split('.')[0]
                pos_raw = info.get('POS', '')
                pos_default = POS_MAP.get(int(pos_raw) if str(pos_raw).replace('.0','').isdigit() else pos_raw, str(pos_raw))
                klub_default = info.get('HOLD', 'Hvidovre IF')
            
            # Hvis ikke i Snowflake, så find info i scouting_db.csv
            elif valgt_navn in manual_names:
                info = scouted_names_df[scouted_names_df['Navn'] == valgt_navn].iloc[0]
                p_id, pos_default, klub_default = info['ID'], info['Position'], info['Klub']
            
            st.markdown(f"<p class='id-label'>ID: {p_id}</p>", unsafe_allow_html=True)
            
        with c2: pos_val = st.text_input("Position", value=pos_default)
        with c3: klub = st.text_input("Klub", value=klub_default)
        
    else:
        # Opret ny spiller logik
        with c1: 
            navn = st.text_input("Spillernavn", placeholder="Navn...")
            p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"
            st.markdown(f"<p class='id-label'>ID: {p_id} (Auto-genereret)</p>", unsafe_allow_html=True)
        with c2: pos_val = st.text_input("Position", placeholder="f.eks. CB")
        with c3: klub = st.text_input("Klub", placeholder="Klub...")

    # --- 3. FORMULAREN ---
    with st.form("scout_form", clear_on_submit=True):
        st.write("**Parametre (1-6)**")
        
        # Sliders...
        col1, col2, col3, col4 = st.columns(4)
        with col1: beslut = st.select_slider("Beslutsomhed", options=[1,2,3,4,5,6], value=1)
        with col2: fart = st.select_slider("Fart", options=[1,2,3,4,5,6], value=1)
        with col3: aggres = st.select_slider("Aggresivitet", options=[1,2,3,4,5,6], value=1)
        with col4: attitude = st.select_slider("Attitude", options=[1,2,3,4,5,6], value=1)

        col5, col6, col7, col8 = st.columns(4)
        with col5: udhold = st.select_slider("Udholdenhed", options=[1,2,3,4,5,6], value=1)
        with col6: leder = st.select_slider("Lederegenskaber", options=[1,2,3,4,5,6], value=1)
        with col7: teknik = st.select_slider("Teknik", options=[1,2,3,4,5,6], value=1)
        with col8: intel = st.select_slider("Intelligens", options=[1,2,3,4,5,6], value=1)

        st.divider()
        m1, m2, _ = st.columns([1, 1, 2])
        with m1: status = st.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        with m2: potentiale = st.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        st.write("**Vurdering**")
        t1, t2, t3 = st.columns(3)
        with t1: styrker = st.text_area("Styrker")
        with t2: udvikling = st.text_area("Udvikling")
        with t3: vurdering = st.text_area("Samlet")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn and p_id:
                avg_rating = round(sum([beslut, fart, aggres, attitude, udhold, leder, teknik, intel]) / 8, 1)
                ny_data = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), navn, klub, pos_val, 
                    avg_rating, status, potentiale, styrker, udvikling, vurdering,
                    beslut, fart, aggres, attitude, udhold, leder, teknik, intel
                ]], columns=["ID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status", "Potentiale", "Styrker", "Udvikling", "Vurdering", "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"])
                
                status_code = save_to_github(ny_data)
                
                if status_code in [200, 201]:
                    st.success("Rapport gemt! Data genindlæses...")
                    st.rerun() # Dette gør at listen opdateres med det samme
                else: 
                    st.error(f"Fejl: {status_code}")
            else: 
                st.error("Navn mangler!")
