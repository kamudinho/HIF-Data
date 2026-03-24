import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
import matplotlib.pyplot as plt

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
EMNE_PATH = "data/emneliste.csv"
HIF_PATH = "data/players.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

# --- GITHUB FUNKTIONER ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
        return content, data['sha']
    return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {
        "message": message, 
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
    }
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

# --- HJÆLPEFUNKTION: TEGN SPILLER TABEL ---
def tegn_spiller_tabel(df_input, key_suffix, sha, path, kan_slettes=True):
    """Viser en editor-tabel og håndterer opdateringer af Skygge-status og sletning."""
    df_temp = df_input.copy()
    
    # Standardisér navne-kolonne
    if 'NAVN' in df_temp.columns: df_temp = df_temp.rename(columns={'NAVN': 'Navn'})
    
    # Tilføj interaktive kolonner hvis de mangler
    df_temp['ℹ️'] = False
    if 'Skyggehold' not in df_temp.columns: df_temp['Skyggehold'] = False
    df_temp = df_temp.rename(columns={'Skyggehold': '🛡️'})
    
    # Definér kolonner og deres rækkefølge
    data_cols = ['Navn', 'Position', 'Klub', 'Pos_Tal', 'Pos_Prioritet', 'Prioritet', 'Lon', 'Kontrakt']
    # Filterer kun de kolonner der faktisk findes i datasættet
    present_cols = [c for c in data_cols if c in df_temp.columns]
    
    if kan_slettes:
        df_temp['🗑️'] = False
        display_cols = ['ℹ️'] + present_cols + ['🛡️', '🗑️']
    else:
        display_cols = ['ℹ️'] + present_cols + ['🛡️']

    # Vis tabellen
    ed_res = st.data_editor(
        df_temp[display_cols],
        column_config={
            "ℹ️": st.column_config.CheckboxColumn("Info", width="small"),
            "🛡️": st.column_config.CheckboxColumn("Skygge", width="small"),
            "🗑️": st.column_config.CheckboxColumn("Slet", width="small"),
            "Pos_Tal": "POS", "Pos_Prioritet": "Kat."
        },
        disabled=present_cols,
        hide_index=True,
        use_container_width=True,
        key=f"ed_{key_suffix}"
    )

    # LOGIK: Gem Skygge-status ved ændring
    if not ed_res['🛡️'].equals(df_temp['🛡️']):
        for idx, row in ed_res.iterrows():
            # Find den originale række og opdater Skyggehold-kolonnen
            name_val = row['Navn']
            df_input.loc[df_input.get('Navn', df_input.get('NAVN')) == name_val, 'Skyggehold'] = row['🛡️']
        
        csv_data = df_input.to_csv(index=False, encoding='utf-8')
        push_to_github(path, "Opdateret Skygge-status", csv_data, sha)
        st.rerun()

    # LOGIK: Sletning (Kun hvis tilladt)
    if kan_slettes and '🗑️' in ed_res.columns:
        if not ed_res['🗑️'].equals(df_temp['🗑️']):
            slet_navn = ed_res[ed_res['🗑️'] == True].iloc[-1]['Navn']
            if st.button(f"Bekræft sletning af {slet_navn}"):
                ny_df = df_input[df_input.get('Navn', df_input.get('NAVN')) != slet_navn]
                push_to_github(path, f"Slettede {slet_navn}", ny_df.to_csv(index=False), sha)
                st.rerun()

# --- HOVEDSIDE ---
def vis_side(dp):
    # 1. INDLÆS DATA
    emne_content, emne_sha = get_github_file(EMNE_PATH)
    hif_content, hif_sha = get_github_file(HIF_PATH)
    
    df_emner = pd.read_csv(StringIO(emne_content)) if emne_content else pd.DataFrame()
    df_hif = pd.read_csv(StringIO(hif_content)) if hif_content else pd.DataFrame()

    # Sørg for booleans er rigtige
    for d in [df_emner, df_hif]:
        if not d.empty and 'Skyggehold' in d.columns:
            d['Skyggehold'] = d['Skyggehold'].fillna(False).astype(bool)

    # 2. DEFINÉR TABS
    tab_emner, tab_hif, tab_liste, tab_bane = st.tabs(["🔍 Emner", "🔴 Hvidovre IF", "📋 Skyggeliste", "🏟️ Skyggehold"])

    # --- TAB 1: EMNER ---
    with tab_emner:
        if not df_emner.empty:
            tegn_spiller_tabel(df_emner, "emner", emne_sha, EMNE_PATH, kan_slettes=True)
        else:
            st.info("Ingen emner i listen.")

    # --- TAB 2: HVIDOVRE IF ---
    with tab_hif:
        if not df_hif.empty:
            # Her kan de IKKE slettes
            tegn_spiller_tabel(df_hif, "hif", hif_sha, HIF_PATH, kan_slettes=False)
        else:
            st.info("Ingen spillere fundet i players.csv.")

    # --- TAB 3: SKYGGELISTE ---
    with tab_liste:
        # Saml alle spillere markeret som Skyggehold fra begge lister
        s_e = df_emner[df_emner['Skyggehold'] == True] if 'Skyggehold' in df_emner.columns else pd.DataFrame()
        s_h = df_hif[df_hif['Skyggehold'] == True] if 'Skyggehold' in df_hif.columns else pd.DataFrame()
        
        # Standardisér kolonner før concat
        if not s_h.empty and 'NAVN' in s_h.columns: s_h = s_h.rename(columns={'NAVN': 'Navn'})
        if not s_h.empty: s_h['Klub'] = 'Hvidovre IF'
        
        df_samlet = pd.concat([s_e, s_h], ignore_index=True)
        
        if df_samlet.empty:
            st.info("Ingen spillere valgt til skyggeholdet. Brug 🛡️ i de andre faner.")
        else:
            st.subheader("📋 Samlet Skyggeliste")
            st.dataframe(
                df_samlet[['Pos_Tal', 'Navn', 'Position', 'Klub', 'Pos_Prioritet', 'Prioritet']].sort_values('Pos_Tal'),
                use_container_width=True, hide_index=True
            )

    # --- TAB 4: SKYGGEHOLD (BANEN) ---
    with tab_bane:
        if df_samlet.empty:
            st.info("Ingen spillere at vise på banen.")
        else:
            # Logik for formationsvalg
            if 'form_emne' not in st.session_state: st.session_state.form_emne = "4-3-3"
            f_cols = st.columns(3)
            for i, f in enumerate(["3-4-3", "4-3-3", "3-5-2"]):
                if f_cols[i].button(f, use_container_width=True, type="primary" if st.session_state.form_emne == f else "secondary"):
                    st.session_state.form_emne = f
                    st.rerun()

            # Tegn banen
            pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333', linewidth=1)
            fig, ax = pitch.draw(figsize=(10, 7))
            
            # Formations-mapping (forkortet for overblik)
            form = st.session_state.form_emne
            if form == "4-3-3":
                pos_map = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(33,25,'VCB'), 3:(33,55,'HCB'), 2:(35,70,'HB'), 
                           6:(50,40,'DM'), 8:(68,25,'VCM'), 10:(68,55,'HCM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
            elif form == "3-4-3":
                pos_map = {1:(10,40,'MM'), 4:(33,20,'VCB'), 3:(33,40,'CB'), 2:(33,60,'HCB'), 5:(60,10,'VWB'), 
                           6:(60,30,'DM'), 8:(60,50,'DM'), 7:(60,70,'HWB'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 10:(85,65,'HW')}
            else: # 3-5-2
                pos_map = {1:(10,40,'MM'), 4:(33,20,'VCB'), 3:(33,40,'CB'), 2:(33,60,'HCB'), 5:(60,10,'VWB'), 
                           6:(60,40,'DM'), 7:(60,70,'HWB'), 8:(75,25,'CM'), 10:(75,55,'CM'), 11:(100,30,'ANG'), 9:(100,50,'ANG')}

            for p_num, (x, y, label) in pos_map.items():
                # Tegn position label
                ax.text(x, y-4, label, color="white", size=8, fontweight='bold', ha='center',
                        bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                
                # Tegn spillere på denne position
                spillere = df_samlet[df_samlet['Pos_Tal'].astype(float) == float(p_num)]
                for i, (_, p) in enumerate(spillere.iterrows()):
                    # Farveforskel: HIF (Rødlig) vs Emner (Hvid/Grønlig)
                    is_hif = p['Klub'] == 'Hvidovre IF'
                    bg_color = "#ffebee" if is_hif else "#f1f8e9"
                    
                    ax.text(x, y + (i*3), p['Navn'], size=8, ha='center', va='top', fontweight='bold',
                            bbox=dict(facecolor=bg_color, edgecolor='#333', boxstyle='square,pad=0.2'))

            st.pyplot(fig)
