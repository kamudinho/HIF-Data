import streamlit as st
import pandas as pd
import requests
import base64
from datetime import datetime
import uuid

# --- KONFIGURATION OG ADGANG ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

POS_MAP = {
    1: "MM", 2: "HB", 3: "CB", 4: "CB", 5: "VB", 
    6: "DM", 8: "CM", 7: "Højre kant", 11: "Venstre kant", 
    9: "Angriber", 10: "Offensiv midtbane"
}

def save_to_github(new_row_df):
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()
        sha = content['sha']
        old_csv = base64.b64decode(content['content']).decode('utf-8')
        new_row_str = ",".join([f'"{str(x)}"' for x in new_row_df.values[0]])
        updated_csv = old_csv.strip() + "\n" + new_row_str
    else:
        sha = None
        updated_csv = ",".join(new_row_df.columns) + "\n" + ",".join([f'"{str(x)}"' for x in new_row_df.values[0]])
    payload = {
        "message": f"Scouting: {new_row_df['Navn'].values[0]}",
        "content": base64.b64encode(updated_csv.encode('utf-8')).decode('utf-8'),
        "sha": sha if sha else ""
    }
    res = requests.put(url, json=payload, headers=headers)
    return res.status_code

def vis_side(df_spillere):
    # CSS der kun strammer op uden at ødelægge labels
    st.markdown("""
        <style>
            [data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
            .stSlider { margin-bottom: -10px !important; }
            .stTextArea textarea { height: 110px !important; }
        </style>
    """, unsafe_allow_html=True)

    st.write("#### Opret Scoutingrapport")
    
    # --- DATA HENTNING ---
    try:
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db_scout = pd.read_csv(raw_url)
        scouted_names = db_scout[['Navn', 'Klub', 'Position', 'ID']].drop_duplicates('Navn')
    except:
        scouted_names = pd.DataFrame(columns=['Navn', 'Klub', 'Position', 'ID'])

    kilde_type = st.radio("Metode", ["Find i system / Tidligere scoutet", "Opret helt ny"], horizontal=True, label_visibility="collapsed")
    
    p_id, navn, klub, pos_val = "", "", "", ""

    # --- BASIS INFORMATION (3 kolonner) ---
    c1, c2, c3 = st.columns([2, 1, 1])
    if kilde_type == "Find i system / Tidligere scoutet":
        system_names = sorted(df_spillere['NAVN'].unique().tolist())
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
        with c2: pos_val = st.text_input("Position", value=pos_default)
        with c3: klub = st.text_input("Klub", value=klub_default)
    else:
        with c1: navn = st.text_input("Spillernavn", placeholder="Navn...")
        with c2: pos_val = st.text_input("Position", placeholder="f.eks. CB")
        with c3: klub = st.text_input("Klub", placeholder="Klub...")
        p_id = f"MAN-{datetime.now().strftime('%y%m%d')}-{str(uuid.uuid4())[:4]}"

    # --- FORMULAR ---
    with st.form("scout_form", clear_on_submit=True):
        st.write("**Parametre (1-6)**")
        
        # Række 1: 4 kolonner
        r1_1, r1_2, r1_3, r1_4 = st.columns(4)
        with r1_1: beslut = st.select_slider("Beslutsomhed", options=[1,2,3,4,5,6], value=3)
        with r1_2: fart = st.select_slider("Fart", options=[1,2,3,4,5,6], value=3)
        with r1_3: aggres = st.select_slider("Aggresivitet", options=[1,2,3,4,5,6], value=3)
        with r1_4: attitude = st.select_slider("Attitude", options=[1,2,3,4,5,6], value=3)

        # Række 2: 4 kolonner
        r2_1, r2_2, r2_3, r2_4 = st.columns(4)
        with r2_1: udhold = st.select_slider("Udholdenhed", options=[1,2,3,4,5,6], value=3)
        with r2_2: leder = st.select_slider("Leder", options=[1,2,3,4,5,6], value=3)
        with r2_3: teknik = st.select_slider("Teknik", options=[1,2,3,4,5,6], value=3)
        with r2_4: intel = st.select_slider("Spilintelligens", options=[1,2,3,4,5,6], value=3)

        st.divider()
        
        # Status og Potentiale
        m1, m2, m_empty = st.columns([1, 1, 2])
        with m1: status = st.selectbox("Status", ["Kig nærmere", "Interessant", "Prioritet", "Køb"])
        with m2: potentiale = st.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])

        st.write("**Vurdering**")
        # Tre kolonner til tekstboksene
        t1, t2, t3 = st.columns(3)
        with t1: styrker = st.text_area("Styrker")
        with t2: udvikling = st.text_area("Udviklingsområder")
        with t3: vurdering = st.text_area("Samlet vurdering")

        if st.form_submit_button("Gem rapport", use_container_width=True):
            if navn and p_id:
                avg_rating = round(sum([beslut, fart, aggres, attitude, udhold, leder, teknik, intel]) / 8, 1)
                ny_data = pd.DataFrame([[
                    p_id, datetime.now().strftime("%Y-%m-%d"), navn, klub, pos_val, 
                    avg_rating, status, potentiale, styrker, udvikling, vurdering,
                    beslut, fart, aggres, attitude, udhold, leder, teknik, intel
                ]], columns=["ID", "Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status", "Potentiale", "Styrker", "Udvikling", "Vurdering", "Beslutsomhed", "Fart", "Aggresivitet", "Attitude", "Udholdenhed", "Lederegenskaber", "Teknik", "Spilintelligens"])
                
                res = save_to_github(ny_data)
                if res in [200, 201]:
                    st.success("Rapport gemt!")
                else: 
                    st.error(f"Fejl ved gem: {res}")
            else: 
                st.error("Udfyld venligst navn.")
