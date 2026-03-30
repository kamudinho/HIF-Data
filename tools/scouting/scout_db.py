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
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- MODAL: SPILLERPROFIL ---
@st.dialog("Spillerprofil", width="large")
def vis_spiller_modal(valgt_navn, billed_map, career_df, alle_rapporter):
    # Sørg for at vi filtrerer rigtigt på tværs af alle rapporter
    spiller_historik = alle_rapporter[alle_rapporter['Navn'] == valgt_navn].sort_values('DATO', ascending=False)
    
    if spiller_historik.empty:
        st.error(f"Ingen historik fundet for {valgt_navn}")
        return
        
    nyeste = spiller_historik.iloc[0]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    # Header
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"**Klub:** {nyeste.get('Klub', '-')} | **Pos:** {nyeste.get('Position', '-')}")
        st.write(f"**Rating:** {nyeste.get('Rating_Avg', 0)} | **Potentiale:** {nyeste.get('Potentiale', '-')}")

    t1, t2, t3, t4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstats"])
    
    keys = ['Beslutsomhed', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Lederegenskaber', 'Teknik', 'Spilintelligens']
    
    # --- TAB 1: RADAR & TEKST ---
    with t1:
        col_stats, col_radar, col_text = st.columns([1, 2, 2])
        with col_stats:
            st.markdown("### Vurderinger")
            for k in keys:
                val = nyeste.get(k, 1)
                st.write(f"**{k}:** {val}")
        
        with col_radar:
            r_vals = []
            for k in keys:
                try:
                    v = float(str(nyeste.get(k, 1)).replace(',', '.'))
                    r_vals.append(v)
                except:
                    r_vals.append(1.0)
            
            fig = go.Figure(data=go.Scatterpolar(
                r=r_vals + [r_vals[0]], 
                theta=keys + [keys[0]], 
                fill='toself', 
                line_color='#df003b'
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[1, 6])),
                showlegend=False, height=350, margin=dict(l=40,r=40,t=40,b=40)
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col_text:
            st.success(f"**Styrker**\n\n{nyeste.get('Styrker', '-')}")
            st.warning(f"**Udvikling**\n\n{nyeste.get('Udvikling', '-')}")
            st.info(f"**Vurdering**\n\n{nyeste.get('Vurdering', '-')}")

    # --- TAB 2: HISTORIK ---
    with t2:
        st.dataframe(
            spiller_historik[['DATO', 'Klub', 'Rating_Avg', 'Status', 'Scout']].rename(columns={'DATO': 'Dato'}),
            use_container_width=True,
            hide_index=True
        )

# --- HOVEDSIDE ---
def vis_side(scout_reports_df, df_spillere, sql_players, career_df):
    if "active_player" not in st.session_state:
        st.session_state.active_player = None
    if "editor_key" not in st.session_state:
        st.session_state.editor_key = 0

    # 1. HENT DATA
    content, sha = get_github_file(FILE_PATH)
    if not content:
        st.error("Kunne ikke hente databasen.")
        return

    df_raw = pd.read_csv(StringIO(content))
    
    # --- KOLONNE-FIX ---
    standard_cols = {
        'PLAYER_WYID': 'PLAYER_WYID', 'DATO': 'DATO', 'NAVN': 'Navn',
        'KLUB': 'Klub', 'POSITION': 'Position', 'RATING_AVG': 'Rating_Avg',
        'POTENTIALE': 'Potentiale', 'ER_EMNE': 'ER_EMNE'
    }
    current_cols = {c.upper(): c for c in df_raw.columns}
    rename_dict = {current_cols[k]: v for k, v in standard_cols.items() if k in current_cols}
    df_raw = df_raw.rename(columns=rename_dict)

    # 2. DATA RENSNING
    df_raw['ER_EMNE'] = df_raw['ER_EMNE'].astype(str).str.lower().map({'true': True, 'false': False, '1': True, '0': False}).fillna(False)
    df_raw['DATO'] = pd.to_datetime(df_raw['DATO'], errors='coerce')
    df_raw['Rating_Avg'] = pd.to_numeric(df_raw['Rating_Avg'], errors='coerce').fillna(0)
    
    # Unikke spillere
    df_unique = df_raw.sort_values('DATO', ascending=False).drop_duplicates('Navn').copy()
    df_unique['Dato_Visning'] = df_unique['DATO'].dt.date

    # 3. FORBERED DISPLAY
    display_cols = ['Navn', 'Klub', 'Position', 'Rating_Avg', 'Potentiale', 'Dato_Visning', 'ER_EMNE']
    df_display = df_unique[[c for c in display_cols if c in df_unique.columns]].copy()
    df_display.insert(0, "Se", False)

    # --- FAST HØJDE (20 linjer + header) ---
    FAST_HOEJDE = 735 

    # 4. DATA EDITOR
    ed_result = st.data_editor(
        df_display,
        column_config={
            "Se": st.column_config.CheckboxColumn("🔍", default=False, width="small"),
            "ER_EMNE": st.column_config.CheckboxColumn("Emne"),
            "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f"),
            "Dato_Visning": "Seneste"
        },
        disabled=['Navn', 'Klub', 'Position', 'Rating_Avg', 'Potentiale', 'Dato_Visning'],
        hide_index=True,
        use_container_width=True,
        height=FAST_HOEJDE, # Her låses højden
        key=f"scout_editor_{st.session_state.editor_key}"
    )

    # 5. GEM LOGIK
    if not ed_result['ER_EMNE'].equals(df_display['ER_EMNE']):
        with st.spinner("Gemmer..."):
            for idx, row in ed_result.iterrows():
                df_raw.loc[df_raw['Navn'] == row['Navn'], 'ER_EMNE'] = row['ER_EMNE']
            
            df_to_save = df_raw.copy()
            df_to_save['DATO'] = df_to_save['DATO'].dt.strftime('%Y-%m-%d')
            new_csv = df_to_save.to_csv(index=False)
            res = push_to_github(FILE_PATH, "Update status", new_csv, sha)
            if res in [200, 201]:
                st.toast("✅ Gemt!")
                st.rerun()

    # 6. MODAL
    valgte = ed_result[ed_result["Se"] == True]
    if not valgte.empty:
        st.session_state.active_player = valgte.iloc[-1]['Navn']
        st.session_state.editor_key += 1
        st.rerun()

    if st.session_state.active_player:
        billed_map = {}
        if sql_players is not None:
            billed_map = dict(zip(sql_players['PLAYER_WYID'].apply(rens_id), sql_players['IMAGEDATAURL']))
        vis_spiller_modal(st.session_state.active_player, billed_map, career_df, df_raw)
        st.session_state.active_player = None
        
# --- RUN ---
if __name__ == "__main__":
    # vis_side(None, None, None, None)
    pass
