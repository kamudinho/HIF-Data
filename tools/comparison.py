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
    url = str(img_url).strip() if pd.notna(img_url) and str(img_url) not in ["0", "0.0", "nan", ""] else f"https://cdn5.wyscout.com/photos/players/public/{pid_c}.png"
    return url

def beregn_p90_stats(pid, adv_df):
    """Internt hjælpeværktøj til at trække de 10 vigtigste stats pr 90"""
    stats_out = {}
    clean_pid = rens_id(pid)
    
    if adv_df is None or adv_df.empty:
        return None
        
    # Find rækken for spilleren
    p_row = adv_df[adv_df['PLAYER_WYID'].apply(rens_id) == clean_pid]
    
    if p_row.empty:
        return None
        
    r = p_row.iloc[0]
    mins = float(r.get('MINUTESONFIELD', 0))
    
    # Beregnings-lambda (Sikrer mod division med 0 og for få minutter)
    p90 = lambda val: round((float(val) / mins) * 90, 2) if mins > 45 else 0.0
    pct = lambda suc, tot: round((float(suc) / float(tot)) * 100, 1) if float(tot) > 0 else 0.0

    return {
        "xG": p90(r.get('XGSHOT', 0)),
        "Driblinger": p90(r.get('DRIBBLES', 0)),
        "Driblinger %": pct(r.get('SUCCESSFULDRIBBLES', 0), r.get('DRIBBLES', 0)),
        "Prog. Løb": p90(r.get('PROGRESSIVERUN', 0)),
        "Prog. Pass": p90(r.get('PROGRESSIVEPASSES', 0)),
        "Pass %": pct(r.get('SUCCESSFULPASSES', 0), r.get('PASSES', 0)),
        "Key Passes": p90(r.get('KEYPASSES', 0)),
        "Erhvervninger": p90(r.get('RECOVERIES', 0)),
        "Interceptions": p90(r.get('INTERCEPTIONS', 0)),
        "Vundne Dueller %": pct(r.get('DUELSWON', 0), r.get('DUELS', 0))
    }

def vis_side(df_spillere, d1, d2, career_df, d3, advanced_stats_df):
    # CSS til styling af de nye rækker
    st.markdown(f"""
        <style>
            .stat-row {{ display: flex; justify-content: space-between; padding: 2px 0; border-bottom: 1px solid #eee; }}
            .stat-label {{ font-size: 0.65rem; color: #777; font-weight: bold; text-transform: uppercase; }}
            .stat-val {{ font-size: 0.8rem; font-weight: 800; }}
            [data-testid="stMetric"] {{ background-color: #f8f9fa; border-bottom: 3px solid {HIF_RED}; border-radius: 4px; padding: 5px !important; }}
            .blue-metric [data-testid="stMetric"] {{ border-bottom: 3px solid {HIF_BLUE} !important; }}
        </style>
    """, unsafe_allow_html=True)

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except: 
        st.error("Kunne ikke læse scouting_db.csv")
        return

    navne_liste = sorted(df_s['Navn'].unique().tolist())
    c1, c2 = st.columns(2)
    s1_navn = c1.selectbox("P1", navne_liste, index=0, label_visibility="collapsed")
    s2_navn = c2.selectbox("P2", navne_liste, index=min(1, len(navne_liste)-1), label_visibility="collapsed")

    def hent_data(navn):
        match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if match.empty: return None
        n = match.iloc[0]
        pid = n['PID_CLEAN']
        
        pos, klub = "-", "-"
        if df_spillere is not None and not df_spillere.empty:
            m = df_spillere[df_spillere['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                pos = map_position(m.iloc[0].get('ROLECODE3', ''))
                klub = m.iloc[0].get('TEAMNAME', 'Hvidovre IF')

        # Find billedet fra d3 (sql_players)
        img_url = ""
        if d3 is not None and not d3.empty:
            img_m = d3[d3['PLAYER_WYID'].apply(rens_id) == pid]
            if not img_m.empty: img_url = img_m.iloc[0].get('IMAGEDATAURL', '')

        stats = {"KAMPE": 0, "MÅL": 0, "ASS": 0, "MIN": 0}
        if career_df is not None and not career_df.empty:
            c_m = career_df[(career_df['PLAYER_WYID'].apply(rens_id) == pid) & (career_df['SEASONNAME'].str.contains("2025/2026", na=False))]
            if not c_m.empty:
                stats = {"KAMPE": int(c_m.iloc[0].get('APPEARANCES', 0)), "MÅL": int(c_m.iloc[0].get('GOAL', 0)),
                         "ASS": int(c_m.iloc[0].get('ASSIST', 0) if 'ASSIST' in c_m.columns else 0), "MIN": int(c_m.iloc[0].get('MINUTESONFIELD', 0))}
        
        return {
            "navn": navn, "pid": pid, "img": img_url, "pos": pos, "klub": klub, "stats": stats,
            "adv": beregn_p90_stats(pid, advanced_stats_df),
            "r": [n.get(k, 0.1) for k in ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']]
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)
    if not p1 or not p2: return

    col_img1, col_data1, col_radar, col_data2, col_img2 = st.columns([1, 2.8, 4.4, 2.8, 1])

    with col_img1:
        st.image(vis_spiller_billede(p1["img"], p1["pid"]), use_container_width=True)

    with col_data1:
        st.markdown(f"<h5 style='margin:0; color:{HIF_RED};'>{p1['navn']}</h5>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("K", p1['stats']['KAMPE'])
        m2.metric("M", p1['stats']['MÅL'])
        m3.metric("A", p1['stats']['ASS'])
        m4.metric("MIN", p1['stats']['MIN'])
        
        if p1['adv']:
            for k, v in p1['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-label'>{k}</span><span class='stat-val' style='color:{HIF_RED}'>{v}</span></div>", unsafe_allow_html=True)

    with col_radar:
        labels = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_RED, opacity=0.3))
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_BLUE, opacity=0.3))
        fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 6])), height=300, margin=dict(l=40, r=40, t=20, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_data2:
        st.markdown(f"<h5 style='margin:0; color:{HIF_BLUE}; text-align:right;'>{p2['navn']}</h5>", unsafe_allow_html=True)
        st.markdown('<div class="blue-metric">', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("K", p2['stats']['KAMPE'])
        m2.metric("M", p2['stats']['MÅL'])
        m3.metric("A", p2['stats']['ASS'])
        m4.metric("MIN", p2['stats']['MIN'])
        st.markdown('</div>', unsafe_allow_html=True)
        
        if p2['adv']:
            for k, v in p2['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-val' style='color:{HIF_BLUE}'>{v}</span><span class='stat-label'>{k}</span></div>", unsafe_allow_html=True)

    with col_img2:
        st.image(vis_spiller_billede(p2["img"], p2["pid"]), use_container_width=True)
