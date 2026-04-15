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

# --- MODAL: SPILLERPROFIL (Fra din scout_db kode) ---
@st.dialog("Seneste Scout Rapport", width="large")
def vis_spiller_modal(valgt_navn, alle_rapporter, career_df=None):
    spiller_historik = alle_rapporter[alle_rapporter['NAVN'] == valgt_navn].sort_values('DATO', ascending=True)
    
    if spiller_historik.empty:
        st.error(f"Ingen data fundet for {valgt_navn}")
        return
        
    nyeste = spiller_historik.iloc[-1]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    img_url = f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    # Header
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=120, fallback="https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png")
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
                val = nyeste.get(k, "-")
                st.write(f"{k.capitalize()}: {val}")
        
        with col_radar:
            r_vals = []
            for k in keys:
                try:
                    v = float(str(nyeste.get(k, 1)).replace(',', '.'))
                    r_vals.append(v)
                except: r_vals.append(1.0)
            
            fig = go.Figure(data=go.Scatterpolar(
                r=r_vals + [r_vals[0]], 
                theta=[k.capitalize() for k in keys] + [keys[0].capitalize()], 
                fill='toself', 
                line_color='#df003b'
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[1, 6])), 
                showlegend=False, height=250, margin=dict(l=40,r=40,t=30,b=30)
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col_text:
            st.write("**Styrker**")
            st.info(nyeste.get('STYRKER', '-'))
            st.write("**Udvikling**")
            st.success(nyeste.get('UDVIKLING', '-'))
            st.write("**Vurdering**")
            st.success(nyeste.get('VURDERING', '-'))

    with t2:
        st.dataframe(spiller_historik.sort_values('DATO', ascending=False), use_container_width=True, hide_index=True)

    with t3:
        st.markdown("### Rating over tid")
        fig_evol = go.Figure(go.Scatter(
            x=spiller_historik['DATO'], 
            y=spiller_historik['RATING_AVG'], 
            mode='lines+markers', 
            line_color='#df003b'
        ))
        fig_evol.update_layout(yaxis=dict(range=[1, 6]), height=300)
        st.plotly_chart(fig_evol, use_container_width=True)

    with t4:
        st.markdown("### Karriereoversigt")
        if career_df is not None:
            stats = career_df[career_df['PLAYER_WYID'].apply(rens_id) == pid].copy()
            if not stats.empty:
                stats_clean = stats.drop_duplicates(subset=['SEASONNAME', 'TEAMNAME', 'COMPETITIONNAME'])
                stats_clean = stats_clean.sort_values('SEASONNAME', ascending=False)
                st.dataframe(stats_clean, use_container_width=True, hide_index=True)
            else:
                st.warning("Ingen karrieredata fundet.")

# --- HOVEDSIDE ---
def vis_side(dp):    
    # --- 1. DATA FORBEREDELSE ---
    df_local = dp.get("scout_reports", pd.DataFrame()).copy()
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()).copy()
    career_df = dp.get("career_data", None) # Henter karrieredata hvis tilgængelig
    
    unique_players = {}

    def get_safe_val(row, col_name, default=""):
        val = row.get(col_name, default)
        if isinstance(val, pd.Series):
            val = val.iloc[0] if not val.empty else default
        return str(val) if pd.notna(val) else default

    def add_to_options(df):
        if df is None or (isinstance(df, pd.DataFrame) and df.empty): return
        df_temp = df.copy()
        df_temp.columns = [str(c).upper().strip() for c in df_temp.columns]
        for _, r in df_temp.iterrows():
            p_id = rens_id(r.get('PLAYER_WYID'))
            if not p_id: continue
            
            f_name = get_safe_val(r, 'FIRSTNAME').replace('None', '').strip()
            l_name = get_safe_val(r, 'LASTNAME').replace('None', '').strip()
            fuldt_navn = f"{f_name} {l_name}" if f_name and l_name else (get_safe_val(r, 'PLAYER_NAME') or get_safe_val(r, 'NAVN') or "Ukendt")
            klub = get_safe_val(r, 'TEAMNAME') or get_safe_val(r, 'KLUB') or "Ukendt klub"
            pos_code = get_safe_val(r, 'ROLECODE3') or get_safe_val(r, 'POSITION') or ""
            
            b_date = r.get('BIRTHDATE') or r.get('BIRTH_DATE') or r.get('BIRTH_DAY') or r.get('DOB') or ""
            birth_val = ""
            if pd.notna(b_date) and str(b_date).strip() != "":
                try: birth_val = pd.to_datetime(b_date).strftime("%Y-%m-%d")
                except: birth_val = str(b_date)
            
            label = f"{fuldt_navn} ({klub})"
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": label, 
                    "data": {"n": fuldt_navn, "id": p_id, "pos": pos_code, "klub": klub, "birth": birth_val}
                }

    add_to_options(df_local)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- 2. UI LAYOUT ---
    data = {"n": "", "id": "", "pos": "", "klub": "", "birth": ""}
    
    # LINJE 1: Navnevalg, Dato-visning og Popup-knap
    row1_c1, row1_c2, row1_c3 = st.columns([3, 1.5, 1])
    
    with row1_c1:
        sel_id = st.selectbox("Vælg spiller", [""] + options_list, 
                            format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...",
                            key="player_selector")
        if sel_id: 
            data = unique_players[sel_id]["data"]

    # Tjek for eksisterende rapporter i databasen
    existing_report = None
    if sel_id and not df_local.empty:
        df_local['MATCH_ID'] = df_local['PLAYER_WYID'].apply(rens_id)
        matches = df_local[df_local['MATCH_ID'] == str(sel_id)]
        if not matches.empty:
            matches = matches.sort_values('DATO', ascending=False)
            existing_report = matches.iloc[0]

    with row1_c2:
        report_date = existing_report['DATO'] if existing_report is not None else "-"
        st.text_input("Seneste rapport", value=report_date, disabled=True)

    with row1_c3:
        st.markdown("<p style='margin-bottom: 28px;'></p>", unsafe_allow_html=True)
        if existing_report is not None:
            if st.button("Åbn rapport", use_container_width=True, key="view_report"):
                vis_spiller_modal(data["n"], df_local, career_df)
        else:
            st.button("Ingen data", disabled=True, use_container_width=True)

    # LINJE 2: POS, KLUB, FØDSELSDAG, SCOUT
    row2_c1, row2_c2, row2_c3, row2_c4 = st.columns([1, 2, 1.5, 1.5])
    row2_c1.text_input("POS", value=data['pos'], disabled=True)
    row2_c2.text_input("KLUB", value=data['klub'], disabled=True)
    row2_c3.text_input("FØDSELSDAG", value=data['birth'], disabled=True)
    scout_navn = row2_c4.text_input("SCOUT", value=st.session_state.get("user", "HIF Scout"), disabled=True)

    # --- 3. FORM OMRÅDE (Selve indtastningen) ---
    with st.form("rapport_form", clear_on_submit=True):
        # ... (Resten af din form-kode er uændret herfra)
        with st.container(border=True):
            st.markdown("**Stamdata & Status**")
            l2_c1, l2_c2, l2_c3 = st.columns(3)
            status_label = l2_c1.selectbox("Status", ["Interessant", "Hold øje", "Kig nærmere", "Køb", "Prioritet"])
            pos_nr = l2_c2.selectbox("POS (1-11)", options=[str(i) for i in range(1, 12)])
            pos_prio = l2_c3.selectbox("Prioritet", options=["A - Start-11", "B - Trupspiller", "C - Udviklingsspiller"])
            # ... (Resten af sliderne og tekstfelter)
            
        # [Her indsættes resten af din eksisterende form-logik for gem-knappen]
        st.form_submit_button("Gem Rapport", use_container_width=True)
