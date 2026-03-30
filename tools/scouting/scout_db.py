import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import base64
from io import StringIO
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- HJÆLPEFUNKTIONER ---
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
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

def rens_id(val):
    """Fjerner .0 og mellemrum fra ID'er så de altid kan matches"""
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- MODAL: SPILLERPROFIL ---
@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, billed_map, career_df, alle_rapporter):
    # 1. ENSRET KOLONNER I RAPPORTER
    df_modal = alle_rapporter.copy()
    mapping = {
        'KLUB': 'Klub', 'POSITION': 'Position', 'RATING_AVG': 'Rating_Avg',
        'STATUS': 'Status', 'SCOUT': 'Scout', 'DATO': 'DATO', 'POTENTIALE': 'Potentiale',
        'STYRKER': 'Styrker', 'UDVIKLING': 'Udvikling', 'VURDERING': 'Vurdering',
        'BESLUTSOMHED': 'Beslutsomhed', 'FART': 'Fart', 'AGGRESIVITET': 'Aggresivitet',
        'ATTITUDE': 'Attitude', 'UDHOLDENHED': 'Udholdenhed', 'LEDEREGENSKABER': 'Lederegenskaber',
        'TEKNIK': 'Teknik', 'SPILINTELLIGENS': 'Spilintelligens'
    }
    current_cols = {c.upper(): c for c in df_modal.columns}
    rename_dict = {current_cols[k]: v for k, v in mapping.items() if k in current_cols}
    df_modal = df_modal.rename(columns=rename_dict)

    # Filtrer historik (sorteret ældst -> nyest for grafer)
    spiller_historik = df_modal[df_modal['Navn'] == valgt_navn].sort_values('DATO', ascending=True)
    if spiller_historik.empty:
        st.error("Ingen data fundet.")
        return
        
    nyeste = spiller_historik.iloc[-1]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    
    # Billede
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    # Header
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"**Klub:** {nyeste.get('Klub', '-')} | **Pos:** {nyeste.get('Position', '-')} | **ID:** {pid}")

    t1, t2, t3, t4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstats"])
    
    # --- TAB 1: RADAR ---
    with t1:
        keys = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
        col_radar, col_text = st.columns([2, 2])
        with col_radar:
            r_vals = []
            for k in keys:
                try: v = float(str(nyeste.get(k, 1)).replace(',', '.'))
                except: v = 1.0
                r_vals.append(v)
            fig = go.Figure(data=go.Scatterpolar(r=r_vals + [r_vals[0]], theta=keys + [keys[0]], fill='toself', line_color='#df003b'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 6])), showlegend=False, height=350, margin=dict(l=40,r=40,t=40,b=40))
            st.plotly_chart(fig, use_container_width=True)
        with col_text:
            st.success(f"**Styrker:**\n\n{nyeste.get('Styrker', '-')}")
            st.info(f"**Vurdering:**\n\n{nyeste.get('Vurdering', '-')}")

    # --- TAB 2: HISTORIK ---
    with t2:
        st.dataframe(spiller_historik.sort_values('DATO', ascending=False), use_container_width=True, hide_index=True)

    # --- TAB 3: UDVIKLING (Graf) ---
    with t3:
        st.markdown("### Rating over tid")
        fig_evol = go.Figure(go.Scatter(x=spiller_historik['DATO'], y=spiller_historik['Rating_Avg'], mode='lines+markers', line_color='#df003b', marker=dict(size=10)))
        fig_evol.update_layout(yaxis=dict(range=[1, 5.5], title="Rating"), height=400, margin=dict(l=20,r=20,t=20,b=20))
        st.plotly_chart(fig_evol, use_container_width=True)

    # --- TAB 4: SÆSONSTATS (Match på PLAYER_WYID) ---
    with t4:
        st.markdown(f"### Wyscout Sæsonstats (ID: {pid})")
        if career_df is not None:
            # Rens ID i career_df for at sikre match
            career_copy = career_df.copy()
            if 'PLAYER_WYID' in career_copy.columns:
                career_copy['match_id'] = career_copy['PLAYER_WYID'].apply(rens_id)
                stats = career_copy[career_copy['match_id'] == pid]
                
                if not stats.empty:
                    # Vis relevante stats (tilpas disse navne til din career_df)
                    cols_to_show = ['competitionName', 'matches', 'goals', 'assists', 'minutesPlayed']
                    available = [c for c in cols_to_show if c in stats.columns]
                    st.dataframe(stats[available], use_container_width=True, hide_index=True)
                else:
                    st.warning("Ingen stats fundet for dette ID i sæson-databasen.")
            else:
                st.error("Kolonnen 'PLAYER_WYID' findes ikke i career_df.")
        else:
            st.error("Sæson-databasen er ikke indlæst.")

# --- HOVEDSIDE ---
def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    if "active_player" not in st.session_state:
        st.session_state.active_player = None
    if "editor_key" not in st.session_state:
        st.session_state.editor_key = 0

    content, sha = get_github_file(FILE_PATH)
    if not content: return
    df_raw = pd.read_csv(StringIO(content))
    
    # ENSRET KOLONNER (Robust fix)
    mapping = {'PLAYER_WYID': 'PLAYER_WYID', 'DATO': 'DATO', 'NAVN': 'Navn', 'KLUB': 'Klub', 'RATING_AVG': 'Rating_Avg', 'ER_EMNE': 'ER_EMNE'}
    current_cols = {c.upper(): c for c in df_raw.columns}
    df_raw = df_raw.rename(columns={current_cols[k]: v for k, v in mapping.items() if k in current_cols})

    # Typer
    df_raw['DATO'] = pd.to_datetime(df_raw['DATO'], errors='coerce')
    df_raw['ER_EMNE'] = df_raw['ER_EMNE'].astype(str).str.lower().map({'true': True, 'false': False, '1': True, '0': False}).fillna(False)
    
    df_unique = df_raw.sort_values('DATO', ascending=False).drop_duplicates('Navn').copy()
    df_unique['Dato_Visning'] = df_unique['DATO'].dt.date

    # Tabel visning
    df_display = df_unique[['Navn', 'Klub', 'Rating_Avg', 'Dato_Visning', 'ER_EMNE']].copy()
    df_display.insert(0, "Se", False)

    # 4. DATA EDITOR (FAST HØJDE: 20 rækker)
    ed_result = st.data_editor(
        df_display,
        column_config={
            "Se": st.column_config.CheckboxColumn("🔍", width="small"),
            "ER_EMNE": st.column_config.CheckboxColumn("Emne"),
            "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f")
        },
        disabled=['Navn', 'Klub', 'Rating_Avg', 'Dato_Visning'],
        hide_index=True, use_container_width=True, height=735,
        key=f"scout_editor_{st.session_state.editor_key}"
    )

    # GEM LOGIK (HVIS ER_EMNE ÆNDRES)
    if not ed_result['ER_EMNE'].equals(df_display['ER_EMNE']):
        with st.spinner("Opdaterer database..."):
            for idx, row in ed_result.iterrows():
                df_raw.loc[df_raw['Navn'] == row['Navn'], 'ER_EMNE'] = row['ER_EMNE']
            
            df_to_save = df_raw.copy()
            df_to_save['DATO'] = df_to_save['DATO'].dt.strftime('%Y-%m-%d')
            new_csv = df_to_save.to_csv(index=False)
            res = push_to_github(FILE_PATH, "Update status via Editor", new_csv, sha)
            if res in [200, 201]:
                st.toast("✅ Database opdateret!")
                st.rerun()

    # MODAL TRIGGER
    valgte = ed_result[ed_result["Se"] == True]
    if not valgte.empty:
        st.session_state.active_player = valgte.iloc[-1]['Navn']
        st.session_state.editor_key += 1
        st.rerun()

    if st.session_state.active_player:
        billed_map = {}
        if sql_players is not None:
            # Sikr at billed-mappet også bruger rensede ID'er
            billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))
        
        vis_spiller_modal(st.session_state.active_player, billed_map, career_df, df_raw)
        st.session_state.active_player = None
