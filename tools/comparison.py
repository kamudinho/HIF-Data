import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# HIF Identitet farver
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'

# --- HJÆLPEFUNKTIONER ---
def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def vis_spiller_billede(img_url, pid, w=60):
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    pid_c = rens_id(pid)
    url = str(img_url).strip() if pd.notna(img_url) and str(img_url) not in ["0", "0.0", "nan", ""] else f"https://cdn5.wyscout.com/photos/players/public/{pid_c}.png"
    if not pid_c and not img_url: url = std
    st.image(url, width=w)

def render_hif_stat(label, value, color):
    # Ny version: Farvestribe i bunden i stedet for siden
    return f"""
        <div style="
            background-color: #f8f9fa; 
            padding: 5px 10px; 
            border-radius: 6px; 
            border-bottom: 4px solid {color}; 
            min-width: 70px;
            text-align: center;
            margin: 0 4px;">
            <div style="font-size: 0.6rem; text-transform: uppercase; color: #666; font-weight: bold; line-height:1;">{label}</div>
            <div style="font-size: 1.1rem; font-weight: 800; color: #1a1a1a; line-height:1.2;">{value}</div>
        </div>
    """

def vis_side(df_spillere, d1, d2, career_df, d3):
    # CSS til at fjerne whitespace og tvinge elementer tættere
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0rem !important; }
            .stat-container { display: flex; justify-content: space-between; align-items: center; width: 100%; }
        </style>
    """, unsafe_allow_html=True)

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except: return

    billed_map = {rens_id(row['PLAYER_WYID']): row['IMAGEDATAURL'] for _, row in d3.iterrows()} if d3 is not None else {}
    navne_liste = sorted(df_s['Navn'].unique().tolist())

    # Selector
    c1, c2 = st.columns(2)
    s1_navn = c1.selectbox("P1", navne_liste, index=0, label_visibility="collapsed")
    s2_navn = c2.selectbox("P2", navne_liste, index=min(1, len(navne_liste)-1), label_visibility="collapsed")

    def hent_data(navn):
        match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if match.empty: return None
        n = match.iloc[0]
        pid = n['PID_CLEAN']
        
        stats = {"Kampe": 0, "Mål": 0, "Assist": 0, "Min": 0}
        if career_df is not None:
            c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & (career_df['SEASONNAME'].str.contains("2025/2026", na=False))]
            if not c_m.empty:
                stats = {"KAMPE": int(c_m.iloc[0].get('APPEARANCES', 0)), "MÅL": int(c_m.iloc[0].get('GOAL', 0)),
                         "ASSIST": int(c_m.iloc[0].get('ASSIST', 0)), "MIN": int(c_m.iloc[0].get('MINUTESPLAYED', 0))}

        return {
            "navn": navn, "pid": pid, "img": billed_map.get(pid), "stats": stats,
            "r": [n.get(k, 0.1) for k in ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']]
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)
    if not p1 or not p2: return

    # --- HOVED-LAYOUT: Alt på én linje ---
    # Vi bruger 5 kolonner: [Billede+Navn] [Stats P1] [Radar] [Stats P2] [Billede+Navn]
    col1, col2, col3, col4, col5 = st.columns([1.5, 2, 3, 2, 1.5])

    with col1:
        st.markdown(f"<h3 style='color:{HIF_RED}; margin:0;'>{p1['navn']}</h3>", unsafe_allow_html=True)
        vis_spiller_billede(p1["img"], p1["pid"])

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        # Samler alle 4 stats vandret via HTML flex
        stats_html = "".join([render_hif_stat(k, v, HIF_RED) for k, v in p1["stats"].items()])
        st.markdown(f"<div style='display:flex; flex-wrap:wrap; gap:5px;'>{stats_html}</div>", unsafe_allow_html=True)

    with col3:
        # Radar Chart
        labels = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_RED, opacity=0.4))
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_BLUE, opacity=0.4))
        fig.update_layout(
            polar=dict(gridshape='linear', radialaxis=dict(visible=False, range=[0, 6]), angularaxis=dict(linecolor="black", gridcolor="#eee")),
            height=280, margin=dict(l=30, r=30, t=10, b=10), showlegend=False, paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        # Samler alle 4 stats vandret til P2
        stats_html2 = "".join([render_hif_stat(k, v, HIF_BLUE) for k, v in p2["stats"].items()])
        st.markdown(f"<div style='display:flex; flex-wrap:wrap; gap:5px; justify-content:flex-end;'>{stats_html2}</div>", unsafe_allow_html=True)

    with col5:
        st.markdown(f"<h3 style='color:{HIF_BLUE}; text-align:right; margin:0;'>{p2['navn']}</h3>", unsafe_allow_html=True)
        cols_img = st.columns([1, 4]) # Trick til at højrestille billede
        with cols_img[1]: vis_spiller_billede(p2["img"], p2["pid"])

    st.divider()
    # Scout vurdering herunder...
