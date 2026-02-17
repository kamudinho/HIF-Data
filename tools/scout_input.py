import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid
from io import StringIO

# --- KONFIGURATION OG ADGANG ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"  # Vi arbejder udelukkende i /data/ mappen

POS_MAP = {
    1: "MM", 2: "HB", 3: "CB", 4: "CB", 5: "VB", 
    6: "DM", 8: "CM", 7: "Højre kant", 11: "Venstre kant", 
    9: "Angriber", 10: "Offensiv midtbane"
}

def save_to_github(new_row_df):
    """Henter eksisterende CSV fra /data/, tilføjer række og uploader."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Hent eksisterende fil
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

    # 2. Upload til GitHub
    payload = {
        "message": f"Scouting: {new_row_df['Navn'].values[0]}",
        "content": base64.b64encode(updated_csv.encode('utf-8')).decode('utf-8'),
        "sha": sha if sha else ""
    }
    
    res = requests.put(url, json=payload, headers=headers)
    return res.status_code

def vis_side(df_spillere):
    """Hovedfunktion for scout-input siden med dublet-rensning."""
    
    st.markdown("""
        <style>
            [data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
            .stSlider { margin-bottom: -10px !important; }
            .stTextArea textarea { height: 110px !important; }
            .id-label { font-size: 12px; color: #666; margin-top: -15px; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.write("#### Scoutrapport")
    
    # --- 1. HENT DATABASE FRA GITHUB ---
    try:
        # Tving frisk hentning med UUID
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db_scout = pd.read_csv(raw_url, sep=None, engine='python')
        db_scout.columns = [c.strip() for c in db_scout.columns]
        
        # Rens navne for usynlige mellemrum i databasen
        db_scout['Navn'] = db_scout['Navn'].astype(str).str.strip()
        scouted_names_df = db_scout[['Navn', 'Klub', 'Position', 'ID']].drop_duplicates('Navn')
    except:
        scouted_names_df = pd.DataFrame(columns=['Navn', 'Klub', 'Position', 'ID'])

    # --- 2. FLET NAVNE OG FJERN DUBLETTER (KONRAD-SIKRING) ---
    # Hent fra systemet (players.csv / Snowflake)
    system_names = []
    if df_spillere is not None and not df_spillere.empty:
        system_names = [str(n).strip() for n in df_spillere['NAVN'].unique().tolist() if n]
    
    # Hent fra scouting databasen
    manual_names = [str(n).strip() for n in scouted_names_df['Navn'].unique().tolist() if n]
    
    # Saml alt i et set (fjerner automatiske dubletter) og sorter
    alle_navne = sorted(list(set(system_names + manual_names)))

    kilde_type = st.radio("Metode", ["Find i systemet", "Opret ny spiller"], horizontal=True, label_visibility="collapsed")
    
    p_id, navn, klub, pos_val = "", "", "", ""
    pos_default, klub_default = "", ""

    # --- 3. BASIS INFORMATION ---
    c1, c2, c3 = st.columns([2, 1, 1])
    
    if kilde_type == "Find i systemet":
        with c1:
            valgt_navn = st.selectbox("Vælg Spiller", options=alle_navne, index=0)
            navn = valgt_navn
            
            # Tjek system-data først
            if valgt_navn in system_names:
                info = df_spillere[df_spillere['NAVN'].str.strip() == valgt_navn].iloc[0]
                p_id = str(info.get('PLAYER_WYID', '0')).split('.')[0]
                pos_raw = info.get('POS', '')
                pos_default = POS_MAP.get(int(pos_raw) if str(pos_raw).replace('.0','').isdigit() else 0, str(pos_raw))
                klub_default = info.get('HOLD', 'Hvidovre IF')
            # Ellers tjek manuel database
            elif valgt_navn in manual_names:
                info = scouted_names_df[scouted_names_df['Navn'] == valgt_navn].iloc[0]
                p_id, pos_default, klub_default = info['ID'], info['Position'], info['Klub']
            
            st.markdown(f"<p class='id-label'>ID: {p_id}</p>", unsafe_allow_html=True)
            
        with c2: pos_val = st.text_input("Position", value=pos_default)
        with c3: klub = st.text_input("Klub", value=klub_default)
        
    else:
        with c1: 
            navn = st.text_input("Spillernavn", placeholder="Indtast navn...")
            p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"
            st.markdown(f"<p class='id-label'>ID: {p_id} (Auto-genereret)</p>", unsafe_allow_html=True)
        with c2: pos_val = st.text_input("Position")
        with c3: klub = st.text_input("Klub")

    # --- 4. FORMULAR ---
    with st.form("scout_form", clear_on_submit=True):
        st.write("**Parametre (1-6)**")
        
        r1 = st.columns(4)
        beslut = r1[0].select_slider("Beslutsomhed", options=[1,2,3,4,5,6], value=1)
        fart = r1[1].select_slider("Fart", options=[1,2,3,4,5,6], value=1)
        aggres = r1[2].select_slider("Aggresivitet", options=[1,2,3,4,5,6], value=1)
        attitude = r1[3].select_slider("Attitude", options=[1,2,3,4,5,6], value=1)

        r2 = st.columns(4)
        udhold = r2[0].select_slider("Udholdenhed", options=[1,2,3,4,5,6], value=1)
        leder = r2[1].select_slider("Lederegenskaber", options=[1,2,3,4,5,6], value=1)
        teknik = r2[2].select_slider("Teknik", options=[1,2,3,4,5,6], value=1)
        intel = r2[3].select_slider("Intelligens", options=[1,2,3,4,5,6], value=1)

        st.divider()
        m1, m2, _ = st.columns([1, 1, 2])
        status = m1.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        potentiale = m2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        st.write("**Vurdering**")
        t1, t2, t3 = st.columns(3)
        styrker = t1.text_area("Styrker")
        udvikling = t2.text_area("Udviklingsområder")
        vurdering = t3.text_area("Samlet vurdering")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn and p_id:
                avg_rating = round(sum([beslut, fart, aggres, attitude, udhold, leder, teknik, intel]) / 8, 1)
                
                ny_data = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), navn, klub, pos_val, 
                    avg_rating, status, potentiale, styrker, udvikling, vurdering,
                    beslut, fart, aggres, attitude, udhold, leder, teknik, intel
                ]], columns=["ID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status", "Potentiale", "Styrker", "Udvikling", "Vurdering", "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"])
                
                if save_to_github(ny_data) in [200, 201]:
                    st.success("Rapport gemt!")
                    st.rerun()
                else: 
                    st.error("Kunne ikke gemme til GitHub. Tjek rettigheder.")
            else: 
                st.error("Udfyld venligst navn.")
