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

# --- MODAL: SPILLERPROFIL (AVANCERET) ---
@st.dialog("Seneste Scout Rapport", width="large")
def vis_spiller_modal(valgt_navn, alle_rapporter, billed_map, career_df=None):
    spiller_historik = alle_rapporter[alle_rapporter['NAVN'] == valgt_navn].sort_values('DATO', ascending=True)
    
    if spiller_historik.empty:
        st.error(f"Ingen data fundet for {valgt_navn}")
        return
        
    nyeste = spiller_historik.iloc[-1]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    
    # Billed-logik: Prioritér IMAGEDATAURL fra mappet, ellers brug standard fallback
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
                fill='toself', 
                line_color='#df003b'
            ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[1, 6], tickfont=dict(size=10))), 
                showlegend=False,
                height=400, 
                margin=dict(l=50, r=50, t=20, b=20),
                autosize=True
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
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
        fig_evol = go.Figure(go.Scatter(x=spiller_historik['DATO'], y=spiller_historik['RATING_AVG'], mode='lines+markers', line_color='#df003b'))
        fig_evol.update_layout(yaxis=dict(range=[1, 6]), height=300)
        st.plotly_chart(fig_evol, use_container_width=True)

    with t4:
        st.markdown("### Karriereoversigt")
        if career_df is not None:
            stats = career_df[career_df['PLAYER_WYID'].apply(rens_id) == pid].copy()
            if not stats.empty:
                st.dataframe(stats.drop_duplicates(subset=['SEASONNAME', 'TEAMNAME', 'COMPETITIONNAME']).sort_values('SEASONNAME', ascending=False), use_container_width=True, hide_index=True)

# --- HOVEDSIDE ---
def vis_side(dp):    
    df_local = dp.get("scout_reports", pd.DataFrame()).copy()
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()).copy()
    career_df = dp.get("career_data", None)
    
    # Erstat blokken i vis_side med denne mere sikre version:
    billed_map = {}
    if not df_wyscout.empty:
        # Vi leder efter alle tænkelige navne for billed-kolonnen
        mulige_kolonner = ['IMAGEDATAURL', 'PLAYER_IMAGE_URL', 'IMAGE_URL']
        fundet_kolonne = next((c for c in mulige_kolonner if c in df_wyscout.columns), None)
        
        if fundet_kolonne:
            billed_map = dict(zip(df_wyscout['PLAYER_WYID'].apply(rens_id), df_wyscout[fundet_kolonne]))

    unique_players = {}
    def get_safe_val(row, col_name, default=""):
        val = row.get(col_name, default)
        return str(val) if pd.notna(val) else default

    def add_to_options(df):
        if df is None or (isinstance(df, pd.DataFrame) and df.empty): return
        df_temp = df.copy()
        df_temp.columns = [str(c).upper().strip() for c in df_temp.columns]
        for _, r in df_temp.iterrows():
            p_id = rens_id(r.get('PLAYER_WYID'))
            if not p_id: continue
            f_name, l_name = get_safe_val(r, 'FIRSTNAME'), get_safe_val(r, 'LASTNAME')
            fuldt_navn = f"{f_name} {l_name}".strip() if f_name or l_name else (get_safe_val(r, 'PLAYER_NAME') or get_safe_val(r, 'NAVN') or "Ukendt")
            klub = get_safe_val(r, 'TEAMNAME') or get_safe_val(r, 'KLUB') or "Ukendt klub"
            b_date = r.get('BIRTHDATE') or r.get('DOB') or ""
            try: birth_val = pd.to_datetime(b_date).strftime("%Y-%m-%d") if pd.notna(b_date) else ""
            except: birth_val = str(b_date)
            
            if p_id not in unique_players:
                unique_players[p_id] = {"label": f"{fuldt_navn} ({klub})", "data": {"n": fuldt_navn, "id": p_id, "pos": get_safe_val(r, 'ROLECODE3') or get_safe_val(r, 'POSITION'), "klub": klub, "birth": birth_val}}

    add_to_options(df_local)
    add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    data = {"n": "", "id": "", "pos": "", "klub": "", "birth": ""}
    
    # LINJE 1: Vælg spiller
    row1_c1, row1_c2, row1_c3 = st.columns([3, 1.5, 1])
    with row1_c1:
        sel_id = st.selectbox("Vælg spiller", [""] + options_list, format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...", key="player_selector")
        if sel_id: data = unique_players[sel_id]["data"]

    existing_report = None
    if sel_id and not df_local.empty:
        df_local['MATCH_ID'] = df_local['PLAYER_WYID'].apply(rens_id)
        matches = df_local[df_local['MATCH_ID'] == str(sel_id)]
        if not matches.empty: existing_report = matches.sort_values('DATO', ascending=False).iloc[0]

    with row1_c2:
        st.text_input("Seneste rapport", value=existing_report['DATO'] if existing_report is not None else "-", disabled=True)
    with row1_c3:
        st.markdown("<p style='margin-bottom: 28px;'></p>", unsafe_allow_html=True)
        if existing_report is not None:
            if st.button("Åbn rapport", use_container_width=True): 
                vis_spiller_modal(data["n"], df_local, billed_map, career_df)
        else: st.button("Ingen data", disabled=True, use_container_width=True)

    # LINJE 2: Info-felter
    row2_c1, row2_c2, row2_c3, row2_c4 = st.columns([1, 2, 1.5, 1.5])
    row2_c1.text_input("POS", value=data['pos'], disabled=True)
    row2_c2.text_input("KLUB", value=data['klub'], disabled=True)
    row2_c3.text_input("FØDSELSDAG", value=data['birth'], disabled=True)
    scout_navn = row2_c4.text_input("SCOUT", value=st.session_state.get("user", "HIF Scout"), disabled=True)

    # --- FORM TIL RAPPORT ---
    with st.form("rapport_form", clear_on_submit=True):
        with st.container(border=True):
            st.markdown("**Stamdata & Status**")
            l2_c1, l2_c2, l2_c3 = st.columns(3)
            status_label = l2_c1.selectbox("Status", ["Interessant", "Hold øje", "Kig nærmere", "Køb", "Prioritet"])
            pos_nr = l2_c2.selectbox("POS (1-11)", options=[str(i) for i in range(1, 12)])
            pos_prio = l2_c3.selectbox("Prioritet", options=["A - Start-11", "B - Trupspiller", "C - Udviklingsspiller"])

            l3_c1, l3_c2, l3_c3 = st.columns(3)
            pot = l3_c1.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
            forv = l3_c2.selectbox("Forventning", ["Realistisk", "Kræver overtalelse", "Forhandling", "Svær"])
            k_udloeb = l3_c3.date_input("Kontraktudløb", value=None)

            l4_c1, l4_c2, l4_c3 = st.columns(3)
            lon = l4_c1.number_input("Lønniveau", min_value=0, step=1000, value=0)
            vindue = l4_c2.selectbox("Transfervindue", ["Sommer 26", "Vinter 26/27", "Sommer 27", "Nuværende trup"])
            er_emne = l4_c3.checkbox("Transferemne?", value=False)

        with st.container(border=True):
            st.markdown("**Vurdering & Egenskaber**")
            m1, m2, m3, m4 = st.columns(4)
            beslut = m1.select_slider("Beslutsomhed", options=list(range(1, 7)), value=3)
            fart = m2.select_slider("Fart", options=list(range(1, 7)), value=3)
            agg = m3.select_slider("Aggresivitet", options=list(range(1, 7)), value=3)
            att = m4.select_slider("Attitude", options=list(range(1, 7)), value=3)
            m5, m6, m7, m8 = st.columns(4)
            udh = m5.select_slider("Udholdenhed", options=list(range(1, 7)), value=3)
            led = m6.select_slider("Lederegenskaber", options=list(range(1, 7)), value=3)
            tek = m7.select_slider("Teknik", options=list(range(1, 7)), value=3)
            intel = m8.select_slider("Intelligens", options=list(range(1, 7)), value=3)

            st.markdown("---")
            v1, v2, v3 = st.columns(3)
            styrker, udv, vurder = v1.text_area("Styrker"), v2.text_area("Udvikling"), v3.text_area("Vurdering")
            kommentar = st.text_area("Kommentar (uddybende)", height=100)

        if st.form_submit_button("Gem Rapport", use_container_width=True):
            if not data["n"]: st.error("Vælg en spiller!")
            else:
                avg = round(sum([beslut, fart, agg, att, udh, led, tek, intel])/8, 2)
                ny = {
                    "PLAYER_WYID": data["id"], 
                    "DATO": datetime.now().strftime("%Y-%m-%d"), 
                    "NAVN": data["n"], 
                    "KLUB": data["klub"], 
                    "POSITION": data["pos"], 
                    "BIRTHDATE": data["birth"], 
                    "RATING_AVG": avg, 
                    "STATUS": status_label, 
                    "POTENTIALE": pot, 
                    "STYRKER": styrker, 
                    "UDVIKLING": udv, 
                    "VURDERING": vurder, 
                    "BESLUTSOMHED": float(beslut), 
                    "FART": float(fart), 
                    "AGGRESIVITET": float(agg), 
                    "ATTITUDE": float(att), 
                    "UDHOLDENHED": float(udh), 
                    "LEDEREGENSKABER": float(led), 
                    "TEKNIK": float(tek), 
                    "SPILINTELLIGENS": float(intel), 
                    "SCOUT": scout_navn, 
                    "KONTRAKT": str(k_udloeb) if k_udloeb else "", 
                    "FORVENTNING": forv, 
                    "POS_PRIORITET": pos_prio, 
                    "POS": pos_nr, 
                    "LON": f"{lon:,}".replace(",", "."), 
                    "SKYGGEHOLD": False, 
                    "KOMMENTAR": kommentar, 
                    "ER_EMNE": er_emne, 
                    "TRANSFER_VINDUE": vindue, 
                    "POS_343": 0.0, "POS_433": 0.0, "POS_352": 0.0
                }
                c, sha = get_github_file(FILE_PATH)
                df_f = pd.concat([pd.read_csv(StringIO(c), low_memory=False) if c else pd.DataFrame(), pd.DataFrame([ny])], ignore_index=True)
                if push_to_github(FILE_PATH, f"Rapport: {data['n']}", df_f[COL_ORDER].to_csv(index=False), sha) in [200, 201]:
                    st.success("Gemt!"); time.sleep(1); st.rerun()
