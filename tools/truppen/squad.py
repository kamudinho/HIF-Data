import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
from datetime import datetime
import matplotlib.pyplot as plt

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/emneliste.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

# --- GITHUB FUNKTIONER ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8')
        return content, data['sha']
    return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

# --- MODAL: SPILLERPROFIL ---
@st.dialog("Spillerprofil: Emne", width="large")
def vis_emne_modal(valgt_navn, emne_data, alle_scout_rapporter):
    nyeste = emne_data[emne_data['Navn'] == valgt_navn].iloc[0]
    rapporter = alle_scout_rapporter[alle_scout_rapporter['Navn'] == valgt_navn] if alle_scout_rapporter is not None else pd.DataFrame()
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1: st.image("https://cdn.pixabay.com/photo/2016/08/08/09/17/avatar-1577909_1280.png", width=120)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"**Klub:** {nyeste.get('Klub', '-')}")
        st.write(f"**Status:** {nyeste.get('Prioritet', '-')} ({nyeste.get('Pos_Prioritet', '-')})")
    with c3:
        st.metric("Pos (Tal)", nyeste.get('Pos_Tal', '-'))
        st.write(f"**Løn:** {nyeste.get('Lon', '-')}")

    t1, t2 = st.tabs(["Detaljer", "Scout Historik"])
    with t1:
        col_a, col_b = st.columns(2)
        col_a.info(f"**Bemærkning:**\n\n{nyeste.get('Bemaerkning', '-')}")
        col_b.write(f"**Kontraktudløb:** {nyeste.get('Kontrakt', '-')}")
        col_b.write(f"**Oprettet af:** {nyeste.get('Oprettet_af', '-')}")
    with t2:
        if not rapporter.empty:
            for _, r in rapporter.sort_values('Dato', ascending=False).iterrows():
                with st.expander(f"Rapport d. {r['Dato']}"):
                    st.write(r.get('Vurdering', '-'))
        else:
            st.info("Ingen rapporter fundet.")

# --- HOVEDSIDE ---
def vis_side(dp):
    # 1. DATA LOADING
    content, sha = get_github_file(FILE_PATH)
    if not content:
        st.error("Kunne ikke hente emneliste.csv.")
        return
    df = pd.read_csv(StringIO(content))
    if 'Skyggehold' not in df.columns: df['Skyggehold'] = False
    df['Skyggehold'] = df['Skyggehold'].fillna(False).astype(bool)

    # 2. TABS
    tab_emner, tab_skygge = st.tabs(["Emner", "Skyggehold"])

    # --- TAB: EMNER (TABELLEN) ---
    with tab_emner:
        vis_kun_skygge = st.toggle("🛡️ Vis kun Skyggehold spillere", value=False)
        df_filtered = df[df['Skyggehold'] == True] if vis_kun_skygge else df
        df_filtered = df_filtered.sort_values(['Pos_Tal', 'Pos_Prioritet'])

        df_display = df_filtered.copy()
        df_display['ℹ️'] = False
        df_display['🗑️'] = False
        df_display = df_display.rename(columns={'Skyggehold': '🛡️'})

        data_cols = ['Navn', 'Position', 'Klub', 'Pos_Tal', 'Pos_Prioritet', 'Prioritet', 'Lon', 'Kontrakt']
        cols_order = ['ℹ️'] + data_cols + ['🛡️', '🗑️']
        
        ed_result = st.data_editor(
            df_display[cols_order],
            column_config={
                "ℹ️": st.column_config.CheckboxColumn("Info", width="small"),
                "🛡️": st.column_config.CheckboxColumn("Skygge", width="small"),
                "🗑️": st.column_config.CheckboxColumn("Slet", width="small"),
                "Pos_Tal": "POS", "Pos_Prioritet": "Kat.", "Lon": "Løn"
            },
            disabled=data_cols, hide_index=True, use_container_width=True, key="emne_db_editor"
        )

        # Logik for interaktion i tabellen
        if not ed_result['ℹ️'].equals(df_display['ℹ️']):
            valgt_navn = ed_result[ed_result["ℹ️"] == True].iloc[-1]['Navn']
            scout_content, _ = get_github_file("data/scouting_db.csv")
            df_rapporter = pd.read_csv(StringIO(scout_content)) if scout_content else None
            vis_emne_modal(valgt_navn, df, df_rapporter)

        if not ed_result['🗑️'].equals(df_display['🗑️']):
            navn_slet = ed_result[ed_result["🗑️"] == True].iloc[-1]['Navn']
            if st.button(f"Bekræft sletning af {navn_slet}"):
                push_to_github(FILE_PATH, f"Slettede {navn_slet}", df[df['Navn'] != navn_slet].to_csv(index=False), sha)
                st.rerun()

        if not ed_result['🛡️'].equals(df_display['🛡️']):
            for idx, row in ed_result.iterrows():
                df.loc[df['Navn'] == row['Navn'], 'Skyggehold'] = row['🛡️']
            push_to_github(FILE_PATH, "Opdateret Skyggehold status", df.to_csv(index=False), sha)
            st.rerun()

    # --- TAB: SKYGGEHOLD (BANEN) ---
    with tab_skygge:
        df_skygge = df[df['Skyggehold'] == True].copy()
        
        if df_skygge.empty:
            st.info("Ingen spillere er valgt til skyggeholdet endnu. Brug i Emner-fanen.")
        else:
            col_pitch, col_menu = st.columns([7, 1])
            
            with col_menu:
                if 'formation_emne' not in st.session_state: st.session_state.formation_emne = "4-3-3"
                for f in ["3-4-3", "4-3-3", "3-5-2"]:
                    if st.button(f, key=f"btn_{f}", use_container_width=True, 
                                 type="primary" if st.session_state.formation_emne == f else "secondary"):
                        st.session_state.formation_emne = f
                        st.rerun()

            with col_pitch:
                pitch = Pitch(pitch_type='statsbomb', pitch_color='#ffffff', line_color='#333', linewidth=1, pad_top=0)
                fig, ax = pitch.draw(figsize=(13, 8))
                
                # Formation Positions Map
                form = st.session_state.formation_emne
                if form == "3-4-3":
                    pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
                                 5: (60, 10, 'VWB'), 6: (60, 30, 'DM'), 8: (60, 50, 'DM'), 7: (60, 70, 'HWB'), 
                                 11: (85, 15, 'VW'), 9: (100, 40, 'ANG'), 10: (85, 65, 'HW')}
                elif form == "4-3-3":
                    pos_config = {1: (10, 40, 'MM'), 5: (35, 10, 'VB'), 4: (33, 25, 'VCB'), 3: (33, 55, 'HCB'), 2: (35, 70, 'HB'),
                                 6: (50, 40, 'DM'), 8: (68, 25, 'VCM'), 10: (68, 55, 'HCM'),
                                 11: (85, 15, 'VW'), 9: (100, 40, 'ANG'), 7: (85, 65, 'HW')}
                else: # 3-5-2
                    pos_config = {1: (10, 40, 'MM'), 4: (33, 22, 'VCB'), 3: (33, 40, 'CB'), 2: (33, 58, 'HCB'),
                                 5: (60, 10, 'VWB'), 6: (60, 40, 'DM'), 7: (60, 70, 'HWB'), 
                                 8: (70, 25, 'CM'), 10: (70, 55, 'CM'), 11: (100, 28, 'ANG'), 9: (100, 52, 'ANG')}

                # Tegn spillere på banen
                for pos_num, (x, y, label) in pos_config.items():
                    spillere = df_skygge[df_skygge['Pos_Tal'].astype(float) == float(pos_num)]
                    
                    # Position Label (MM, CB, etc)
                    ax.text(x, y - 4, f" {label} ", size=9, color="white", fontweight='bold', ha='center',
                            bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                    
                    if not spillere.empty:
                        for i, (_, p) in enumerate(spillere.iterrows()):
                            # Farvekode baseret på Kat. (Pos_Prioritet)
                            kat = str(p['Pos_Prioritet'])[0] # A, B eller C
                            color = "#e8f5e9" if kat == 'A' else "#fffde7" if kat == 'B' else "white"
                            
                            ax.text(x, (y - 1) + (i * 2.5), f" {p['Navn']} ", size=8.5, fontweight='bold', ha='center', va='top',
                                    bbox=dict(facecolor=color, edgecolor='#333', boxstyle='square,pad=0.2', linewidth=0.5))

                st.pyplot(fig, use_container_width=True)
