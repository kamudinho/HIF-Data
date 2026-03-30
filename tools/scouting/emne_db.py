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

# --- POSITIONSMAPPING ---
POS_OPTIONS = {
    "0": "Vælg position", "1": "Målmand", "2": "Højre back", "5": "Venstre back",
    "4": "Midtstopper (V)", "3.5": "Midtstopper (C)", "3": "Midtstopper (H)",
    "6": "Defensiv midt", "8": "Central midt", "7": "Højre kant",
    "11": "Venstre kant", "10": "Offensiv midt", "9": "Angriber"
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
def vis_spiller_modal(valgt_navn, alle_rapporter):
    # Filtrér historik for spilleren
    spiller_historik = alle_rapporter[alle_rapporter['Navn'] == valgt_navn].sort_values('DATO', ascending=False)
    nyeste = spiller_historik.iloc[0]
    
    pid = str(nyeste.get('PLAYER_WYID', '')).split('.')[0]
    img_url = f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150, fallback="https://via.placeholder.com/150")
    with c2:
        st.subheader(valgt_navn)
        st.write(f"**Klub:** {nyeste.get('KLUB', '-')} | **Pos:** {nyeste.get('POSITION', '-')}")
        st.write(f"**Rating:** {nyeste.get('RATING_AVG', 0)} | **Status:** {nyeste.get('STATUS', '-')}")

    t1, t2, t3 = st.tabs(["Seneste Rapport", "Historik", "Udvikling"])
    
    # Egenskaber til Radar
    keys = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
    
    with t1:
        col_stats, col_radar, col_text = st.columns([1, 2, 2])
        with col_stats:
            for k in keys:
                val = nyeste.get(k, 1)
                st.write(f"**{k.title()}:** {val}")
        with col_radar:
            r_vals = [float(str(nyeste.get(k, 1)).replace(',', '.')) for k in keys]
            labels = [k.title()[:5] + '.' for k in keys]
            fig = go.Figure(data=go.Scatterpolar(r=r_vals + [r_vals[0]], theta=labels + [labels[0]], fill='toself', line_color=HIF_ROD))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 6])), showlegend=False, height=300, margin=dict(l=30,r=30,t=30,b=30))
            st.plotly_chart(fig, use_container_width=True)
        with col_text:
            st.success(f"**Styrker:**\n\n{nyeste.get('STYRKER', '-')}")
            st.info(f"**Vurdering:**\n\n{nyeste.get('VURDERING', '-')}")

    with t2:
        for _, rap in spiller_historik.iterrows():
            dato_str = rap['DATO'].strftime('%d. %b %Y') if hasattr(rap['DATO'], 'strftime') else str(rap['DATO'])
            with st.expander(f"Rapport - {dato_str} (Scout: {rap.get('SCOUT','?')})"):
                st.write(f"**Rating:** {rap.get('RATING_AVG', 0)}")
                st.write(f"**Vurdering:** {rap.get('VURDERING', '-')}")

    with t3:
        hist_evo = spiller_historik.sort_values('DATO')
        fig_evo = go.Figure(go.Scatter(x=hist_evo['DATO'], y=hist_evo['RATING_AVG'], mode='lines+markers', line_color=HIF_ROD))
        fig_evo.update_layout(yaxis=dict(range=[1, 6], title="Rating"), height=300)
        st.plotly_chart(fig_evo, use_container_width=True)

# --- HOVEDLOGIK ---
def vis_side():
    if "active_player" not in st.session_state: st.session_state.active_player = None
    if 'form_skygge' not in st.session_state: st.session_state.form_skygge = "3-4-3"

    # Hent data fra GitHub
    content, sha = get_github_file(DB_PATH)
    if not content:
        st.error("Kunne ikke hente data fra GitHub.")
        return

    # Læs CSV og standardiser
    df_raw = pd.read_csv(StringIO(content))
    # Vi laver en kopi til visning hvor vi tvinger kolonnenavne til at være pæne
    df_clean = df_raw.copy()
    
    # Sikr at vigtige kolonner findes (case-insensitive check)
    cols_upper = [c.upper() for c in df_clean.columns]
    df_clean.columns = cols_upper
    
    # Mapping tilbage til de navne vi bruger i koden
    rename_map = {
        'NAVN': 'Navn', 'KLUB': 'KLUB', 'POSITION': 'POSITION', 
        'RATING_AVG': 'RATING_AVG', 'DATO': 'DATO', 'SKYGGEHOLD': 'SKYGGEHOLD'
    }
    df_clean = df_clean.rename(columns=rename_map)
    
    # Konverter typer
    df_clean['DATO'] = pd.to_datetime(df_clean['DATO'], errors='coerce')
    df_clean['SKYGGEHOLD'] = df_clean['SKYGGEHOLD'].astype(str).str.upper().map({'TRUE': True, 'FALSE': False}).fillna(False)
    
    # Nyeste rapport pr. spiller
    df_unique = df_clean.sort_values('DATO', ascending=False).drop_duplicates('Navn').copy()

    t1, t2, t3, t4 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste", "🏟️ Banevisning"])

    # Filtrér grupper
    df_hif = df_unique[df_unique['KLUB'] == 'Hvidovre IF'].copy()
    df_emner = df_unique[df_unique['KLUB'] != 'Hvidovre IF'].copy()

    # --- TAB 1 & 2: OVERSIGTER ---
    for tab, data, key_suffix in [(t1, df_emner, "emne"), (t2, df_hif, "hif")]:
        with tab:
            if data.empty:
                st.info("Ingen spillere fundet.")
                continue
            
            display_cols = ['Navn', 'KLUB', 'POSITION', 'RATING_AVG', 'SKYGGEHOLD']
            df_disp = data[display_cols].copy()
            df_disp.insert(0, "Profil", False)
            
            # Dynamisk højde
            h = (len(df_disp) + 1) * 35 + 20
            
            ed = st.data_editor(
                df_disp,
                column_config={
                    "Profil": st.column_config.CheckboxColumn("Se", width="small"),
                    "SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge", width="small"),
                    "RATING_AVG": st.column_config.NumberColumn("Rating", format="%.1f")
                },
                disabled=['Navn', 'KLUB', 'POSITION'],
                hide_index=True, use_container_width=True, height=h, key=f"ed_{key_suffix}"
            )

            # Gem ændringer til Skyggehold
            if not ed['SKYGGEHOLD'].equals(data['SKYGGEHOLD'].values):
                for idx, row in ed.iterrows():
                    player_name = row['Navn']
                    df_raw.loc[df_raw.iloc[:, 2] == player_name, 'SKYGGEHOLD'] = str(row['SKYGGEHOLD'])
                push_to_github(DB_PATH, "Update Skygge Status", df_raw.to_csv(index=False), sha)
                st.rerun()

            # Åbn modal
            valgte = ed[ed["Profil"] == True]
            if not valgte.empty:
                st.session_state.active_player = valgte.iloc[-1]['Navn']
                st.rerun()

    # --- TAB 3: SKYGGELISTE (TAKTISK) ---
    with t3:
        df_s = df_unique[df_unique['SKYGGEHOLD'] == True].copy()
        if not df_s.empty:
            # Sørg for at taktiske kolonner findes
            for c in ['POS_343', 'POS_433', 'POS_352']:
                if c not in df_s.columns: df_s[c] = "0"
            
            # Vi viser taktiske valg. Vi caster til string for at matche POS_OPTIONS nøgler
            df_s[['POS_343', 'POS_433', 'POS_352']] = df_s[['POS_343', 'POS_433', 'POS_352']].astype(str).replace('nan','0').apply(lambda x: x.str.split('.').str[0] if '.' in str(x) else x)

            ed_s = st.data_editor(
                df_s[['Navn', 'POS_343', 'POS_433', 'POS_352']],
                hide_index=True, use_container_width=True,
                column_config={
                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys()))
                }, disabled=['Navn']
            )
            
            if not ed_s[['POS_343', 'POS_433', 'POS_352']].equals(df_s[['POS_343', 'POS_433', 'POS_352']]):
                for _, row in ed_s.iterrows():
                    # Opdater rådata
                    df_raw.loc[df_raw.iloc[:, 2] == row['Navn'], ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]
                push_to_github(DB_PATH, "Update Tactical Positions", df_raw.to_csv(index=False), sha)
                st.rerun()

    # --- TAB 4: BANEVISNING ---
    with t4:
        df_pitch_data = df_unique[df_unique['SKYGGEHOLD'] == True].copy()
        f = st.session_state.form_skygge
        p_col = f"POS_{f.replace('-', '')}"
        
        c_p, c_m = st.columns([5, 1])
        with c_m:
            for opt in ["3-4-3", "4-3-3", "3-5-2"]:
                if st.button(opt, key=f"btn_{opt}", type="primary" if f == opt else "secondary", use_container_width=True):
                    st.session_state.form_skygge = opt
                    st.rerun()
        
        with c_p:
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333', linewidth=1)
            fig, ax = pitch.draw(figsize=(10, 7))
            
            # Formationer
            if f == "3-4-3": m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(55,10,'VWB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 2:(55,70,'HWB'), 11:(80,15,'VW'), 9:(100,40,'ANG'), 7:(80,65,'HW')}
            elif f == "4-3-3": m = {1:(10,40,'MM'), 5:(35,10,'VB'), 4:(30,25,'VCB'), 3:(30,55,'HCB'), 2:(35,70,'HB'), 6:(55,30,'DM'), 8:(55,50,'DM'), 10:(75,40,'CM'), 11:(85,15,'VW'), 9:(100,40,'ANG'), 7:(85,65,'HW')}
            else: m = {1:(10,40,'MM'), 4:(30,22,'VCB'), 3.5:(30,40,'CB'), 3:(30,58,'HCB'), 5:(45,10,'VWB'), 6:(60,30,'DM'), 8:(60,50,'DM'), 2:(45,70,'HWB'), 10:(75,40,'CM'), 9:(95,32,'ANG'), 7:(95,48,'ANG')}

            for pid, (x, y, lbl) in m.items():
                # Tegn boks for position
                ax.text(x, y-4, lbl, size=8, color="white", weight='bold', ha='center', bbox=dict(facecolor=HIF_ROD, edgecolor='white', boxstyle='round,pad=0.2'))
                
                # Find spillere på denne position (håndterer både 3 og 3.0 i data)
                players = df_pitch_data[df_pitch_data[p_col].astype(str).str.startswith(str(pid))]
                for i, (_, p) in enumerate(players.iterrows()):
                    ax.text(x, y+(i*4), p['Navn'], size=8, ha='center', weight='bold', bbox=dict(facecolor='white', edgecolor='#333', alpha=0.8, boxstyle='square,pad=0.1'))
            st.pyplot(fig)

    # Trigger Modal
    if st.session_state.active_player:
        vis_spiller_modal(st.session_state.active_player, df_clean)
        st.session_state.active_player = None

if __name__ == "__main__":
    vis_side()
