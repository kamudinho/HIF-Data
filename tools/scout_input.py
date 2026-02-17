import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid
from io import StringIO

# --- KONFIGURATION OG ADGANG ---
# REPO skal kun være "bruger/repo"
# FILE_PATH skal indeholde hele stien fra roden
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"

POS_MAP = {
    1: "MM", 2: "HB", 3: "CB", 4: "CB", 5: "VB", 
    6: "DM", 8: "CM", 7: "Højre kant", 11: "Venstre kant", 
    9: "Angriber", 10: "Offensiv midtbane"
}

def save_to_github(new_row_df):
    """Henter eksisterende CSV, tilføjer række og uploader til GitHub."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Forsøg at hente eksisterende fil
    r = requests.get(url, headers=headers)
    
    if r.status_code == 200:
        content = r.json()
        sha = content['sha']
        # Dekod eksisterende indhold
        old_csv_raw = base64.b64decode(content['content']).decode('utf-8')
        old_df = pd.read_csv(StringIO(old_csv_raw))
        # Kombiner med ny data
        updated_df = pd.concat([old_df, new_row_df], ignore_index=True)
        updated_csv = updated_df.to_csv(index=False)
    else:
        # Hvis filen ikke findes, opret en ny med header
        sha = None
        updated_csv = new_row_df.to_csv(index=False)

    # 2. Forbered payload til GitHub
    payload = {
        "message": f"Scouting: {new_row_df['Navn'].values[0]}",
        "content": base64.b64encode(updated_csv.encode('utf-8')).decode('utf-8'),
        "sha": sha if sha else ""
    }
    
    # 3. Send opdatering (PUT)
    res = requests.put(url, json=payload, headers=headers)
    return res.status_code

def vis_side(df_spillere):
    # CSS til at stramme layoutet op
    st.markdown("""
        <style>
            [data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
            .stSlider { margin-bottom: -10px !important; }
            .stTextArea textarea { height: 110px !important; }
            .id-label { font-size: 12px; color: #666; margin-top: -15px; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.write("#### Scoutrapport")
    
    # --- DATA HENTNING (Læs fra den rigtige mappe) ---
    try:
        # Vi bruger rå URL til læsning (cache busting med uuid for at få de nyeste data)
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db_scout = pd.read_csv(raw_url)
        scouted_names = db_scout[['Navn', 'Klub', 'Position', 'ID']].drop_duplicates('Navn')
    except:
        # Hvis filen er tom eller ikke findes endnu
        scouted_names = pd.DataFrame(columns=['Navn', 'Klub', 'Position', 'ID'])

    kilde_type = st.radio("Metode", ["Find i systemet", "Opret ny spiller"], horizontal=True, label_visibility="collapsed")
    
    p_id, navn, klub, pos_val = "", "", "", ""

    # --- BASIS INFORMATION ---
    c1, c2, c3 = st.columns([2, 1, 1])
    
    if kilde_type == "Find i systemet":
        system_names = sorted(df_spillere['NAVN'].unique().tolist()) if not df_spillere.empty else []
        manual_names = sorted(scouted_names['Navn'].unique().tolist())
        alle_navne = sorted(list(set(system_names + manual_names)))
        
        with c1:
            valgt_navn = st.selectbox("Vælg Spiller", options=alle_navne)
            navn = valgt_navn
            if valgt_navn in system_names:
                info = df_spillere[df_spillere['NAVN'] == valgt_navn].iloc[0]
                p_id = str(info['PLAYER_WYID']).split('.')[0]
                pos_raw = info.get('POS', '')
                pos_default = POS_MAP.get(int(pos_raw) if str(pos_raw).replace('.0','').isdigit() else pos_raw, str(pos_raw))
                klub_default = info.get('HOLD', 'Hvidovre IF')
            else:
                info = scouted_names[scouted_names['Navn'] == valgt_navn].iloc[0]
                p_id, pos_default, klub_default = info['ID'], info['Position'], info['Klub']
            
            st.markdown(f"<p class='id-label'>ID: {p_id}</p>", unsafe_allow_html=True)
            
        with c2: pos_val = st.text_input("Position", value=pos_default)
        with c3: klub = st.text_input("Klub", value=klub_default)
        
    else:
        with c1: 
            navn = st.text_input("Spillernavn", placeholder="Navn...")
            p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"
            st.markdown(f"<p class='id-label'>ID: {p_id} (Auto-genereret)</p>", unsafe_allow_html=True)
        with c2: pos_val = st.text_input("Position", placeholder="f.eks. CB")
        with c3: klub = st.text_input("Klub", placeholder="Klub...")

    # --- FORMULAR ---
    with st.form("scout_form", clear_on_submit=True):
        st.write("**Parametre (1-6)**")
        
        # Række 1
        r1_1, r1_2, r1_3, r1_4 = st.columns(4)
        with r1_1: beslut = st.select_slider("Beslutsomhed", options=[1,2,3,4,5,6], value=1)
        with r1_2: fart = st.select_slider("Fart", options=[1,2,3,4,5,6], value=1)
        with r1_3: aggres = st.select_slider("Aggresivitet", options=[1,2,3,4,5,6], value=1)
        with r1_4: attitude = st.select_slider("Attitude", options=[1,2,3,4,5,6], value=1)

        # Række 2
        r2_1, r2_2, r2_3, r2_4 = st.columns(4)
        with r2_1: udhold = st.select_slider("Udholdenhed", options=[1,2,3,4,5,6], value=1)
        with r2_2: leder = st.select_slider("Lederegenskaber", options=[1,2,3,4,5,6], value=1)
        with r2_3: teknik = st.select_slider("Tekniske færdigheder", options=[1,2,3,4,5,6], value=1)
        with r2_4: intel = st.select_slider("Spilintelligens", options=[1,2,3,4,5,6], value=1)

        st.divider()
        
        m1, m2, m_empty = st.columns([1, 1, 2])
        with m1: status = st.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        with m2: potentiale = st.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        st.write("**Vurdering**")
        t1, t2, t3 = st.columns(3)
        with t1: styrker = st.text_area("Styrker")
        with t2: udvikling = st.text_area("Udviklingsområder")
        with t3: vurdering = st.text_area("Samlet vurdering")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn and p_id:
                avg_rating = round(sum([beslut, fart, aggres, attitude, udhold, leder, teknik, intel]) / 8, 1)
                
                # Opret DataFrame til den nye række
                ny_data = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), navn, klub, pos_val, 
                    avg_rating, status, potentiale, styrker, udvikling, vurdering,
                    beslut, fart, aggres, attitude, udhold, leder, teknik, intel
                ]], columns=["ID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status", "Potentiale", "Styrker", "Udvikling", "Vurdering", "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"])
                
                # Kør gemme-funktionen
                status_code = save_to_github(ny_data)
                
                if status_code in [200, 201]:
                    st.success(f"Rapport gemt i {FILE_PATH}!")
                    st.balloons()
                else: 
                    st.error(f"Fejl ved gem: {status_code}. Tjek dine GITHUB_TOKEN rettigheder.")
            else: 
                st.error("Udfyld venligst navn.")
