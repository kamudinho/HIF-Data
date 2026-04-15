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

def render_rapport_indhold(report, keys, unique_suffix=""):
    """Tegner rapportens indhold med unikt ID for at undgå DuplicateElementId"""
    col_stats, col_radar, col_text = st.columns([0.8, 2.0, 1.5])
    
    with col_stats:
        st.markdown("**Egenskaber**")
        for k in keys:
            st.write(f"{k.capitalize()}: **{report.get(k, '-')}**")
    
    with col_radar:
        r_vals = []
        for k in keys:
            try: 
                v = float(str(report.get(k, 1)).replace(',', '.'))
                r_vals.append(v)
            except: r_vals.append(1.0)
        
        fig = go.Figure(data=go.Scatterpolar(
            r=r_vals + [r_vals[0]], 
            theta=[k.capitalize() for k in keys] + [keys[0].capitalize()], 
            fill='toself', line_color='#df003b'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[1, 6])), 
            showlegend=False, height=350,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        # UNIQUE KEY tilføjet her for at løse fejlen:
        st.plotly_chart(fig, use_container_width=True, key=f"radar_{report.get('DATO')}_{unique_suffix}")
        
    with col_text:
        st.write("**Styrker**")
        st.info(report.get('STYRKER', '-'))
        st.write("**Udvikling**")
        st.info(report.get('UDVIKLING', '-'))
        st.write("**Vurdering**")
        st.success(report.get('VURDERING', '-'))
        if report.get('KOMMENTAR'):
            st.write("**Uddybende Kommentar**")
            st.write(report.get('KOMMENTAR'))

# --- POPUP DIALOG ---
@st.dialog("Spillerrapport", width="large")
def show_report_popup(valgt_navn, alle_rapporter, billed_map):
    # Sorter historik (nyeste først)
    spiller_historik = alle_rapporter[alle_rapporter['NAVN'] == valgt_navn].sort_values('DATO', ascending=False)
    if spiller_historik.empty:
        st.error("Ingen data fundet")
        return
        
    nyeste = spiller_historik.iloc[0]
    pid = rens_id(nyeste.get('PLAYER_WYID'))
    img_url = billed_map.get(pid) or f"https://cdn5.wyscout.com/photos/players/public/{pid}.png"
    
    c1, c2 = st.columns([1, 3])
    with c1:
        st.image(img_url, width=150)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"**Klub:** {nyeste.get('KLUB', '-')} | **ID:** {pid}")

    t1, t2 = st.tabs(["Seneste Rapport", "Historik"])
    keys = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']

    with t1:
        render_rapport_indhold(nyeste, keys, unique_suffix="latest")

    with t2:
        # CSS til at gøre expander-overskriften mindre specifikt i dette vindue
        st.markdown("""
            <style>
            .st-emotion-cache-p5m613 p, .st-emotion-cache-1pxmth6 p {
                font-size: 13px !important;
                font-weight: 500 !important;
            }
            /* Styling af selve expander-titlen */
            div[data-testid="stExpander"] details summary p {
                font-size: 13px !important;
                color: #333 !important;
            }
            </style>
            """, unsafe_allow_html=True)

        for idx, row in spiller_historik.iterrows():
            # Overskuelig header - nu påvirket af CSS ovenfor
            header = f"{row['DATO']} | {row.get('RATING_AVG', '-')} | {row.get('STATUS', '-')} ({row.get('SCOUT', 'Scout')})"
            
            with st.expander(header):
                # Hurtig-info række
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Rating", row.get('RATING_AVG', '-'))
                m2.metric("Potentiale", row.get('POTENTIALE', '-'))
                m3.metric("Status", row.get('STATUS', '-'))
                m4.metric("Scout", row.get('SCOUT', '-'))
                
                st.divider()
                
                # Den fulde rapport-visning inkl. radar (bruger unikt suffix fra din tidligere fejl-rettelse)
                render_rapport_indhold(row, keys, unique_suffix=f"hist_{idx}")

# --- HOVEDSIDE ---
def vis_side(dp):    
    df_local = dp.get("scout_reports", pd.DataFrame()).copy()
    df_wyscout = dp.get("wyscout_players", pd.DataFrame()).copy()

    billed_map = {}
    if not df_wyscout.empty and 'IMAGEDATAURL' in df_wyscout.columns:
        billed_map = dict(zip(df_wyscout['PLAYER_WYID'].apply(rens_id), df_wyscout['IMAGEDATAURL']))

    unique_players = {}
    def get_safe_val(row, col_name):
        val = row.get(col_name, "")
        return str(val) if pd.notna(val) else ""

    def add_to_options(df):
        if df is None or (isinstance(df, pd.DataFrame) and df.empty): return
        for _, r in df.iterrows():
            p_id = rens_id(r.get('PLAYER_WYID'))
            if not p_id: continue
            f, l = get_safe_val(r, 'FIRSTNAME'), get_safe_val(r, 'LASTNAME')
            navn = f"{f} {l}".strip() if f or l else (get_safe_val(r, 'PLAYER_NAME') or get_safe_val(r, 'NAVN') or "Ukendt")
            klub = get_safe_val(r, 'TEAMNAME') or get_safe_val(r, 'KLUB') or "Ukendt"
            if p_id not in unique_players:
                unique_players[p_id] = {"label": f"{navn} ({klub})", "data": {"n": navn, "id": p_id, "pos": get_safe_val(r, 'POSITION'), "klub": klub, "birth": get_safe_val(r, 'BIRTHDATE')}}

    add_to_options(df_local); add_to_options(df_wyscout)
    options_list = sorted(list(unique_players.keys()), key=lambda x: unique_players[x]["label"])

    # HEADER & VALG
    data = {"n": "", "id": "", "pos": "", "klub": "", "birth": ""}
    r1c1, r1c2, r1c3 = st.columns([3, 1.5, 1])
    with r1c1:
        sel_id = st.selectbox("Vælg spiller", [""] + options_list, format_func=lambda x: unique_players[x]["label"] if x else "Vælg spiller...")
        if sel_id: data = unique_players[sel_id]["data"]

    existing_report = None
    if sel_id and not df_local.empty:
        m = df_local[df_local['PLAYER_WYID'].apply(rens_id) == str(sel_id)]
        if not m.empty: existing_report = m.sort_values('DATO', ascending=False).iloc[0]

    with r1c2: st.text_input("Seneste rapport", value=existing_report['DATO'] if existing_report is not None else "-", disabled=True)
    with r1c3:
        st.markdown("<p style='margin-bottom: 28px;'></p>", unsafe_allow_html=True)
        if existing_report is not None:
            if st.button("Åbn rapport", use_container_width=True): show_report_popup(data["n"], df_local, billed_map)

    # STAMDATA RÆKKE
    r2c1, r2c2, r2c3, r2c4 = st.columns([1, 2, 1.5, 1.5])
    r2c1.text_input("POS", value=data['pos'], disabled=True)
    r2c2.text_input("KLUB", value=data['klub'], disabled=True)
    r2c3.text_input("FØDSEL", value=data['birth'], disabled=True)
    scout_navn = r2c4.text_input("SCOUT", value=st.session_state.get("user", "HIF Scout"), disabled=True)

    # RAPPORT FORM
    with st.form("rapport_form", clear_on_submit=True):
        with st.container(border=True):
            st.markdown("**Stamdata & Status**")
            l2c1, l2c2, l2c3 = st.columns(3)
            status = l2c1.selectbox("Status", ["Interessant", "Hold øje", "Kig nærmere", "Køb", "Prioritet"])
            pos_nr = l2c2.selectbox("POS (1-11)", options=[str(i) for i in range(1, 12)])
            prio = l2c3.selectbox("Prioritet", options=["A - Start-11", "B - Trupspiller", "C - Udviklingsspiller"])

            l3c1, l3c2, l3c3 = st.columns(3)
            pot = l3c1.selectbox("Potentiale", ["Lavt", "Middel", "Højt", "Top"])
            forvent = l3c2.selectbox("Forventning", ["Realistisk", "Kræver overtalelse", "Svær"])
            kontrakt = l3c3.date_input("Kontraktudløb", value=None)

            l4c1, l4c2, l4c3 = st.columns(3)
            lon = l4c1.number_input("Lønniveau", value=0)
            vindue = l4c2.selectbox("Transfervindue", ["Sommer 26", "Vinter 26/27", "Sommer 27"])
            er_emne = l4c3.checkbox("Transferemne?")

        with st.container(border=True):
            st.markdown("**Vurdering & Egenskaber**")
            m1, m2, m3, m4 = st.columns(4)
            b_des = m1.select_slider("Beslutsomhed", options=range(1, 7), value=3)
            b_fart = m2.select_slider("Fart", options=range(1, 7), value=3)
            b_agg = m3.select_slider("Aggresivitet", options=range(1, 7), value=3)
            b_att = m4.select_slider("Attitude", options=range(1, 7), value=3)
            
            m5, m6, m7, m8 = st.columns(4)
            b_udh = m5.select_slider("Udholdenhed", options=range(1, 7), value=3)
            b_led = m6.select_slider("Lederegenskaber", options=range(1, 7), value=3)
            b_tek = m7.select_slider("Teknik", options=range(1, 7), value=3)
            b_int = m8.select_slider("Spilintelligens", options=range(1, 7), value=3)

            st.markdown("---")
            v1, v2, v3 = st.columns(3)
            styrker = v1.text_area("Styrker")
            udv = v2.text_area("Udvikling")
            vurder = v3.text_area("Vurdering")
            kommentar = st.text_area("Kommentar (uddybende)")

        if st.form_submit_button("Gem Rapport", use_container_width=True):
            if data["n"]:
                avg = round(sum([b_des, b_fart, b_agg, b_att, b_udh, b_led, b_tek, b_int])/8, 2)
                ny_rapport = {
                    "PLAYER_WYID": data["id"], "DATO": datetime.now().strftime("%Y-%m-%d"),
                    "NAVN": data["n"], "KLUB": data["klub"], "POSITION": data["pos"], "BIRTHDATE": data["birth"],
                    "RATING_AVG": avg, "STATUS": status, "POTENTIALE": pot, "STYRKER": styrker, "UDVIKLING": udv, "VURDERING": vurder,
                    "BESLUTSOMHED": float(b_des), "FART": float(b_fart), "AGGRESIVITET": float(b_agg), "ATTITUDE": float(b_att),
                    "UDHOLDENHED": float(b_udh), "LEDEREGENSKABER": float(b_led), "TEKNIK": float(b_tek), "SPILINTELLIGENS": float(b_int),
                    "SCOUT": scout_navn, "KONTRAKT": str(kontrakt), "FORVENTNING": forvent, "POS_PRIORITET": prio,
                    "POS": pos_nr, "LON": f"{lon:,}".replace(",", "."), "SKYGGEHOLD": False, "KOMMENTAR": kommentar,
                    "ER_EMNE": er_emne, "TRANSFER_VINDUE": vindue, "POS_343": 0.0, "POS_433": 0.0, "POS_352": 0.0
                }
                content, sha = get_github_file(FILE_PATH)
                df_old = pd.read_csv(StringIO(content), low_memory=False) if content else pd.DataFrame(columns=COL_ORDER)
                df_final = pd.concat([df_old, pd.DataFrame([ny_rapport])], ignore_index=True)[COL_ORDER]
                if push_to_github(FILE_PATH, f"Rapport: {data['n']}", df_final.to_csv(index=False), sha) in [200, 201]:
                    st.success("Gemt!"); time.sleep(1); st.rerun()
