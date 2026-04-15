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
    
    # Billed-logik
    fallback_url = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png"
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    c1, c2 = st.columns([1, 3])
    with c1:
        try:
            st.image(img_url, width=120)
        except:
            st.image(fallback_url, width=120)
            
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
                fill='toself', line_color='#df003b'
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[1, 6], tickfont=dict(size=10))),
                showlegend=False, height=350, margin=dict(l=40, r=40, t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
        with col_text:
            st.write("**Styrker**")
            st.info(nyeste.get('STYRKER', '-'))
            st.write("**Vurdering**")
            st.success(nyeste.get('VURDERING', '-'))

    with t2:
        st.dataframe(spiller_historik.sort_values('DATO', ascending=False), use_container_width=True, hide_index=True)

    with t3:
        st.markdown("### Rating over tid")
        fig_evol = go.Figure(go.Scatter(x=spiller_historik['DATO'], y=spiller_historik['RATING_AVG'], mode='lines+markers', line_color='#df003b'))
        fig_evol.update_layout(yaxis=dict(range=[1, 6]), height=300)
        st.plotly_chart(fig_evol, use_container_width=True)

    with t4:
        st.markdown("### Karriereoversigt")
        if career_df is not None:
            stats = career_df[career_df['PLAYER_WYID'].apply(rens_id) == pid].copy()
            if not stats.empty:
                stats_clean = stats.drop_duplicates(subset=['SEASONNAME', 'TEAMNAME', 'COMPETITIONNAME']).sort_values('SEASONNAME', ascending=False)
                st.dataframe(stats_clean, use_container_width=True, hide_index=True)

# --- HOVEDSIDE ---
def vis_side(dp):    
    # Hent data fra data-pack (dp)
    df_local = dp.get("scout_reports", pd.DataFrame()).copy()
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()).copy()
    career_df = dp.get("career_data", None)
    
    # 1. Byg billed_map fra Wyscout listen
    billed_map = {}
    if not df_wyscout.empty:
        # Tjekker for mulige kolonnenavne (IMAGEDATAURL er standard i din app)
        img_col = next((c for c in ['IMAGEDATAURL', 'PLAYER_IMAGE_URL'] if c in df_wyscout.columns), None)
        if img_col:
            billed_map = dict(zip(df_wyscout['PLAYER_WYID'].apply(rens_id), df_wyscout[img_col]))

    # 2. Saml unikke spillere til dropdown
    unique_players = {}
    def get_safe_val(row, col_name):
        val = row.get(col_name, "")
        return str(val) if pd.notna(val) else ""

    def add_to_options(df):
        if df is None or df.empty: return
        for _, r in df.iterrows():
            p_id = rens_id(r.get('PLAYER_WYID') or r.get('player_wyid'))
            if not p_id: continue
            
            # Navne-logik
            navn = get_safe_val(r, 'NAVN') or get_safe_val(r, 'PLAYER_NAME')
            if not navn:
                f, l = get_safe_val(r, 'FIRSTNAME'), get_safe_val(r, 'LASTNAME')
                navn = f"{f} {l}".strip() or "Ukendt"
            
            klub = get_safe_val(r, 'KLUB') or get_safe_val(r, 'TEAMNAME') or "Ukendt"
            
            if p_id not in unique_players:
                unique_players[p_id] = {
                    "label": f"{navn} ({klub})",
                    "data": {"n": navn, "id": p_id, "pos": get_safe_val(r, 'POSITION') or get_safe_val(r, 'ROLECODE3'), "klub": klub}
                }

    add_to_options(df_local)
    add_to_options(df_wyscout)
    
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # --- UI LAYOUT ---
    row1_c1, row1_c2, row1_c3 = st.columns([3, 1.5, 1])
    
    with row1_c1:
        sel_id = st.selectbox("Vælg spiller", [""] + options_list, format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...", key="player_selector")
        data = unique_players[sel_id]["data"] if sel_id else {"n": "", "id": "", "pos": "", "klub": ""}

    existing_report = None
    if sel_id and not df_local.empty:
        matches = df_local[df_local['PLAYER_WYID'].apply(rens_id) == str(sel_id)]
        if not matches.empty:
            existing_report = matches.sort_values('DATO', ascending=False).iloc[0]

    with row1_c2:
        st.text_input("Seneste rapport", value=existing_report['DATO'] if existing_report is not None else "-", disabled=True)
    
    with row1_c3:
        st.markdown("<p style='margin-bottom: 28px;'></p>", unsafe_allow_html=True)
        if existing_report is not None:
            if st.button("Åbn rapport", use_container_width=True):
                vis_spiller_modal(data["n"], df_local, billed_map, career_df)
        else:
            st.button("Ingen data", disabled=True, use_container_width=True)

    # --- FORM ---
    with st.form("rapport_form", clear_on_submit=True):
        st.markdown("### Ny Scout Rapport")
        c1, c2, c3 = st.columns(3)
        status = c1.selectbox("Status", ["Interessant", "Hold øje", "Køb", "Prioritet"])
        pot = c2.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
        prio = c3.selectbox("Prioritet", ["A - Start-11", "B - Trup", "C - Udvikling"])

        st.markdown("#### Egenskaber (1-6)")
        m1, m2, m3, m4 = st.columns(4)
        beslut = m1.select_slider("Beslutsomhed", options=range(1, 7), value=3)
        fart = m2.select_slider("Fart", options=range(1, 7), value=3)
        tek = m3.select_slider("Teknik", options=range(1, 7), value=3)
        intel = m4.select_slider("Intelligens", options=range(1, 7), value=3)

        styrker = st.text_area("Styrker")
        vurdering = st.text_area("Vurdering")

        if st.form_submit_button("Gem Rapport", use_container_width=True):
            if not sel_id:
                st.error("Vælg en spiller først!")
            else:
                avg = round((beslut + fart + tek + intel) / 4, 2)
                ny_rapport = {
                    "PLAYER_WYID": data["id"],
                    "DATO": datetime.now().strftime("%Y-%m-%d"),
                    "NAVN": data["n"],
                    "KLUB": data["klub"],
                    "POSITION": data["pos"],
                    "RATING_AVG": avg,
                    "STATUS": status,
                    "POTENTIALE": pot,
                    "POS_PRIORITET": prio,
                    "STYRKER": styrker,
                    "VURDERING": vurdering,
                    "BESLUTSOMHED": float(beslut),
                    "FART": float(fart),
                    "TEKNIK": float(tek),
                    "SPILINTELLIGENS": float(intel)
                }
                # Hent nyeste fil for at undgå overwrite-fejl
                content, sha = get_github_file(FILE_PATH)
                df_current = pd.read_csv(StringIO(content)) if content else pd.DataFrame()
                df_updated = pd.concat([df_current, pd.DataFrame([ny_rapport])], ignore_index=True)
                
                res = push_to_github(FILE_PATH, f"Rapport: {data['n']}", df_updated.to_csv(index=False), sha)
                if res in [200, 201]:
                    st.success("Gemt!"); time.sleep(1); st.rerun()
