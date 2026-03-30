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
CAREER_PATH = "data/player_career.csv" # Til Tab 4 i modalen
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

POS_OPTIONS = {
    "0": "Ingen", "1": "Målmand", "2": "Højre back", "5": "Venstre back",
    "4": "Midtstopper (V)", "3.5": "Midtstopper (C)", "3": "Midtstopper (H)",
    "6": "Defensiv midt", "8": "Central midt", "7": "Højre kant",
    "11": "Venstre kant", "10": "Offensiv midt", "9": "Angriber"
}

# --- HJÆLPEFUNKTIONER ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

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
def vis_spiller_modal(valgt_navn, alle_rapporter, career_df):
    spiller_historik = alle_rapporter[alle_rapporter['Navn'] == valgt_navn].sort_values('DATO', ascending=False)
    nyeste = spiller_historik.iloc[0]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    img_url = f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    c1, c2 = st.columns([1, 3])
    with c1: st.image(img_url, width=150)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"Klub: {nyeste.get('KLUB', 'Ukendt')} | Pos: {nyeste.get('POSITION', 'Ukendt')}")
        st.write(f"Rating: {nyeste.get('RATING_AVG', 0)} | Potentiale: {nyeste.get('POTENTIALE', '-')}")

    t1, t2, t3, t4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstats"])
    keys = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
    labels = ['Beslut.', 'Fart', 'Aggres.', 'Attitude', 'Udhold.', 'Leder', 'Teknik', 'Intell.']

    with t1:
        col_stats, col_radar, col_text = st.columns([0.8, 1.5, 1.5])
        with col_stats:
            st.markdown("**Vurderinger**")
            for k in keys: st.write(f"**{k.capitalize()}:** {nyeste.get(k, 1)}")
        with col_radar:
            try:
                r_vals = [float(str(nyeste.get(k, 1)).replace(',', '.')) for k in keys]
                fig = go.Figure(data=go.Scatterpolar(r=r_vals + [r_vals[0]], theta=labels + [labels[0]], fill='toself', line_color=HIF_ROD))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 6])), showlegend=False, height=300, margin=dict(l=40,r=40,t=20,b=20))
                st.plotly_chart(fig, use_container_width=True)
            except: st.error("Kunne ikke tegne radar")
        with col_text:
            st.success(f"**Styrker**\n\n{nyeste.get('STYRKER', '-')}")
            st.warning(f"**Udvikling**\n\n{nyeste.get('UDWIKLING', '-')}")
            st.info(f"**Vurdering**\n\n{nyeste.get('VURDERING', '-')}")

    with t2:
        for idx, rap in spiller_historik.iterrows():
            with st.expander(f"Rapport fra {rap['DATO'].date() if hasattr(rap['DATO'], 'date') else rap['DATO']}", expanded=(idx == spiller_historik.index[0])):
                st.write(f"**Scout:** {rap.get('SCOUT', '-')}")
                st.write(f"**Vurdering:** {rap.get('VURDERING', '-')}")

    with t3:
        hist_evo = spiller_historik.sort_values('DATO')
        fig_evo = go.Figure(go.Scatter(x=hist_evo['DATO'], y=hist_evo['RATING_AVG'], mode='lines+markers', line_color=HIF_ROD))
        fig_evo.update_layout(yaxis=dict(range=[1, 6]), height=350)
        st.plotly_chart(fig_evo, use_container_width=True)

    with t4:
        if career_df is not None and not career_df.empty:
            p_stats = career_df[career_df['PLAYER_WYID'].apply(rens_id) == pid].copy()
            if not p_stats.empty:
                st.dataframe(p_stats, use_container_width=True, hide_index=True)
            else: st.info("Ingen stats fundet.")

# --- HOVEDSIDE LOGIK ---
def vis_side():
    st.set_page_config(page_title="HIF Scouting", layout="wide")
    
    if "active_player" not in st.session_state: st.session_state.active_player = None
    if "editor_key" not in st.session_state: st.session_state.editor_key = 0
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    # Hent Data
    db_content, db_sha = get_github_file(DB_PATH)
    career_content, _ = get_github_file(CAREER_PATH)
    
    if not db_content: return

    df_raw = pd.read_csv(StringIO(db_content))
    df_raw.columns = [str(c).upper().strip() for c in df_raw.columns]
    if 'NAVN' in df_raw.columns: df_raw = df_raw.rename(columns={'NAVN': 'Navn'})
    df_raw['DATO'] = pd.to_datetime(df_raw['DATO'], errors='coerce')
    
    career_df = pd.read_csv(StringIO(career_content)) if career_content else None
    
    df_unique = df_raw.sort_values('DATO', ascending=False).drop_duplicates('Navn').copy()
    df_unique['VIS_DATO'] = df_unique['DATO'].dt.date
    df_unique['SKYGGEHOLD'] = df_unique['SKYGGEHOLD'].fillna(False).replace({'True':True, 'False':False, '1':True, '0':False, 1:True, 0:False}).astype(bool)

    t1, t2, t3, t4 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste", "🏟️ Banevisning"])

    df_hif = df_unique[df_unique['KLUB'] == 'Hvidovre IF'].copy()
    df_emner = df_unique[df_unique['KLUB'] != 'Hvidovre IF'].copy()

    # --- TAB 1 & 2: OVERSIGTSLISTER ---
    for tab, data, label in [(t1, df_emner, "emne"), (t2, df_hif, "hif")]:
        with tab:
            if data.empty: 
                st.info("Ingen spillere fundet.")
                continue
            
            df_disp = data[['Navn', 'KLUB', 'POSITION', 'RATING_AVG', 'POTENTIALE', 'VIS_DATO', 'SKYGGEHOLD']].copy()
            df_disp.insert(0, "Se", False)
            
            h = (len(df_disp) + 1) * 35 + 15
            ed = st.data_editor(
                df_disp,
                column_config={
                    "Se": st.column_config.CheckboxColumn("Profil", default=False, width="small"),
                    "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge", default=False, width="small"),
                    "RATING_AVG": st.column_config.NumberColumn("Rating", format="%.1f")
                },
                disabled=['Navn', 'KLUB', 'POSITION', 'POTENTIALE', 'VIS_DATO'],
                hide_index=True, use_container_width=True, height=h, key=f"ed_{label}_{st.session_state.editor_key}"
            )

            # Check for profil-klik
            valgte_profil = ed[ed["Se"] == True]
            if not valgte_profil.empty:
                st.session_state.active_player = valgte_profil.iloc[-1]['Navn']
                st.session_state.editor_key += 1
                st.rerun()

            # Check for Skyggehold-ændring og gem til GitHub
            if not ed['SKYGGEHOLD'].equals(data['SKYGGEHOLD'].values):
                for idx, row in ed.iterrows():
                    df_raw.loc[df_raw['Navn'] == row['Navn'], 'SKYGGEHOLD'] = row['SKYGGEHOLD']
                push_to_github(DB_PATH, "Update Skygge Status", df_raw.to_csv(index=False), db_sha)
                st.rerun()

    # --- TAB 3: SKYGGELISTE (TAKTISK) ---
    with t3:
        df_s = df_unique[df_unique['SKYGGEHOLD'] == True].copy()
        if not df_s.empty:
            ed_s = st.data_editor(
                df_s[['Navn', 'POS_343', 'POS_433', 'POS_352']],
                hide_index=True, use_container_width=True, height=(len(df_s)+1)*35+10,
                column_config={
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys()))
                }, disabled=['Navn']
            )
            if not ed_s[['POS_343', 'POS_433', 'POS_352']].equals(df_s[['POS_343', 'POS_433', 'POS_352']]):
                for _, row in ed_s.iterrows():
                    df_raw.loc[df_raw['Navn'] == row['Navn'], ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]
                push_to_github(DB_PATH, "Update Tactical POS", df_raw.to_csv(index=False), db_sha)
                st.rerun()
        else:
            st.info("Ingen spillere på skyggelisten.")

    # --- TAB 4: BANEVISNING ---
    with t4:
        df_pitch_data = df_unique[df_unique['SKYGGEHOLD'] == True].copy()
        f = st.session_state.form_skygge
        p_col = f"POS_{f.replace('-', '')}"
        
        c_p, c_m = st.columns([5, 1])
        with c_m:
            for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(opt, key=f"p_{opt}", type="primary" if f == opt else "secondary", use_container_width=True):
                    st.session_state.form_skygge = opt
                    st.rerun()
        
        with c_p:
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
            fig, ax = pitch.draw(figsize=(10, 7))
            
            # Koordinater
            if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
            elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
            else: m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}

            for pid, (x, y, lbl) in m.items():
                ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                pos_players = df_pitch_data[df_pitch_data[p_col].astype(str) == str(pid)]
                for i, (_, p) in enumerate(pos_players.iterrows()):
                    ax.text(x, y+(i*4), p['Navn'], size=8, ha='center', weight='bold', bbox=dict(facecolor='white', edgecolor='#333', alpha=0.8, boxstyle='square,pad=0.1'))
            st.pyplot(fig)

    # Trigger Modal
    if st.session_state.active_player:
        vis_spiller_modal(st.session_state.active_player, df_raw, career_df)
        st.session_state.active_player = None

if __name__ == "__main__":
    vis_side()
