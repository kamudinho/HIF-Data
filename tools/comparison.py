import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# HIF Identitet
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'

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

def vis_spiller_billede(img_url, pid):
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    pid_c = rens_id(pid)
    url = str(img_url).strip() if pd.notna(img_url) and str(img_url) not in ["0", "0.0", "nan", ""] else f"https://cdn5.wyscout.com/photos/players/public/{pid_c}.png"
    return url

def vis_side(df_spillere, d1, d2, career_df, d3):
    # CSS uden ordbogs-fejl
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; }
            [data-testid="stMetric"] {
                background-color: #f8f9fa;
                border-bottom: 3px solid #cc0000;
                border-radius: 4px;
                padding: 5px !important;
                text-align: center;
            }
            .blue-metric [data-testid="stMetric"] {
                border-bottom: 3px solid #0056a3 !important;
            }
            [data-testid="stMetricLabel"] { font-size: 0.6rem !important; font-weight: bold !important; color: #666 !important; }
            [data-testid="stMetricValue"] { font-size: 1.1rem !important; font-weight: 800 !important; }
        </style>
    """, unsafe_allow_html=True)

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except: return

    billed_map = {rens_id(row['PLAYER_WYID']): row['IMAGEDATAURL'] for _, row in d3.iterrows()} if d3 is not None else {}
    navne_liste = sorted(df_s['Navn'].unique().tolist())

    c1, c2 = st.columns(2)
    s1_navn = c1.selectbox("P1", navne_liste, index=0, label_visibility="collapsed")
    s2_navn = c2.selectbox("P2", navne_liste, index=min(1, len(navne_liste)-1), label_visibility="collapsed")

    def hent_data(navn):
        match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if match.empty: return None
        n = match.iloc[0]
        pid = n['PID_CLEAN']
        
        pos, klub = "Ukendt", "Ukendt"
        if df_spillere is not None:
            m = df_spillere[df_spillere['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                pos = map_position(m.iloc[0].get('ROLECODE3', ''))
                klub = m.iloc[0].get('TEAMNAME', 'Hvidovre IF')

        stats = {"KMP": 0, "MÅL": 0, "AST": 0, "MIN": 0}
        if career_df is not None:
            c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & (career_df['SEASONNAME'].str.contains("2025/2026", na=False))]
            if not c_m.empty:
                stats = {"KMP": int(c_m.iloc[0].get('APPEARANCES', 0)), "MÅL": int(c_m.iloc[0].get('GOAL', 0)),
                         "AST": int(c_m.iloc[0].get('ASSIST', 0)), "MIN": int(c_m.iloc[0].get('MINUTESPLAYED', 0))}
        
        return {"navn": navn, "pid": pid, "img": billed_map.get(pid), "pos": pos, "klub": klub, "stats": stats,
                "r": [n.get(k, 0.1) for k in ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']]}

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)
    if not p1 or not p2: return

    # Kolonner
    col_img1, col_data1, col_radar, col_data2, col_img2 = st.columns([1, 2.5, 4, 2.5, 1])

    with col_img1:
        st.image(vis_spiller_billede(p1["img"], p1["pid"]), use_container_width=True)

    with col_data1:
        st.markdown(f"<h4 style='margin:0; color:{HIF_RED};'>{p1['navn']}</h4>", unsafe_allow_html=True)
        st.caption(f"{p1['pos']} | {p1['klub']}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("KMP", p1['stats']['KMP'])
        m2.metric("MÅL", p1['stats']['MÅL'])
        m3.metric("AST", p1['stats']['AST'])
        m4.metric("MIN", p1['stats']['MIN'])

    with col_radar:
        labels = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_RED, opacity=0.3))
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_BLUE, opacity=0.3))
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=False, range=[0, 6]), 
                       angularaxis=dict(linecolor="black", gridcolor="#eee", tickfont=dict(size=8))),
            height=280, margin=dict(l=40, r=40, t=10, b=10), showlegend=False, paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with col_data2:
        st.markdown(f"<h4 style='margin:0; color:{HIF_BLUE}; text-align:right;'>{p2['navn']}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:right; margin:0; font-size:0.8rem; color:gray;'>{p2['pos']} | {p2['klub']}</p>", unsafe_allow_html=True)
        st.markdown('<div class="blue-metric">', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("KMP", p2['stats']['KMP'])
        m2.metric("MÅL", p2['stats']['MÅL'])
        m3.metric("AST", p2['stats']['AST'])
        m4.metric("MIN", p2['stats']['MIN'])
        st.markdown('</div>', unsafe_allow_html=True)

    with col_img2:
        st.image(vis_spiller_billede(p2["img"], p2["pid"]), use_container_width=True)

    st.markdown("---")
