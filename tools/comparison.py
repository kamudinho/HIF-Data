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
    """Beregner P90 stats baseret på de rå tal fra SQL queryen"""
    clean_pid = rens_id(pid)
    if adv_df is None or adv_df.empty: return None
    
    p_row = adv_df[adv_df['PLAYER_WYID'].apply(rens_id) == clean_pid]
    if p_row.empty: return None
    
    r = p_row.iloc[0]
    mins = float(r.get('MINUTESONFIELD', 0))
    
    if mins < 45:
        return {k: "-" for k in ["xG P90", "xA P90", "Driblinger", "Driblinger %", "Prog. Løb", "Prog. Pass", "Pass %", "Key Passes", "Interceptions", "Dueller %", "Touch i felt"]}
        
    p90 = lambda val: round((float(r.get(val, 0)) / mins) * 90, 2)
    pct = lambda suc, tot: round((float(r.get(suc, 0)) / float(r.get(tot, 1))) * 100, 1) if float(r.get(tot, 0)) > 0 else 0.0

    return {
        "xG P90": p90('XGSHOT'),
        "xA P90": p90('XGASSIST'),
        "Driblinger": p90('DRIBBLES'),
        "Driblinger %": pct('SUCCESSFULDRIBBLES', 'DRIBBLES'),
        "Prog. Løb": p90('PROGRESSIVERUN'),
        "Prog. Pass": p90('PROGRESSIVEPASSES'),
        "Pass %": pct('SUCCESSFULPASSES', 'PASSES'),
        "Key Passes": p90('KEYPASSES'),
        "Interceptions": p90('INTERCEPTIONS'),
        "Dueller %": pct('DUELSWON', 'DUELS'),
        "Touch i felt": p90('TOUCHINBOX')
    }

def vis_side(df_spillere, d1, d2, career_df, d3, advanced_stats_df):
    # CSS til styling
    st.markdown(f"""
        <style>
            .stat-row {{ display: flex; justify-content: space-between; padding: 2px 0; border-bottom: 1px solid #eee; }}
            .stat-label {{ font-size: 0.65rem; color: #777; font-weight: bold; text-transform: uppercase; }}
            .stat-val {{ font-size: 0.8rem; font-weight: 800; }}
            [data-testid="stMetric"] {{ background-color: #f8f9fa; border-bottom: 3px solid {HIF_RED}; border-radius: 4px; padding: 5px !important; }}
            .blue-metric [data-testid="stMetric"] {{ border-bottom: 3px solid {HIF_BLUE} !important; }}
            .diff-box {{ background-color: #f1f1f1; padding: 10px; border-radius: 5px; margin-top: 10px; font-size: 0.85rem; border-left: 5px solid {HIF_RED}; }}
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
        
        pos, klub = "Ukendt", "Ukendt"
        if df_spillere is not None and not df_spillere.empty:
            m = df_spillere[df_spillere['PLAYER_WYID'].apply(rens_id) == pid]
            if not m.empty:
                pos = map_position(m.iloc[0].get('ROLECODE3', ''))
                klub = m.iloc[0].get('TEAMNAME', 'Hvidovre IF')

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
        
        scouting_labels = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
        return {
            "navn": navn, "pid": pid, "img": img_url, "pos": pos, "klub": klub, "stats": stats,
            "adv": beregn_p90_stats(pid, advanced_stats_df),
            "r": [n.get(k, 0.1) for k in scouting_labels],
            "scout_data": {k: n.get(k, 0) for k in scouting_labels}
        }

    p1, p2 = hent_data(s1_navn), hent_data(s2_navn)
    if not p1 or not p2: return

    # --- TOP SEKTION ---
    col_img1, col_data1, col_radar, col_data2, col_img2 = st.columns([1, 2.8, 4.4, 2.8, 1])

    with col_img1:
        st.image(vis_spiller_billede(p1["img"], p1["pid"]), use_container_width=True)

    with col_data1:
        st.markdown(f"<h5 style='margin:0; color:{HIF_RED};'>{p1['navn']}</h5>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0; font-size:0.75rem; color:gray;'>{p1['klub']} | {p1['pos']}</p>", unsafe_allow_html=True)
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
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', name=p1['navn'], line_color=HIF_RED, opacity=0.4))
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', name=p2['navn'], line_color=HIF_BLUE, opacity=0.4))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6], tickfont=dict(size=8))), height=320, margin=dict(l=40, r=40, t=30, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_data2:
        st.markdown(f"<h5 style='margin:0; color:{HIF_BLUE}; text-align:right;'>{p2['navn']}</h5>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0; font-size:0.75rem; color:gray; text-align:right;'>{p2['pos']} | {p2['klub']}</p>", unsafe_allow_html=True)
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

    # --- OPSUMMERING AF FORSKELLE ---
    st.markdown("---")
    st.subheader("Data-opsummering: Hvor adskiller de sig?")
    
    # Logik til at finde største forskelle i scouting karakterer
    diffs = []
    for k in labels:
        d = p1['scout_data'][k] - p2['scout_data'][k]
        diffs.append((k, d))
    
    # Sorter efter absolut forskel
    diffs_sorted = sorted(diffs, key=lambda x: abs(x[1]), reverse=True)
    
    col_sum1, col_sum2 = st.columns(2)
    
    with col_sum1:
        st.markdown(f"**Styrker: {p1['navn']}**")
        p1_top = [f"{k} (+{round(d,1)})" for k, d in diffs_sorted if d > 0.5][:3]
        if p1_top:
            for s in p1_top: st.write(f"✅ {s}")
        else:
            st.write("Ingen markante forskelle fundet.")

    with col_sum2:
        st.markdown(f"**Styrker: {p2['navn']}**")
        p2_top = [f"{k} (+{round(abs(d),1)})" for k, d in diffs_sorted if d < -0.5][:3]
        if p2_top:
            for s in p2_top: st.write(f"✅ {s}")
        else:
            st.write("Ingen markante forskelle fundet.")
