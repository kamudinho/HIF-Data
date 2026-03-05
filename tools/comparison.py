import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- HJÆLPEFUNKTIONER ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def map_position(pos_code):
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back",
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt",
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber",
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    return pos_map.get(rens_id(pos_code), "Ukendt")

def vis_spiller_billede(img_url, pid, w=70):
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    pid_c = rens_id(pid)
    url = str(img_url).strip() if pd.notna(img_url) and str(img_url) not in ["0", "0.0", "nan", ""] else f"https://cdn5.wyscout.com/photos/players/public/{pid_c}.png"
    if not pid_c: url = std
    st.image(url, width=w)

def render_stat(label, val, align="left"):
    # Kompakt tal-look uden spildplads
    st.markdown(f"""
        <div style="text-align: {align}; margin-bottom: -5px;">
            <p style="margin:0; font-size: 0.7rem; color: gray; text-transform: uppercase;">{label}</p>
            <p style="margin:0; font-size: 1.4rem; font-weight: 800; line-height: 1.1;">{val}</p>
        </div>
    """, unsafe_allow_html=True)

# --- HOVEDFUNKTION ---
def vis_side(df_spillere, d1, d2, career_df, d3):
    # CSS der tvinger elementerne tæt sammen
    st.markdown("""
        <style>
            .block-container { padding-top: 0.5rem !important; }
            [data-testid="column"] { gap: 0rem !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0.3rem !important; }
            h1, h2, h3 { margin-bottom: -10px !important; }
        </style>
    """, unsafe_allow_html=True)

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except: return

    billed_map = {rens_id(row['PLAYER_WYID']): row['IMAGEDATAURL'] for _, row in d3.iterrows()} if d3 is not None else {}
    navne = sorted(df_s['Navn'].unique().tolist())

    # Selectors
    sel1, sel2 = st.columns(2)
    s1_navn = sel1.selectbox("Spiller 1", navne, index=0, label_visibility="collapsed")
    s2_navn = sel2.selectbox("Spiller 2", navne, index=min(1, len(navne)-1), label_visibility="collapsed")

    def hent_data(navn):
        match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if match.empty: return None
        n = match.iloc[0]
        pid = n['PID_CLEAN']
        
        # Hent Pos og Klub fra df_spillere
        pos_s, klub_s = "Ukendt", "Ukendt"
        if df_spillere is not None:
            m = df_spillere[df_spillere['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                pos_s = map_position(m.iloc[0].get('ROLECODE3', ''))
                klub_s = m.iloc[0].get('TEAMNAME', 'HIF')

        # Karrierestats
        stats = {"Kampe": 0, "Mål": 0, "Assist": 0, "Min": 0}
        if career_df is not None:
            c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & (career_df['SEASONNAME'].str.contains("2025/2026", na=False))]
            if not c_m.empty:
                stats = {"Kampe": int(c_m.iloc[0].get('APPEARANCES', 0)), "Mål": int(c_m.iloc[0].get('GOAL', 0)),
                         "Assist": int(c_m.iloc[0].get('ASSIST', 0)), "Min": int(c_m.iloc[0].get('MINUTESPLAYED', 0))}

        return {
            "navn": navn, "pid": pid, "img": billed_map.get(pid), "pos": pos_s, "klub": klub_s,
            "stats": stats, "vurdering": n.get('Vurdering', '-'),
            "r": [n.get(k, 0) for k in ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']]
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)
    if not p1 or not p2: return

    st.markdown("<hr style='margin:5px 0; opacity:0.2;'>", unsafe_allow_html=True)

    # --- TOP: Navne & Info ---
    t1, t2 = st.columns(2)
    with t1:
        st.markdown(f"<h2 style='color:#df003b; margin:0;'>{p1['navn']}</h2>", unsafe_allow_html=True)
        c_i, c_t = st.columns([1, 4])
        with c_i: vis_spiller_billede(p1["img"], p1["pid"])
        with c_t: st.markdown(f"<p style='color:gray; font-size:0.8rem; line-height:1.2;'>{p1['pos']}<br>{p1['klub']}</p>", unsafe_allow_html=True)
    with t2:
        st.markdown(f"<h2 style='text-align:right; color:#0056a3; margin:0;'>{p2['navn']}</h2>", unsafe_allow_html=True)
        c_t, c_i = st.columns([4, 1])
        with c_i: vis_spiller_billede(p2["img"], p2["pid"])
        with c_t: st.markdown(f"<div style='text-align:right; color:gray; font-size:0.8rem; line-height:1.2;'>{p2['pos']}<br>{p2['klub']}</div>", unsafe_allow_html=True)

    # --- CENTER: Stats & Radar (8-kant) ---
    # Vi bruger negativ margin til at suge radaren op til navnene
    st.markdown("<div style='margin-top: -30px;'>", unsafe_allow_html=True)
    sl, sm, sr = st.columns([1.5, 5, 1.5])
    
    with sl:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        for k, v in p1["stats"].items(): render_stat(k, v)

    with sr:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        for k, v in p2["stats"].items(): render_stat(k, v, "right")

    with sm:
        labels = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
        fig = go.Figure()
        for p, color in [(p1, '#df003b'), (p2, '#0056a3')]:
            fig.add_trace(go.Scatterpolar(r=p['r']+[p['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=color, opacity=0.4))

        fig.update_layout(
            polar=dict(
                gridshape='linear', # 8-kantet
                radialaxis=dict(visible=True, range=[0, 6], gridcolor="#eee", linecolor="#000", tickfont=dict(size=8)),
                angularaxis=dict(linecolor="#000", gridcolor="#eee", linewidth=1.5)
            ),
            height=420, margin=dict(l=40, r=40, t=10, b=10), showlegend=False, paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

    # --- BUND: Vurdering ---
    b1, b2 = st.columns(2)
    b1.markdown(f"<div style='background:#fff0f3; padding:10px; border-left:4px solid #df003b; border-radius:4px; font-size:0.85rem;'><b>Vurdering:</b><br>{p1['vurdering']}</div>", unsafe_allow_html=True)
    b2.markdown(f"<div style='background:#f0f7ff; padding:10px; border-right:4px solid #0056a3; border-radius:4px; text-align:right; font-size:0.85rem;'><b>Vurdering:</b><br>{p2['vurdering']}</div>", unsafe_allow_html=True)
