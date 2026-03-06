import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# HIF Identitet farver
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

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

def vis_spiller_billede(img_url, pid, w=85):
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    pid_c = rens_id(pid)
    url = str(img_url).strip() if pd.notna(img_url) and str(img_url) not in ["0", "0.0", "nan", ""] else f"https://cdn5.wyscout.com/photos/players/public/{pid_c}.png"
    if not pid_c and not img_url: url = std
    st.image(url, width=w)

def render_hif_stat(label, value, align="left"):
    # Genbruger dit CSS-design fra skud-siden
    border_side = "left" if align == "left" else "right"
    st.markdown(f"""
        <div style="
            background-color: #f8f9fa; 
            padding: 10px 15px; 
            border-radius: 8px; 
            border-{border_side}: 5px solid {HIF_RED}; 
            margin-bottom: 8px;
            text-align: {align};">
            <div style="font-size: 0.7rem; text-transform: uppercase; color: #666; font-weight: bold;">{label}</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: #1a1a1a;">{value}</div>
        </div>
    """, unsafe_allow_html=True)

# --- HOVEDFUNKTION ---
def vis_side(df_spillere, d1, d2, career_df, d3):
    # CSS til at fjerne whitespace og stramme layoutet op
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0.2rem !important; }
            [data-testid="column"] { gap: 0.5rem !important; }
            h2 { margin-top: -10px !important; margin-bottom: 5px !important; }
        </style>
    """, unsafe_allow_html=True)

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except:
        st.error("Kunne ikke indlæse scouting_db.csv")
        return

    billed_map = {rens_id(row['PLAYER_WYID']): row['IMAGEDATAURL'] for _, row in d3.iterrows()} if d3 is not None else {}
    navne_liste = sorted(df_s['Navn'].unique().tolist())

    # 1. Spiller vælgere
    c_sel1, c_sel2 = st.columns(2)
    s1_navn = c_sel1.selectbox("Vælg Spiller 1", navne_liste, index=0, label_visibility="collapsed")
    s2_navn = c_sel2.selectbox("Vælg Spiller 2", navne_liste, index=min(1, len(navne_liste)-1), label_visibility="collapsed")

    def hent_data(navn):
        s_match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if s_match.empty: return None
        n = s_match.iloc[0]
        pid = n['PID_CLEAN']
        
        pos_str, klub_str = "Ukendt", "Ukendt"
        if df_spillere is not None and not df_spillere.empty:
            m = df_spillere[df_spillere['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                pos_str = map_position(m.iloc[0].get('ROLECODE3', ''))
                klub_str = m.iloc[0].get('TEAMNAME', 'Hvidovre IF')

        stats = {"Kampe": 0, "Mål": 0, "Assist": 0, "Min": 0}
        if career_df is not None:
            c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & (career_df['SEASONNAME'].str.contains("2025/2026", na=False))]
            if not c_m.empty:
                stats = {"Kampe": int(c_m.iloc[0].get('APPEARANCES', 0)), "Mål": int(c_m.iloc[0].get('GOAL', 0)),
                         "Assist": int(c_m.iloc[0].get('ASSIST', 0)), "Min": int(c_m.iloc[0].get('MINUTESPLAYED', 0))}

        return {
            "navn": navn, "pid": pid, "img": billed_map.get(pid), "pos": pos_str, "klub": klub_str, "stats": stats,
            "vurdering": n.get('Vurdering', '-'),
            "r": [n.get(k, 0.1) for k in ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']]
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)
    if not p1 or not p2: return

    st.markdown("<hr style='margin:10px 0; border:0; border-top:1px solid #eee;'>", unsafe_allow_html=True)

    # 2. Header (Navn, Billede, Klub)
    h1, h2 = st.columns(2)
    with h1:
        st.markdown(f"<h2 style='color:{HIF_RED};'>{p1['navn']}</h2>", unsafe_allow_html=True)
        ci1, ct1 = st.columns([1, 3])
        with ci1: vis_spiller_billede(p1["img"], p1["pid"])
        with ct1: st.markdown(f"<div style='color:gray; font-size:0.9rem;'>{p1['pos']}<br>{p1['klub']}</div>", unsafe_allow_html=True)
    
    with h2:
        st.markdown(f"<h2 style='color:#0056a3; text-align:right;'>{p2['navn']}</h2>", unsafe_allow_html=True)
        ct2, ci2 = st.columns([3, 1])
        with ci2: vis_spiller_billede(p2["img"], p2["pid"])
        with ct2: st.markdown(f"<div style='color:gray; font-size:0.9rem; text-align:right;'>{p2['pos']}<br>{p2['klub']}</div>", unsafe_allow_html=True)

    # 3. Center sektion (HIF StatBoxes - Radar - HIF StatBoxes)
    st.markdown("<div style='margin-top: -20px;'>", unsafe_allow_html=True)
    col_left, col_mid, col_right = st.columns([1.5, 4, 1.5])

    with col_left:
        st.markdown("<br><br>", unsafe_allow_html=True) # Justering
        for k, v in p1["stats"].items():
            render_hif_stat(k, v, align="left")

    with col_right:
        st.markdown("<br><br>", unsafe_allow_html=True)
        for k, v in p2["stats"].items():
            render_hif_stat(k, v, align="right")

    with col_mid:
        labels = ['Fart', 'Teknik', 'Beslut', 'Intel', 'Aggr', 'Leder', 'Att', 'Udh']
        fig = go.Figure()
        # Spiller 1 (HIF Rød)
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', name=p1['navn'], line_color=HIF_RED, opacity=0.4))
        # Spiller 2 (Blå)
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', name=p2['navn'], line_color='#0056a3', opacity=0.4))

        fig.update_layout(
            polar=dict(
                gridshape='linear', # Ottekanten
                radialaxis=dict(visible=True, range=[0, 6], gridcolor="#eee", linecolor="#444", tickfont=dict(size=8)),
                angularaxis=dict(gridcolor="#eee", linecolor="#000", linewidth=1.5)
            ),
            height=450, margin=dict(l=40, r=40, t=10, b=10), showlegend=False, paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

    # 4. Scout vurdering
    v1, v2 = st.columns(2)
    v1.markdown(f"<div style='background:#f8f9fa; padding:15px; border-left:5px solid {HIF_RED}; border-radius:4px;'><b>Vurdering {p1['navn']}:</b><br><small>{p1['vurdering']}</small></div>", unsafe_allow_html=True)
    v2.markdown(f"<div style='background:#f8f9fa; padding:15px; border-right:5px solid #0056a3; border-radius:4px; text-align:right;'><b>Vurdering {p2['navn']}:</b><br><small>{p2['vurdering']}</small></div>", unsafe_allow_html=True)
