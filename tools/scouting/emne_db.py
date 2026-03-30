import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

# Præcis mapping af dine talværdier fra CSV'en
POS_OPTIONS = {
    "0.0": "Vælg", "0": "Vælg",
    "1.0": "Målmand", "1": "Målmand",
    "2.0": "Højre back", "2": "Højre back",
    "5.0": "Venstre back", "5": "Venstre back",
    "4.0": "Midtstopper (V)", "4": "Midtstopper (V)",
    "3.5": "Midtstopper (C)", 
    "3.0": "Midtstopper (H)", "3": "Midtstopper (H)",
    "6.0": "Defensiv midt", "6": "Defensiv midt",
    "8.0": "Central midt", "8": "Central midt",
    "7.0": "Højre kant", "7": "Højre kant",
    "11.0": "Venstre kant", "11": "Venstre kant",
    "10.0": "Offensiv midt", "10": "Offensiv midt",
    "9.0": "Angriber", "9": "Angriber"
}

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
    payload = {"message": message, "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')}
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

# --- MODAL: SPILLERPROFIL ---
@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, df_full):
    spiller_data = df_full[df_full['Navn'] == valgt_navn].sort_values('DATO', ascending=False)
    nyeste = spiller_data.iloc[0]
    
    # Rens WYID til billede
    pid = str(nyeste.get('PLAYER_WYID', '')).split('.')[0]
    img_url = f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150, fallback="https://via.placeholder.com/150")
    with c2:
        st.subheader(valgt_navn)
        st.write(f"**Klub:** {nyeste.get('KLUB', '-')} | **Rating:** {nyeste.get('RATING_AVG', 0)}")
        st.write(f"**Status:** {nyeste.get('STATUS', '-')} | **Prioritet:** {nyeste.get('PRIORITET', '-')}")

    t1, t2 = st.tabs(["Seneste Rapport", "Historik"])
    with t1:
        st.info(f"**Vurdering:**\n\n{nyeste.get('VURDERING', '-')}")
        st.success(f"**Styrker:**\n\n{nyeste.get('STYRKER', '-')}")
    with t2:
        for _, rap in spiller_data.iterrows():
            st.write(f"**{rap['DATO'].date()}:** Rating {rap['RATING_AVG']} - {rap['VURDERING']}")

# --- HOVEDLOGIK ---
def vis_side():
    st.set_page_config(page_title="HIF Scouting", layout="wide")
    
    # Session States
    if "active_player" not in st.session_state: st.session_state.active_player = None
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    # Hent data
    content, sha = get_github_file(DB_PATH)
    if not content:
        st.error("Kunne ikke finde scouting_db.csv")
        return

    # Læs og tving kolonnenavne til korrekt format
    df_raw = pd.read_csv(StringIO(content))
    
    # AUTO-MAPPER: Vi omdøber kolonnerne internt så de matcher koden
    col_map = {c.upper(): c for c in df_raw.columns}
    
    def get_col(target):
        return col_map.get(target.upper(), target)

    # Opret en visnings-DF med standardiserede navne
    df = df_raw.copy()
    df['DATO'] = pd.to_datetime(df[get_col('DATO')], errors='coerce')
    df['Navn'] = df[get_col('Navn')]
    df['KLUB'] = df[get_col('KLUB')]
    df['RATING_AVG'] = pd.to_numeric(df[get_col('RATING_AVG')], errors='coerce').fillna(0)
    
    # Håndtering af Skyggehold (Boolean check)
    skygge_col = get_col('SKYGGEHOLD')
    df['SKYGGE_BOOL'] = df[skygge_col].astype(str).str.upper().str.strip() == 'TRUE'

    # Unik liste (nyeste rapport først)
    df_unique = df.sort_values('DATO', ascending=False).drop_duplicates('Navn').copy()

    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste", "🏟️ Banevisning"])

    # --- LISTER ---
    for tab, filter_val, key in [(tab1, False, "emner"), (tab2, True, "hif")]:
        with tab:
            if filter_val:
                data = df_unique[df_unique['KLUB'] == 'Hvidovre IF']
            else:
                data = df_unique[df_unique['KLUB'] != 'Hvidovre IF']
            
            if data.empty:
                st.info("Ingen spillere i denne kategori.")
                continue

            # Forbered data til editor
            df_editor = data[['Navn', 'KLUB', 'RATING_AVG', 'SKYGGE_BOOL']].copy()
            df_editor.insert(0, "Se", False)
            
            ed = st.data_editor(
                df_editor,
                column_config={
                    "Se": st.column_config.CheckboxColumn("Profil", width="small"),
                    "SKYGGE_BOOL": st.column_config.CheckboxColumn("Skygge", width="small"),
                    "RATING_AVG": st.column_config.NumberColumn("Rating", format="%.1f")
                },
                disabled=['Navn', 'KLUB'],
                hide_index=True, use_container_width=True, key=f"editor_{key}"
            )

            # Gem ændringer i Skyggehold
            if not ed['SKYGGE_BOOL'].equals(df_editor['SKYGGE_BOOL']):
                for idx, row in ed.iterrows():
                    # Find alle rækker for spilleren i den oprindelige df_raw og opdater
                    df_raw.loc[df_raw[get_col('Navn')] == row['Navn'], skygge_col] = row['SKYGGE_BOOL']
                
                push_to_github(DB_PATH, "Update Skyggehold", df_raw.to_csv(index=False), sha)
                st.rerun()

            # Trigger Profil
            if ed["Se"].any():
                st.session_state.active_player = ed[ed["Se"] == True].iloc[-1]["Navn"]
                st.rerun()

    # --- SKYGGELISTE (TAKTISK) ---
    with tab3:
        df_s = df_unique[df_unique['SKYGGE_BOOL'] == True].copy()
        if not df_s.empty:
            # Vi viser taktiske positioner
            taktik_cols = [get_col('POS_343'), get_col('POS_433'), get_col('POS_352')]
            
            # Konverter værdier til string for selectbox (f.eks. 3.5 -> "3.5")
            for c in taktik_cols:
                df_s[c] = df_s[c].astype(str).str.replace('nan', '0').apply(lambda x: x.split('.')[0] if x.endswith('.0') else x)

            ed_s = st.data_editor(
                df_s[['Navn'] + taktik_cols],
                column_config={
                    get_col('POS_343'): st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    get_col('POS_433'): st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    get_col('POS_352'): st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys()))
                },
                disabled=['Navn'], hide_index=True, use_container_width=True
            )
            
            if not ed_s[taktik_cols].equals(df_s[taktik_cols]):
                for _, row in ed_s.iterrows():
                    df_raw.loc[df_raw[get_col('Navn')] == row['Navn'], taktik_cols] = row[taktik_cols].values
                push_to_github(DB_PATH, "Update Taktik", df_raw.to_csv(index=False), sha)
                st.rerun()
        else:
            st.info("Marker spillere med 'Skygge' i oversigterne for at se dem her.")

    # --- BANEVISNING ---
    with tab4:
        df_pitch_data = df_unique[df_unique['SKYGGE_BOOL'] == True].copy()
        f = st.session_state.form_skygge
        p_col = get_col(f"POS_{f.replace('-', '')}")
        
        c1, c2 = st.columns([5, 1])
        with c2:
            for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(opt, type="primary" if f == opt else "secondary", use_container_width=True):
                    st.session_state.form_skygge = opt
                    st.rerun()
        with c1:
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333')
            fig, ax = pitch.draw(figsize=(10, 7))
            
            # Formationer
            if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
            elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
            else: m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}

            for pid, (x, y, lbl) in m.items():
                ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                # Matcher både float-strings ("3.5") og int-strings ("3")
                players = df_pitch_data[df_pitch_data[p_col].astype(str).str.startswith(str(pid))]
                for i, (_, p) in enumerate(players.iterrows()):
                    ax.text(x, y+(i*4), p['Navn'], size=8, ha='center', weight='bold', bbox=dict(facecolor='white', edgecolor='#333', alpha=0.8, boxstyle='square,pad=0.1'))
            st.pyplot(fig)

    # Vis Modal hvis aktiv
    if st.session_state.active_player:
        vis_spiller_modal(st.session_state.active_player, df)
        st.session_state.active_player = None

if __name__ == "__main__":
    vis_side()
