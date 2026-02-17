# tools/scout_input.py
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
FILE_PATH = "data/scouting_db.csv"  # Præcis den sti du har angivet

POS_MAP = {
    1: "MM", 2: "HB", 3: "CB", 4: "CB", 5: "VB", 
    6: "DM", 8: "CM", 7: "Højre kant", 11: "Venstre kant", 
    9: "Angriber", 10: "Offensiv midtbane"
}

def save_to_github(new_row_df):
    """Henter eksisterende CSV fra data/, tilføjer række og uploader."""
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    r = requests.get(url, headers=headers)
    
    if r.status_code == 200:
        content = r.json()
        sha = content['sha']
        old_csv_raw = base64.b64decode(content['content']).decode('utf-8')
        old_df = pd.read_csv(StringIO(old_csv_raw))
        # Saml data og bevar CSV-struktur
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
    """Viser scouting-interfacet med fuld database-integration."""
    
    st.markdown("""
        <style>
            [data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
            .id-label { font-size: 12px; color: #666; margin-top: -15px; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.write("#### Scoutrapport")
    
    # --- 1. LÆS EKSISTERENDE DATA FRA data/scouting_db.csv ---
    try:
        # Tving frisk hentning for at fange nye opdateringer (som f.eks. Konrad)
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db_scout = pd.read_csv(raw_url)
        db_scout.columns = [c.strip() for c in db_scout.columns]
        
        # Rens navne for usynlige mellemrum
        db_scout['Navn'] = db_scout['Navn'].astype(str).str.strip()
        scouted_names_df = db_scout[['Navn', 'Klub', 'Position', 'ID']].drop_duplicates('Navn')
    except:
        scouted_names_df = pd.DataFrame(columns=['Navn', 'Klub', 'Position', 'ID'])

    # --- 2. SAML ALLE NAVNE UDEN DUBLETTER ---
    system_names = []
    if df_spillere is not None and not df_spillere.empty:
        system_names = [str(n).strip() for n in df_spillere['NAVN'].unique().tolist() if n]
    
    manual_names = [str(n).strip() for n in scouted_names_df['Navn'].unique().tolist() if n]
    
    # Set-logik fjerner dubletter (hvis Konrad er i begge lister)
    alle_navne = sorted(list(set(system_names + manual_names)))

    kilde_type = st.radio("Metode", ["Find i systemet", "Opret ny spiller"], horizontal=True, label_visibility="collapsed")
    
    p_id, navn, klub, pos_val = "", "", "", ""

    # --- 3. INPUT SEKTION ---
    c1, c2, c3 = st.columns([2, 1, 1])
    
    if kilde_type == "Find i systemet":
        with c1:
            valgt_navn = st.selectbox("Vælg Spiller", options=alle_navne)
            navn = valgt_navn
            
            # Find info: Tjek først det officielle system
            if valgt_navn in system_names:
                info = df_spillere[df_spillere['NAVN'].str.strip() == valgt_navn].iloc[0]
                p_id = str(info.get('PLAYER_WYID', '0')).split('.')[0]
                pos_raw = info.get('POS', '')
                pos_default = POS_MAP.get(int(pos_raw) if str(pos_raw).replace('.0','').isdigit() else 0, str(pos_raw))
                klub_default = info.get('HOLD', 'Hvidovre IF')
            # Hvis ikke i systemet, så brug data fra din CSV
            else:
                info = scouted_names_df[scouted_names_df['Navn'] == valgt_navn].iloc[0]
                p_id, pos_default, klub_default = info['ID'], info['Position'], info['Klub']
            
            st.markdown(f"<p class='id-label'>ID: {p_id}</p>", unsafe_allow_html=True)
            
        with c2: pos_val = st.text_input("Position", value=pos_default)
        with c3: klub = st.text_input("Klub", value=klub_default)
        
    else:
        with c1: 
            navn = st.text_input("Spillernavn")
            p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"
            st.markdown(f"<p class='id-label'>ID: {p_id}</p>", unsafe_allow_html=True)
        with c2: pos_val = st.text_input("Position")
        with c3: klub = st.text_input("Klub")

    # --- 4. FORMULAR ---
    with st.form("scout_form", clear_on_submit=True):
        st.write("**Parametre (1-6)**")
        r1 = st.columns(4)
        beslut = r1[0].select_slider("Beslutsomhed", options=[1,2,3,4,5,6])
        fart = r1[1].select_slider("Fart", options=[1,2,3,4,5,6])
        aggres = r1[2].select_slider("Aggresivitet", options=[1,2,3,4,5,6])
        att = r1[3].select_slider("Attitude", options=[1,2,3,4,5,6])
        
        r2 = st.columns(4)
        udhold = r2[0].select_slider("Udholdenhed", options=[1,2,3,4,5,6])
        leder = r2[1].select_slider("Lederegenskaber", options=[1,2,3,4,5,6])
        teknik = r2[2].select_slider("Teknik", options=[1,2,3,4,5,6])
        intel = r2[3].select_slider("Intelligens", options=[1,2,3,4,5,6])

        st.divider()
        m1, m2, _ = st.columns([1,1,2])
        status = m1.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        pot = m2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        styrker = st.text_area("Styrker")
        vurdering = st.text_area("Samlet vurdering")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn:
                avg = round(sum([beslut, fart, aggres, att, udhold, leder, teknik, intel]) / 8, 1)
                ny_df = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), navn, klub, pos_val, 
                    avg, status, pot, styrker, vurdering,
                    beslut, fart, aggres, att, udhold, leder, teknik, intel
                ]], columns=["ID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status", "Potentiale", "Styrker", "Vurdering", "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"])
                
                if save_to_github(ny_df) in [200, 201]:
                    st.success("Rapport gemt!")
                    st.rerun()
            else:
                st.error("Navn mangler!")
