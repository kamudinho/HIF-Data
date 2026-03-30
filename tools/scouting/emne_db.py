import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
from datetime import datetime

# --- 1. KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

# Mapping af de rå værdier fra din CSV (både som tal og tekst)
POS_OPTIONS = {
    "0": "Vælg position", "1": "Målmand", "2": "Højre back", "5": "Venstre back",
    "4": "Midtstopper (V)", "3.5": "Midtstopper (C)", "3": "Midtstopper (H)",
    "6": "Defensiv midt", "8": "Central midt", "7": "Højre kant",
    "11": "Venstre kant", "10": "Offensiv midt", "9": "Angriber"
}

# --- 2. GITHUB KOMMUNIKATION ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
        return content, data['sha']
    return None, None

def push_to_github(path, message, content, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

# --- 3. MODAL: SPILLERPROFIL ---
@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, df_full):
    # Find alle rapporter på spilleren
    spiller_historik = df_full[df_full['Navn'] == valgt_navn].sort_values('DATO', ascending=False)
    nyeste = spiller_historik.iloc[0]
    
    # Hent billede via PLAYER_WYID
    pid = str(nyeste.get('PLAYER_WYID', '')).split('.')[0]
    img_url = f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150, fallback="https://via.placeholder.com/150")
    with c2:
        st.subheader(valgt_navn)
        st.write(f"**Klub:** {nyeste.get('KLUB', '-')} | **Pos:** {nyeste.get('POSITION', '-')}")
        st.write(f"**Rating:** {nyeste.get('RATING_AVG', 0)} | **Status:** {nyeste.get('STATUS', '-')}")
        st.write(f"**Prioritet:** {nyeste.get('PRIORITET', '-')}")

    t1, t2, t3 = st.tabs(["Seneste Rapport", "Historik", "Udvikling"])
    
    with t1:
        st.success(f"**Styrker:**\n\n{nyeste.get('STYRKER', '-')}")
        st.info(f"**Vurdering:**\n\n{nyeste.get('VURDERING', '-')}")
        if nyeste.get('KONTRAKT'):
            st.warning(f"**Kontraktudløb:** {nyeste.get('KONTRAKT')}")

    with t2:
        for _, rap in spiller_historik.iterrows():
            d = rap['DATO'].strftime('%d/%m-%Y') if not pd.isna(rap['DATO']) else "Ukendt dato"
            with st.expander(f"Rapport fra {d} (Rating: {rap['RATING_AVG']})"):
                st.write(f"**Scout:** {rap.get('SCOUT', '-')}")
                st.write(f"**Beskrivelse:** {rap.get('VURDERING', '-')}")

    with t3:
        hist_evo = spiller_historik.sort_values('DATO')
        fig = go.Figure(go.Scatter(x=hist_evo['DATO'], y=hist_evo['RATING_AVG'], mode='lines+markers', line_color=HIF_ROD))
        fig.update_layout(yaxis=dict(range=[0, 6], title="Rating"), height=300)
        st.plotly_chart(fig, use_container_width=True)

# --- 4. HOVEDAPP ---
def vis_side():
    st.set_page_config(page_title="HIF Scouting System", layout="wide")
    
    if "active_player" not in st.session_state: st.session_state.active_player = None
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    # Hent data
    content, sha = get_github_file(DB_PATH)
    if not content:
        st.error("Kunne ikke forbinde til GitHub-databasen.")
        return

    # Læs og rens data
    df_raw = pd.read_csv(StringIO(content))
    df_raw.columns = [c.strip() for c in df_raw.columns] # Fjern mellemrum i kolonnenavne
    
    df = df_raw.copy()
    # Rens alle tekst-kolonner for usynlige mellemrum
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.strip()

    # Konverter datoer og ratings
    df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
    df['RATING_AVG'] = pd.to_numeric(df['RATING_AVG'], errors='coerce').fillna(0)
    
    # Robust Skyggehold-check (håndterer både True, TRUE og 'True ')
    df['SKYGGE_BOOL'] = df['SKYGGEHOLD'].str.upper().isin(['TRUE', '1', 'YES'])

    # Unik liste over spillere (nyeste rapport altid øverst)
    df_unique = df.sort_values('DATO', ascending=False).drop_duplicates('Navn').copy()

    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste", "🏟️ Banevisning"])

    # Filtrering af Hvidovre vs Emner
    is_hif = df_unique['KLUB'].str.contains("Hvidovre", case=False, na=False)
    df_hif = df_unique[is_hif]
    df_emner = df_unique[~is_hif]

    # --- LISTER (TAB 1 & 2) ---
    for tab, data, label in [(tab1, df_emner, "emner"), (tab2, df_hif, "hif")]:
        with tab:
            if data.empty:
                st.info("Ingen spillere fundet her.")
                continue

            df_disp = data[['Navn', 'KLUB', 'POSITION', 'RATING_AVG', 'SKYGGE_BOOL']].copy()
            df_disp.insert(0, "Se", False)
            
            h = (len(df_disp) + 1) * 35 + 20
            ed = st.data_editor(
                df_disp,
                column_config={
                    "Se": st.column_config.CheckboxColumn("Profil", width="small"),
                    "SKYGGE_BOOL": st.column_config.CheckboxColumn("Skygge", width="small"),
                    "RATING_AVG": st.column_config.NumberColumn("Rating", format="%.1f")
                },
                disabled=['Navn', 'KLUB', 'POSITION', 'RATING_AVG'],
                hide_index=True, use_container_width=True, height=h, key=f"ed_{label}"
            )

            # Hvis man trykker på "Se" (Profil)
            if ed["Se"].any():
                st.session_state.active_player = ed[ed["Se"] == True].iloc[-1]["Navn"]
                st.rerun()

            # Hvis man ændrer Skygge-status
            if not ed['SKYGGE_BOOL'].equals(df_disp['SKYGGE_BOOL']):
                for idx, row in ed.iterrows():
                    df_raw.loc[df_raw['Navn'].str.strip() == row['Navn'], 'SKYGGEHOLD'] = str(row['SKYGGE_BOOL'])
                push_to_github(DB_PATH, "Update Skyggehold", df_raw.to_csv(index=False), sha)
                st.rerun()

    # --- SKYGGELISTE TAKTIK (TAB 3) ---
    with tab3:
        df_s = df_unique[df_unique['SKYGGE_BOOL'] == True].copy()
        if not df_s.empty:
            t_cols = ['POS_343', 'POS_433', 'POS_352']
            # Rens tal-formater (3.5 -> "3.5")
            for c in t_cols:
                df_s[c] = df_s[c].astype(str).str.replace('nan', '0').apply(lambda x: x.split('.')[0] if x.endswith('.0') else x)

            ed_s = st.data_editor(
                df_s[['Navn'] + t_cols],
                column_config={c: st.column_config.SelectboxColumn(c.replace('POS_', ''), options=list(POS_OPTIONS.keys())) for c in t_cols},
                disabled=['Navn'], hide_index=True, use_container_width=True, key="ed_taktik"
            )
            
            if not ed_s[t_cols].equals(df_s[t_cols]):
                for _, row in ed_s.iterrows():
                    df_raw.loc[df_raw['Navn'].str.strip() == row['Navn'], t_cols] = row[t_cols].values
                push_to_github(DB_PATH, "Update Taktiske Positioner", df_raw.to_csv(index=False), sha)
                st.rerun()
        else:
            st.info("Marker spillere med 'Skygge' i oversigterne for at se dem her.")

    # --- BANEVISNING (TAB 4) ---
    with tab4:
        df_pitch_data = df_unique[df_unique['SKYGGE_BOOL'] == True].copy()
        f = st.session_state.form_skygge
        p_col = f"POS_{f.replace('-', '')}"
        
        c1, c2 = st.columns([5, 1])
        with c2:
            st.write("**Formation**")
            for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(opt, type="primary" if f == opt else "secondary", use_container_width=True):
                    st.session_state.form_skygge = opt
                    st.rerun()
        with c1:
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
            fig, ax = pitch.draw(figsize=(10, 7))
            
            # Formationer og koordinater
            if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
            elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
            else: m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}

            for pid, (x, y, lbl) in m.items():
                ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                # Find og tegn spillere for positionen
                players = df_pitch_data[df_pitch_data[p_col].astype(str).str.startswith(str(pid))]
                for i, (_, p) in enumerate(players.iterrows()):
                    ax.text(x, y+(i*4), p['Navn'], size=8, ha='center', weight='bold', bbox=dict(facecolor='white', edgecolor='#333', alpha=0.8, boxstyle='square,pad=0.1'))
            st.pyplot(fig)

    # Vis dialog hvis en spiller er valgt
    if st.session_state.active_player:
        vis_spiller_modal(st.session_state.active_player, df)
        st.session_state.active_player = None

if __name__ == "__main__":
    vis_side()
