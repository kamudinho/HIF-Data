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
    pid_c = rens_id(pid)
    url = str(img_url).strip() if pd.notna(img_url) and str(img_url).lower() not in ["0", "0.0", "nan", "none", ""] else ""
    if url == "": return f"https://cdn5.wyscout.com/photos/players/public/{pid_c}.png"
    return url

def beregn_p90_stats(pid, adv_df):
    clean_pid = rens_id(pid)
    if adv_df is None or adv_df.empty: return None
    p_row = adv_df[adv_df['PLAYER_WYID'].apply(rens_id) == clean_pid]
    if p_row.empty: return None
    r = p_row.iloc[0]
    mins = float(r.get('MINUTESONFIELD', 0))
    if mins < 45: return {k: "-" for k in ["XG P90", "XA P90", "DRIBLINGER", "PASS %", "KEY PASSES", "INTERCEPTIONS", "DUELLER %"]}
    p90 = lambda val: round((float(r.get(val, 0)) / mins) * 90, 2)
    pct = lambda suc, tot: round((float(r.get(suc, 0)) / float(r.get(tot, 1))) * 100, 1) if float(r.get(tot, 0)) > 0 else 0.0
    return {
        "XG P90": p90('XGSHOT'), "XA P90": p90('XGASSIST'), "DRIBLINGER": p90('DRIBBLES'),
        "PASS %": pct('SUCCESSFULPASSES', 'PASSES'), "KEY PASSES": p90('KEYPASSES'),
        "INTERCEPTIONS": p90('INTERCEPTIONS'), "DUELLER %": pct('DUELSWON', 'DUELS')
    }

def vis_side(df_spillere, d1, d2, career_df, d3, advanced_stats_df):
    # --- CSS: SIDESTILLEDE BOKSE & DYNAMISK HØJDE ---
    st.markdown(f"""
        <style>
            .header-box {{ height: 55px; display: flex; flex-direction: column; justify-content: center; }}
            .player-title {{ margin: 0 !important; font-size: 1.4rem; font-weight: 800; line-height: 1; }}
            .player-sub {{ margin: 3px 0 0 0 !important; font-size: 0.9rem; color: gray; text-transform: uppercase; }}
            
            .metrics-box {{ height: 65px; margin-top: 10px; }}
            [data-testid="stMetricValue"] {{ font-size: 1.25rem !important; font-weight: 900 !important; }}
            
            .stat-row {{ 
                display: flex; justify-content: space-between; padding: 0 10px;
                border-bottom: 1px solid #f0f0f0; align-items: center; height: 42px;
            }}
            .stat-label {{ font-size: 0.8rem; color: #666; font-weight: bold; text-transform: uppercase; }}
            .stat-val {{ font-size: 1.1rem; font-weight: 800; }}

            /* Sidestillede bokse container */
            .notes-wrapper {{
                display: flex;
                flex-direction: column;
                gap: 12px;
                margin-top: 15px;
            }}
            .note-box {{
                padding: 14px;
                border-radius: 10px;
                border: 1px solid #eee;
                font-size: 1rem;
                line-height: 1.5;
                background: #ffffff;
                box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            }}
            .note-title {{ 
                font-size: 0.75rem; 
                font-weight: 900; 
                text-transform: uppercase; 
                color: #bbb; 
                margin-bottom: 6px; 
                letter-spacing: 1.2px; 
            }}
            .vurdering-hif {{ border-left: 5px solid {HIF_RED}; background: #fff8f8; }}
            .vurdering-mod {{ border-right: 5px solid {HIF_BLUE}; background: #f8fbff; }}
        </style>
    """, unsafe_allow_html=True)

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except: return

    navne_liste = sorted(df_s['Navn'].unique().tolist())
    c1, c2 = st.columns(2)
    s1_navn = c1.selectbox("P1", navne_liste, index=0, label_visibility="collapsed")
    s2_navn = c2.selectbox("P2", navne_liste, index=min(1, len(navne_liste)-1), label_visibility="collapsed")

    def hent_data(navn):
        match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if match.empty: return None
        n = match.iloc[0]
        pid = n['PID_CLEAN']
        
        pos, klub = "-", "Hvidovre IF"
        if df_spillere is not None and not df_spillere.empty:
            m = df_spillere[df_spillere['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                pos = map_position(m.iloc[0].get('ROLECODE3', ''))
                klub = m.iloc[0].get('TEAMNAME', 'Hvidovre IF')
        
        img_url = ""
        if d3 is not None and not d3.empty:
            img_m = d3[d3['PLAYER_WYID'].apply(rens_id) == pid]
            if not img_m.empty: img_url = img_m.iloc[0].get('IMAGEDATAURL', '')

        stats = {"K": 0, "M": 0, "A": 0, "MIN": 0}
        if career_df is not None and not career_df.empty:
            c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & (career_df['SEASONNAME'].str.contains("2025/2026", na=False))]
            if not c_m.empty:
                stats = {"K": int(c_m.iloc[0].get('APPEARANCES', 0)), "M": int(c_m.iloc[0].get('GOAL', 0)),
                         "A": int(c_m.iloc[0].get('ASSIST', 0)), "MIN": int(c_m.iloc[0].get('MINUTESONFIELD', 0))}
        
        labels = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
        return {
            "navn": navn, "pid": pid, "img": img_url, "pos": pos, "klub": klub, "stats": stats, 
            "adv": beregn_p90_stats(pid, advanced_stats_df),
            "r": [n.get(k, 0.1) for k in labels],
            "styrker": n.get('Styrker', '-'), "udvikling": n.get('Udvikling', '-'), "vurdering": n.get('Vurdering', '-'),
            "scout_scores": {k: n.get(k, 0) for k in labels}
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)
    if not p1 or not p2: return

    # --- HOVEDLAYOUT ---
    col_img1, col_data1, col_center, col_data2, col_img2 = st.columns([1, 3.2, 3.6, 3.2, 1], vertical_alignment="top")

    # SPILLER 1
    with col_img1:
        st.image(vis_spiller_billede(p1["img"], p1["pid"]), use_container_width=True)

    with col_data1:
        st.markdown(f"<div class='header-box'><p class='player-title' style='color:{HIF_RED};'>{p1['navn']}</p><p class='player-sub'>{p1['pos']} | {p1['klub']}</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='metrics-box'>", unsafe_allow_html=True)
        m_cols = st.columns(4)
        for i, (k, v) in enumerate(p1['stats'].items()): m_cols[i].metric(k, v)
        st.markdown("</div>", unsafe_allow_html=True)
        
        if p1['adv']:
            for k, v in p1['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-label'>{k}</span><span class='stat-val' style='color:{HIF_RED}'>{v}</span></div>", unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class='notes-wrapper'>
                <div class='note-box'><div class='note-title'>Styrker</div>{p1['styrker']}</div>
                <div class='note-box'><div class='note-title'>Udvikling</div>{p1['udvikling']}</div>
                <div class='note-box vurdering-hif'><div class='note-title' style='color:{HIF_RED};'>Scout Vurdering</div><b>{p1['vurdering']}</b></div>
            </div>
        """, unsafe_allow_html=True)

    # CENTER (RADAR)
    with col_center:
        labels = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_RED, opacity=0.35))
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_BLUE, opacity=0.35))
        fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 6])), height=320, margin=dict(l=40, r=40, t=10, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown("<div style='text-align:center; color:#999; font-weight:900; letter-spacing:2px; font-size:0.7rem;'>PROFIL SAMMENLIGNING</div>", unsafe_allow_html=True)

    # SPILLER 2
    with col_data2:
        st.markdown(f"<div class='header-box' style='text-align:right;'><p class='player-title' style='color:{HIF_BLUE};'>{p2['navn']}</p><p class='player-sub'>{p2['pos']} | {p2['klub']}</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='metrics-box blue-metric'>", unsafe_allow_html=True)
        m_cols = st.columns(4)
        for i, (k, v) in enumerate(p2['stats'].items()): m_cols[i].metric(k, v)
        st.markdown("</div>", unsafe_allow_html=True)
        
        if p2['adv']:
            for k, v in p2['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-val' style='color:{HIF_BLUE}'>{v}</span><span class='stat-label'>{k}</span></div>", unsafe_allow_html=True)

        st.markdown(f"""
            <div class='notes-wrapper' style='text-align:right;'>
                <div class='note-box'><div class='note-title'>Styrker</div>{p2['styrker']}</div>
                <div class='note-box'><div class='note-title'>Udvikling</div>{p2['udvikling']}</div>
                <div class='note-box vurdering-mod'><div class='note-title' style='color:{HIF_BLUE};'>Scout Vurdering</div><b>{p2['vurdering']}</b></div>
            </div>
        """, unsafe_allow_html=True)

    with col_img2:
        st.image(vis_spiller_billede(p2["img"], p2["pid"]), use_container_width=True)
