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
    if not pid_c and not img_url: url = std
    return url

def get_hif_stat_html(label, value, color):
    # Denne returnerer nu en ren HTML-streng
    return f"""
        <div style="background-color: #f8f9fa; padding: 4px 6px; border-radius: 4px; 
                    border-bottom: 3px solid {color}; min-width: 55px; text-align: center; margin: 2px;">
            <div style="font-size: 0.5rem; text-transform: uppercase; color: #666; font-weight: bold; line-height:1;">{label}</div>
            <div style="font-size: 0.9rem; font-weight: 800; color: #1a1a1a; line-height:1.1;">{value}</div>
        </div>
    """

def vis_side(df_spillere, d1, d2, career_df, d3):
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; }
            [data-testid="stVerticalBlock"] { gap: 0rem !important; }
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
        
        pos_str, klub_str = "Ukendt", "Ukendt"
        if df_spillere is not None:
            m = df_spillere[df_spillere['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                pos_str = map_position(m.iloc[0].get('ROLECODE3', ''))
                klub_str = m.iloc[0].get('TEAMNAME', 'Hvidovre IF')

        stats = {"Kampe": 0, "Mål": 0, "Assist": 0, "Min": 0}
        if career_df is not None:
            c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & (career_df['SEASONNAME'].str.contains("2025/2026", na=False))]
            if not c_m.empty:
                stats = {"KMP": int(c_m.iloc[0].get('APPEARANCES', 0)), "MÅL": int(c_m.iloc[0].get('GOAL', 0)),
                         "AST": int(c_m.iloc[0].get('ASSIST', 0)), "MIN": int(c_m.iloc[0].get('MINUTESPLAYED', 0))}
        
        return {"navn": navn, "pid": pid, "img": billed_map.get(pid), "pos": pos_str, "klub": klub_str, "stats": stats,
                "r": [n.get(k, 0.1) for k in ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']]}

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)
    if not p1 or not p2: return

    # --- SELVE LAYOUTET ---
    # Vi bruger st.columns for at dele skærmen op
    col_img1, col_info1, col_radar, col_info2, col_img2 = st.columns([1, 2, 4, 2, 1])

    with col_img1:
        st.image(vis_spiller_billede(p1["img"], p1["pid"]), use_container_width=True)

    with col_info1:
        st.markdown(f"""
            <div style="text-align: left;">
                <h4 style="margin:0; color:{HIF_RED}; font-size:1.1rem;">{p1['navn']}</h4>
                <p style="margin:0; font-size:0.75rem; color:gray;">{p1['pos']}<br>{p1['klub']}</p>
                <div style="display: flex; flex-wrap: wrap; margin-top: 8px;">
                    {"".join([get_hif_stat_html(k, v, HIF_RED) for k, v in p1['stats'].items()])}
                </div>
            </div>
        """, unsafe_allow_html=True)

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

    with col_info2:
        st.markdown(f"""
            <div style="text-align: right;">
                <h4 style="margin:0; color:{HIF_BLUE}; font-size:1.1rem;">{p2['navn']}</h4>
                <p style="margin:0; font-size:0.75rem; color:gray; text-align:right;">{p2['pos']}<br>{p2['klub']}</p>
                <div style="display: flex; flex-wrap: wrap; justify-content: flex-end; margin-top: 8px;">
                    {"".join([get_hif_stat_html(k, v, HIF_BLUE) for k, v in p2['stats'].items()])}
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_img2:
        st.image(vis_spiller_billede(p2["img"], p2["pid"]), use_container_width=True)

    st.markdown("---")
