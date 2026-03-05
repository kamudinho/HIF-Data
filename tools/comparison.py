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

def vis_spiller_billede(img_url, pid, w=75):
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    img_clean = str(img_url).strip() if pd.notna(img_url) else ""
    pid_clean = rens_id(pid)
    url = img_clean if img_clean not in ["0", "0.0", "nan", ""] else f"https://cdn5.wyscout.com/photos/players/public/{pid_clean}.png"
    if not pid_clean and not img_clean: url = std
    st.image(url, width=w)

def render_stat_col(label, value, align="left"):
    st.markdown(f"""
        <div style="text-align: {align}; margin-bottom: 12px; line-height: 1.1;">
            <p style="margin:0; font-size: 0.7rem; color: #888; text-transform: uppercase; font-weight: 700;">{label}</p>
            <p style="margin:0; font-size: 1.6rem; font-weight: 800;">{value}</p>
        </div>
    """, unsafe_allow_html=True)

def vis_side(df_spillere, d1, d2, career_df, d3):
    # CSS til at fjerne spildplads
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0.2rem !important; }
            [data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-start; }
        </style>
    """, unsafe_allow_html=True)

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except: return

    billed_map = {rens_id(row['PLAYER_WYID']): row['IMAGEDATAURL'] for _, row in d3.iterrows()} if d3 is not None else {}
    navne_liste = sorted(df_s['Navn'].unique().tolist())

    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Spiller 1", navne_liste, index=0)
    s2_navn = c_sel2.selectbox("Spiller 2", navne_liste, index=min(1, len(navne_liste)-1))

    def hent_data(navn):
        s_match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if s_match.empty: return None
        n = s_match.iloc[0]
        pid = n['PID_CLEAN']
        
        pos_str, klub_str = "Ukendt", "Ukendt"
        if df_spillere is not None and not df_spillere.empty:
            df_p = df_spillere.copy()
            df_p.columns = [c.upper() for c in df_p.columns]
            m = df_p[df_p['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                pos_str = map_position(m.iloc[0].get('ROLECODE3', ''))
                klub_str = m.iloc[0].get('TEAMNAME', 'Hvidovre IF')

        stats = {"Kampe": 0, "Mål": 0, "Assist": 0, "Min": 0}
        if career_df is not None:
            cdf = career_df.copy()
            cdf.columns = [c.upper() for c in cdf.columns]
            c_m = cdf[(cdf['PLAYER_WYID'].apply(rens_id) == pid) & (cdf['SEASONNAME'].str.contains("2025/2026", na=False))]
            if not c_m.empty:
                stats = {"Kampe": int(c_m.iloc[0].get('APPEARANCES', 0)), "Mål": int(c_m.iloc[0].get('GOAL', 0)),
                         "Assist": int(c_m.iloc[0].get('ASSIST', 0)), "Min": int(c_m.iloc[0].get('MINUTESPLAYED', 0))}

        return {
            "navn": navn, "pid": pid, "img": billed_map.get(pid), "pos": pos_str, "klub": klub_str, "stats": stats,
            "vurdering": n.get('Vurdering', 'Ingen scouting-notater fundet.'),
            "r": [n.get(k, 0) for k in ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']]
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)
    st.markdown("<hr style='margin:10px 0; border:0; border-top:1px solid #eee;'>", unsafe_allow_html=True)

    # --- TOP SEKTION ---
    h1, h2 = st.columns(2)
    with h1:
        st.markdown(f"<h1 style='color:#df003b; margin:0; font-size:2.2rem;'>{p1['navn']}</h1>", unsafe_allow_html=True)
        ci, ct = st.columns([1, 4])
        with ci: vis_spiller_billede(p1["img"], p1["pid"])
        with ct: st.markdown(f"<p style='color:#888; margin-top:5px;'>{p1['pos']}<br>{p1['klub']}</p>", unsafe_allow_html=True)
    with h2:
        st.markdown(f"<h1 style='color:#0056a3; margin:0; text-align:right; font-size:2.2rem;'>{p2['navn']}</h1>", unsafe_allow_html=True)
        ct, ci = st.columns([4, 1])
        with ci: vis_spiller_billede(p2["img"], p2["pid"])
        with ct: st.markdown(f"<div style='text-align:right; color:#888; margin-top:5px;'>{p2['pos']}<br>{p2['klub']}</div>", unsafe_allow_html=True)

    # --- CENTER SEKTION (STATS & RADAR) ---
    st.markdown("<div style='margin-top: -40px;'>", unsafe_allow_html=True)
    s1, rad, s2 = st.columns([1.5, 5, 1.5])
    
    with s1:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        for k, v in p1["stats"].items(): render_stat_col(k, v)

    with s2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        for k, v in p2["stats"].items(): render_stat_col(k, v, "right")

    with rad:
        labels = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
        fig = go.Figure()
        for p, col in [(p1, '#df003b'), (p2, '#0056a3')]:
            fig.add_trace(go.Scatterpolar(r=p['r']+[p['r'][0]], theta=labels+[labels[0]], fill='toself', name=p['navn'], line_color=col, opacity=0.5))

        fig.update_layout(
            polar=dict(
                gridshape='linear',
                radialaxis=dict(visible=True, range=[0, 6], gridcolor="#eee", linecolor="#000", tickfont=dict(size=9)),
                angularaxis=dict(gridcolor="#eee", linecolor="#000", linewidth=1.5)
            ),
            height=480, margin=dict(l=50, r=50, t=10, b=10), showlegend=False, paper_bgcolor='white'
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

    # --- BUND SEKTION ---
    v1, v2 = st.columns(2)
    v1.markdown(f"<div style='background:#fff0f3; padding:15px; border-left:5px solid #df003b; border-radius:4px;'><b>Scout vurdering:</b><br><span style='font-size:0.9rem;'>{p1['vurdering']}</span></div>", unsafe_allow_html=True)
    v2.markdown(f"<div style='background:#f0f7ff; padding:15px; border-right:5px solid #0056a3; border-radius:4px; text-align:right;'><b>Scout vurdering:</b><br><span style='font-size:0.9rem;'>{p2['vurdering']}</span></div>", unsafe_allow_html=True)
