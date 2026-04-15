import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import base64
from io import StringIO
from datetime import datetime
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

COL_ORDER = [
    "PLAYER_WYID", "DATO", "NAVN", "KLUB", "POSITION", "BIRTHDATE", "RATING_AVG", "STATUS",
    "POTENTIALE", "STYRKER", "UDVIKLING", "VURDERING", "BESLUTSOMHED", "FART",
    "AGGRESIVITET", "ATTITUDE", "UDHOLDENHED", "LEDEREGENSKABER", "TEKNIK",
    "SPILINTELLIGENS", "SCOUT", "KONTRAKT", "FORVENTNING",
    "POS_PRIORITET", "POS", "LON", "SKYGGEHOLD", "KOMMENTAR", 
    "ER_EMNE", "TRANSFER_VINDUE", "POS_343", "POS_433", "POS_352"
]

# --- HJÆLPEFUNKTIONER ---
def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
            return content, data['sha']
    except Exception as e:
        st.error(f"GitHub Hent Fejl: {e}")
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

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

# --- MODAL: SPILLERPROFIL ---
@st.dialog("Seneste Scout Rapport", width="large")
def vis_spiller_modal(valgt_navn, alle_rapporter, billed_map, career_df=None):
    spiller_historik = alle_rapporter[alle_rapporter['NAVN'] == valgt_navn].sort_values('DATO', ascending=True)
    if spiller_historik.empty:
        st.error(f"Ingen data fundet for {valgt_navn}")
        return
        
    nyeste = spiller_historik.iloc[-1]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    
    # Her henter vi URL fra mappet baseret på PLAYER_WYID
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    fallback_url = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png"
    
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url if img_url else fallback_url, width=150)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"Klub: {nyeste.get('KLUB', '-')} | Pos: {nyeste.get('POSITION', '-')} | ID: {pid}")

    t1, t2, t3, t4 = st.tabs(["Seneste Rapport", "Historik", "Udvikling", "Sæsonstats"])
    keys = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']

    with t1:
        col_stats, col_radar, col_text = st.columns([0.8, 1.5, 1.5])
        with col_stats:
            st.markdown("**Vurderinger**")
            for k in keys:
                st.write(f"{k.capitalize()}: {nyeste.get(k, '-')}")
        
        with col_radar:
            r_vals = []
            for k in keys:
                try: v = float(str(nyeste.get(k, 1)).replace(',', '.')); r_vals.append(v)
                except: r_vals.append(1.0)
            
            fig = go.Figure(data=go.Scatterpolar(r=r_vals + [r_vals[0]], theta=[k.capitalize() for k in keys] + [keys[0].capitalize()], fill='toself', line_color='#df003b'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 6])), showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)
            
        with col_text:
            st.write("**Styrker**"); st.info(nyeste.get('STYRKER', '-'))
            st.write("**Vurdering**"); st.success(nyeste.get('VURDERING', '-'))

    with t2:
        st.dataframe(spiller_historik.sort_values('DATO', ascending=False), use_container_width=True, hide_index=True)

    with t3:
        fig_evol = go.Figure(go.Scatter(x=spiller_historik['DATO'], y=spiller_historik['RATING_AVG'], mode='lines+markers', line_color='#df003b'))
        st.plotly_chart(fig_evol, use_container_width=True)

    with t4:
        if career_df is not None:
            stats = career_df[career_df['PLAYER_WYID'].apply(rens_id) == pid].copy()
            if not stats.empty:
                st.dataframe(stats.drop_duplicates(subset=['SEASONNAME', 'TEAMNAME', 'COMPETITIONNAME']).sort_values('SEASONNAME', ascending=False), use_container_width=True, hide_index=True)

# --- HOVEDSIDE ---
def vis_side(dp):    
    if "editor_key" not in st.session_state: st.session_state.editor_key = 0
    
    df_local_raw = dp.get("scout_reports", pd.DataFrame()).copy()
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()).copy()
    career_df = dp.get("career_data", None)

    # --- 1. BYG BILLEDE-MAP (VIGTIGT!) ---
    # Her sikrer vi at vi bruger PLAYER_WYID som nøgle og IMAGEDATAURL som værdi
    billed_map = {}
    if not df_wyscout.empty and 'IMAGEDATAURL' in df_wyscout.columns:
        billed_map = dict(zip(df_wyscout['PLAYER_WYID'].apply(rens_id), df_wyscout['IMAGEDATAURL']))

    # --- 2. EDITOR SEKTION (Skyggehold / Emner) ---
    st.markdown("### Database Overblik")
    if not df_local_raw.empty:
        df_unique = df_local_raw.sort_values('DATO', ascending=False).drop_duplicates(subset=['PLAYER_WYID']).copy()
        display_cols = ['NAVN', 'KLUB', 'RATING_AVG', 'KONTRAKT', 'ER_EMNE', 'SKYGGEHOLD']
        df_display = df_unique[display_cols].copy()
        df_display.insert(0, "SE", False)
        
        ed_result = st.data_editor(df_display, hide_index=True, use_container_width=True, key=f"ed_{st.session_state.editor_key}")
        
        # Hvis der trykkes på "SE" i editoren
        valgte_navn = ed_result[ed_result["SE"] == True]
        if not valgte_navn.empty:
            vis_spiller_modal(valgte_navn.iloc[-1]['NAVN'], df_local_raw, billed_map, career_df)

    st.divider()

    # --- 3. INPUT FORM (Din oprindelige logik) ---
    unique_players = {}
    def add_to_options(df):
        if df is None or df.empty: return
        for _, r in df.iterrows():
            p_id = rens_id(r.get('PLAYER_WYID'))
            if not p_id: continue
            navn = r.get('NAVN') or r.get('PLAYER_NAME') or f"{r.get('FIRSTNAME','')} {r.get('LASTNAME','')}".strip()
            klub = r.get('KLUB') or r.get('TEAMNAME') or "Ukendt"
            if p_id not in unique_players:
                unique_players[p_id] = {"label": f"{navn} ({klub})", "data": {"n": navn, "id": p_id, "klub": klub, "pos": r.get('POSITION')}}

    add_to_options(df_local_raw)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    row1_c1, row1_c2, row1_c3 = st.columns([3, 1.5, 1])
    with row1_c1:
        sel_id = st.selectbox("Vælg spiller for ny rapport", [""] + options_list, format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")
    
    if sel_id:
        data = unique_players[sel_id]["data"]
        # Find seneste rapport for valgte spiller i dropdown
        existing = df_local_raw[df_local_raw['PLAYER_WYID'].apply(rens_id) == sel_id].sort_values('DATO', ascending=False)
        with row1_c2: st.text_input("Seneste dato", value=existing.iloc[0]['DATO'] if not existing.empty else "-", disabled=True)
        with row1_c3: 
            st.markdown("<br>", unsafe_allow_html=True)
            if not existing.empty:
                if st.button("Se Profil", use_container_width=True):
                    vis_spiller_modal(data["n"], df_local_raw, billed_map, career_df)

        with st.form("rapport_form", clear_on_submit=True):
            st.markdown("#### Ny Vurdering")
            l2_c1, l2_c2 = st.columns(2)
            status = l2_c1.selectbox("Status", ["Interessant", "Hold øje", "Køb", "Prioritet"])
            er_emne = l2_c2.checkbox("Transferemne?")
            
            m1, m2, m3, m4 = st.columns(4)
            beslut = m1.select_slider("Fart", options=range(1,7), value=3)
            # ... (tilføj de andre slidere her)

            if st.form_submit_button("Gem Rapport", use_container_width=True):
                # Din gemme-logik her med COL_ORDER
                st.success("Rapport gemt!")
