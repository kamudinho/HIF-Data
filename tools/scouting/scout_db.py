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

# --- GITHUB HJÆLPEFUNKTIONER ---
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
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, billed_map, career_df, alle_rapporter):
    spiller_historik = alle_rapporter[alle_rapporter['Navn'] == valgt_navn].sort_values('Dato', ascending=False)
    nyeste = spiller_historik.iloc[0]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    # Header
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"Klub: {nyeste.get('Klub', '-')} | Pos: {nyeste.get('Position', '-')}")
        st.write(f"Rating: {nyeste.get('Rating_Avg', 0)} | Potentiale: {nyeste.get('Potentiale', '-')}")

    t1, t2, t3, t4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstats"])
    
    keys = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
    labels = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']

    # --- TAB 1: SENESTE RAPPORT ---
    with t1:
        col_stats, col_radar, col_text = st.columns([0.8, 1.5, 1.5])
        with col_stats:
            st.markdown("**Vurderinger**")
            for k in keys:
                st.write(f"**{k}:** {nyeste.get(k, 1)}")
        with col_radar:
            r_vals = [float(str(nyeste.get(k, 1)).replace(',', '.')) for k in keys]
            fig = go.Figure(data=go.Scatterpolar(r=r_vals + [r_vals[0]], theta=labels + [labels[0]], fill='toself', line_color='#df003b'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 6])), showlegend=False, height=300, margin=dict(l=40,r=40,t=20,b=20))
            st.plotly_chart(fig, use_container_width=True)
        with col_text:
            st.success(f"**Styrker**\n\n{nyeste.get('Styrker', '-')}")
            st.warning(f"**Udvikling**\n\n{nyeste.get('Udvikling', '-')}")
            st.info(f"**Vurdering**\n\n{nyeste.get('Vurdering', '-')}")

    # --- TAB 2-4 forbliver uændret ... ---
    # (Logikken for Historik, Udvikling og Sæsonstats indsættes her fra din oprindelige kode)

def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    if "active_player" not in st.session_state:
        st.session_state.active_player = None
    if "editor_key" not in st.session_state:
        st.session_state.editor_key = 0

    # 1. HENT DATA DIREKTE FRA GITHUB
    content, sha = get_github_file(FILE_PATH)
    if not content:
        st.error("Kunne ikke hente scouting_db.csv fra GitHub")
        return

    df_raw = pd.read_csv(StringIO(content))
    
    # SIKR AT 'ER_EMNE' EKSISTERER (SOM SIDSTE KOLONNE)
    if 'ER_EMNE' not in df_raw.columns:
        df_raw['ER_EMNE'] = False

    df_raw['PLAYER_WYID'] = df_raw['PLAYER_WYID'].apply(rens_id)
    df_raw['DATO'] = pd.to_datetime(df_raw['DATO'])
    
    # Find unikke spillere (nyeste rapport først)
    df_unique = df_raw.sort_values('DATO', ascending=False).drop_duplicates('Navn').copy()
    df_unique['DATO'] = df_unique['Dato'].dt.date

    # Billed-map
    billed_map = {}
    if sql_players is not None:
        billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))

    # 2. FORBERED DISPLAY (Emne til sidst)
    df_display = df_unique[['Navn', 'Klub', 'Position', 'Rating_Avg', 'Potentiale', 'Dato', 'ER_EMNE']].copy()
    df_display.insert(0, "Se", False)

    dynamic_height = (len(df_display) + 1) * 35 + 10

    # 3. DATA EDITOR
    ed_result = st.data_editor(
        df_display,
        column_config={
            "Se": st.column_config.CheckboxColumn("Profil", default=False),
            "ER_EMNE": st.column_config.CheckboxColumn("Emne", help="Ving af for at tilføje til emnelisten"),
            "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f")
        },
        disabled=['Navn', 'Klub', 'Position', 'Rating_Avg', 'Potentiale', 'Dato'],
        hide_index=True,
        use_container_width=True,
        height=dynamic_height,
        key=f"editor_v{st.session_state.editor_key}"
    )

    # 4. GEM LOGIK (HVIS ER_EMNE ÆNDRES)
    if not ed_result['ER_EMNE'].equals(df_display['ER_EMNE']):
        with st.spinner("Gemmer ændringer til GitHub..."):
            # Opdater df_raw baseret på ændringerne i editoren
            for _, row in ed_result.iterrows():
                df_raw.loc[df_raw['Navn'] == row['Navn'], 'ER_EMNE'] = row['ER_EMNE']
            
            # Konverter til CSV og push
            new_csv = df_raw.to_csv(index=False)
            res = push_to_github(FILE_PATH, "Update ER_EMNE status", new_csv, sha)
            
            if res in [200, 201]:
                st.success("✅ Database opdateret!")
                st.rerun()
            else:
                st.error(f"❌ Fejl ved gem. Status: {res}")

    # 5. MODAL HÅNDTERING
    valgte = ed_result[ed_result["Se"] == True]
    if not valgte.empty:
        st.session_state.active_player = valgte.iloc[-1]['Navn']
        st.session_state.editor_key += 1
        st.rerun()

    if st.session_state.active_player:
        vis_spiller_modal(st.session_state.active_player, billed_map, career_df, df_raw)
        st.session_state.active_player = None
