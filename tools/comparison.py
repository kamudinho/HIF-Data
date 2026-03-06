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
    clean_pid = rens_id(pid)
    if adv_df is None or adv_df.empty: return None
    p_row = adv_df[adv_df['PLAYER_WYID'].apply(rens_id) == clean_pid]
    if p_row.empty: return None
    r = p_row.iloc[0]
    mins = float(r.get('MINUTESONFIELD', 0))
    if mins < 45: return {k: "-" for k in ["xG P90", "xA P90", "Driblinger", "Pass %", "Key Passes", "Interceptions", "Dueller %"]}
    
    p90 = lambda val: round((float(r.get(val, 0)) / mins) * 90, 2)
    pct = lambda suc, tot: round((float(r.get(suc, 0)) / float(r.get(tot, 1))) * 100, 1) if float(r.get(tot, 0)) > 0 else 0.0

    return {
        "xG P90": p90('XGSHOT'),
        "xA P90": p90('XGASSIST'),
        "Driblinger": p90('DRIBBLES'),
        "Pass %": pct('SUCCESSFULPASSES', 'PASSES'),
        "Key Passes": p90('KEYPASSES'),
        "Interceptions": p90('INTERCEPTIONS'),
        "Dueller %": pct('DUELSWON', 'DUELS')
    }

def vis_side(df_spillere, d1, d2, career_df, d3, advanced_stats_df):
    st.markdown(f"""
        <style>
            .stat-row {{ display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid #eee; align-items: center; }}
            .stat-label {{ font-size: 0.65rem; color: #777; font-weight: bold; text-transform: uppercase; }}
            .stat-val {{ font-size: 0.85rem; font-weight: 800; }}
            [data-testid="stMetric"] {{ background-color: #f8f9fa; border-bottom: 3px solid {HIF_RED}; border-radius: 4px; padding: 5px !important; }}
            .blue-metric [data-testid="stMetric"] {{ border-bottom: 3px solid {HIF_BLUE} !important; }}
            .summary-text {{ font-size: 0.85rem; line-height: 1.4; color: #333; padding: 10px; background: #fdfdfd; border: 1px solid #eee; border-radius: 8px; text-align: center; }}
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
        pos, klub = "-", "-"
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
        return {"navn": navn, "pid": pid, "img": img_url, "pos": pos, "klub": klub, "stats": stats, 
                "adv": beregn_p90_stats(pid, advanced_stats_df), "r": [n.get(k, 0.1) for k in labels],
                "scout_scores": {k: n.get(k, 0) for k in labels}}

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)
    if not p1 or not p2: return

    # --- Layout Struktur ---
    col_img1, col_data1, col_center, col_data2, col_img2 = st.columns([1, 2.5, 4, 2.5, 1])

    with col_img1:
        st.image(vis_spiller_billede(p1["img"], p1["pid"]), use_container_width=True)

    with col_data1:
        st.markdown(f"<h5 style='margin:0; color:{HIF_RED};'>{p1['navn']}</h5>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0 0 10px 0; font-size:0.7rem; color:gray;'>{p1['klub']} | {p1['pos']}</p>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("K", p1['stats']['K'])
        m2.metric("M", p1['stats']['M'])
        m3.metric("A", p1['stats']['A'])
        m4.metric("MIN", p1['stats']['MIN'])
        if p1['adv']:
            for k, v in p1['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-label'>{k}</span><span class='stat-val' style='color:{HIF_RED}'>{v}</span></div>", unsafe_allow_html=True)

    with col_center:
        # Radar Chart
        labels = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_RED, opacity=0.3))
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_BLUE, opacity=0.3))
        fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 6])), height=280, margin=dict(l=40, r=40, t=20, b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        # Dynamisk Tekstvurdering (Mellem tabellerne)
        diffs = {k: p1['scout_scores'][k] - p2['scout_scores'][k] for k in labels}
        max_p1 = max(diffs, key=diffs.get)
        max_p2 = min(diffs, key=diffs.get)
        
        st.markdown(f"""
            <div class='summary-text'>
                <b>Sammenligning:</b><br>
                {p1['navn']} er markant stærkere på <b>{max_p1.lower()}</b>, 
                mens {p2['navn']} har sin største fordel i <b>{max_p2.lower()}</b>.
            </div>
        """, unsafe_allow_html=True)

    with col_data2:
        st.markdown(f"<h5 style='margin:0; color:{HIF_BLUE}; text-align:right;'>{p2['navn']}</h5>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0 0 10px 0; font-size:0.7rem; color:gray; text-align:right;'>{p2['pos']} | {p2['klub']}</p>", unsafe_allow_html=True)
        st.markdown('<div class="blue-metric">', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("K", p2['stats']['K'])
        m2.metric("M", p2['stats']['M'])
        m3.metric("A", p2['stats']['A'])
        m4.metric("MIN", p2['stats']['MIN'])
        st.markdown('</div>', unsafe_allow_html=True)
        if p2['adv']:
            for k, v in p2['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-val' style='color:{HIF_BLUE}'>{v}</span><span class='stat-label'>{k}</span></div>", unsafe_allow_html=True)

    with col_img2:
        st.image(vis_spiller_billede(p2["img"], p2["pid"]), use_container_width=True)
