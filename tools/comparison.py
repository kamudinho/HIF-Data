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
    st.markdown(f"""
        <style>
            .player-card {{
                padding: 20px; border-radius: 12px; border: 1px solid #eee;
                background: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.03);
                margin-bottom: 15px;
            }}
            .card-hif {{ border-left: 10px solid {HIF_RED}; }}
            .card-mod {{ border-right: 10px solid {HIF_BLUE}; text-align: right; }}
            .player-title {{ margin: 0 !important; font-size: 1.6rem; font-weight: 900; line-height: 1.1; }}
            .player-sub {{ margin: 2px 0 12px 0 !important; font-size: 0.95rem; color: gray; text-transform: uppercase; font-weight: 600; }}
            .quick-stats {{ display: flex; gap: 15px; margin-bottom: 15px; border-top: 1px solid #f0f0f0; padding-top: 10px; }}
            .card-mod .quick-stats {{ justify-content: flex-end; }}
            .q-item {{ text-align: center; min-width: 40px; }}
            .q-label {{ font-size: 0.7rem; color: #999; font-weight: bold; text-transform: uppercase; display: block; }}
            .q-val {{ font-size: 1.1rem; font-weight: 800; color: #333; }}
            .stat-row {{ display: flex; justify-content: space-between; padding: 0 5px; border-bottom: 1px solid #f8f8f8; align-items: center; height: 38px; }}
            .stat-label {{ font-size: 0.8rem; color: #777; font-weight: bold; text-transform: uppercase; }}
            .stat-val {{ font-size: 1.1rem; font-weight: 800; }}
            .scouting-header {{ text-align: center; font-weight: 900; font-size: 0.9rem; color: #bbb; text-transform: uppercase; letter-spacing: 3px; margin-top: 35px; margin-bottom: 12px; }}
            .note-box {{ padding: 18px; border-radius: 12px; border: 1px solid #eee; font-size: 1.05rem; line-height: 1.6; background: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.02); margin-bottom: 15px; }}
            .note-hif {{ border-left: 8px solid {HIF_RED}; }}
            .note-mod {{ border-right: 8px solid {HIF_BLUE}; text-align: right; }}
            .center-analysis {{ margin-top: 15px; padding: 10px; background: #fcfcfc; border: 1px solid #eee; border-radius: 10px; text-align: center; font-size: 0.9rem; font-weight: 700; }}
        </style>
    """, unsafe_allow_html=True)

    try:
        df_s = pd.read_csv('data/scouting_db.csv')
        df_s['PID_CLEAN'] = df_s['PLAYER_WYID'].apply(rens_id)
    except:
        st.error("Kunne ikke indlæse scouting_db.csv")
        return

    navne_liste = sorted(df_s['Navn'].unique().tolist())
    c1, c2 = st.columns(2)
    s1_navn = c1.selectbox("P1", navne_liste, index=0, label_visibility="collapsed")
    s2_navn = c2.selectbox("P2", navne_liste, index=min(1, len(navne_liste)-1), label_visibility="collapsed")

    def hent_data(navn):
        match = df_s[df_s['Navn'] == navn].sort_values('Dato').iloc[-1:]
        if match.empty: return None
        n = match.iloc[0]
        pid = rens_id(n['PID_CLEAN'])
        
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
            c_m = career_df[career_df['PLAYER_WYID'].apply(rens_id) == pid]
            current_season = c_m[c_m['SEASONNAME'].str.contains("2025/2026", na=False, case=False)]
            
            target = current_season.iloc[0] if not current_season.empty else (c_m.iloc[0] if not c_m.empty else None)
            
            if target is not None:
                stats = {
                    "K": int(target.get('MATCHES', 0)),
                    "M": int(target.get('GOALS', 0)),
                    "A": int(target.get('ASSISTS', 0)),
                    "MIN": int(target.get('MINUTES', 0))
                }
        
        lbls = ['Aggresivitet', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Fart', 'Attitude', 'Lederegenskaber', 'Udholdenhed']
        return {
            "navn": navn, "pid": pid, "img": img_url, "pos": pos, "klub": klub, "stats": stats, 
            "adv": beregn_p90_stats(pid, advanced_stats_df),
            "r": [n.get(k, 0.1) for k in lbls],
            "styrker": n.get('Styrker', '-'), "udvikling": n.get('Udvikling', '-'), "vurdering": n.get('Vurdering', '-'),
            "scout_scores": {k: n.get(k, 0) for k in lbls}
        }

    p1 = hent_data(s1_navn)
    p2 = hent_data(s2_navn)
    if not p1 or not p2: return

    # --- TOP LAYOUT: [SPILLER VENSTRE] [RADAR] [SPILLER HØJRE] ---
    col_left, col_center, col_right = st.columns([4.2, 3.6, 4.2])

    with col_left:
        st.markdown(f"""<div class='player-card card-hif'>
            <div style='display: flex; gap: 15px; align-items: start;'>
                <img src='{vis_spiller_billede(p1["img"], p1["pid"])}' style='width: 90px; border-radius: 8px;'>
                <div style='flex-grow: 1;'>
                    <p class='player-title' style='color:{HIF_RED};'>{p1['navn']}</p>
                    <p class='player-sub'>{p1['pos']} | {p1['klub']}</p>
                    <div class='quick-stats'>
                        <div class='q-item'><span class='q-label'>K</span><span class='q-val'>{p1['stats']['K']}</span></div>
                        <div class='q-item'><span class='q-label'>M</span><span class='q-val'>{p1['stats']['M']}</span></div>
                        <div class='q-item'><span class='q-label'>A</span><span class='q-val'>{p1['stats']['A']}</span></div>
                        <div class='q-item'><span class='q-label'>MIN</span><span class='q-val'>{p1['stats']['MIN']}</span></div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        if p1['adv']:
            for k, v in p1['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-label'>{k}</span><span class='stat-val' style='color:{HIF_RED}'>{v}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_center:
        labels = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_RED, opacity=0.4))
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_BLUE, opacity=0.4))
        fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 6])), height=330, margin=dict(l=40, r=40, t=10, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        diffs = {k: p1['scout_scores'][k] - p2['scout_scores'][k] for k in labels}
        max_p1 = max(diffs, key=diffs.get); max_p2 = min(diffs, key=diffs.get)
        st.markdown(f"<div class='center-analysis'>DATATJEK: {p1['navn']} (+{max_p1.lower()}) vs {p2['navn']} (+{max_p2.lower()})</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown(f"""<div class='player-card card-mod'>
            <div style='display: flex; gap: 15px; align-items: start; flex-direction: row-reverse;'>
                <img src='{vis_spiller_billede(p2["img"], p2["pid"])}' style='width: 90px; border-radius: 8px;'>
                <div style='flex-grow: 1;'>
                    <p class='player-title' style='color:{HIF_BLUE};'>{p2['navn']}</p>
                    <p class='player-sub'>{p2['pos']} | {p2['klub']}</p>
                    <div class='quick-stats'>
                        <div class='q-item'><span class='q-label'>MIN</span><span class='q-val'>{p2['stats']['MIN']}</span></div>
                        <div class='q-item'><span class='q-label'>A</span><span class='q-val'>{p2['stats']['A']}</span></div>
                        <div class='q-item'><span class='q-label'>M</span><span class='q-val'>{p2['stats']['M']}</span></div>
                        <div class='q-item'><span class='q-label'>K</span><span class='q-val'>{p2['stats']['K']}</span></div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        if p2['adv']:
            for k, v in p2['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-val' style='color:{HIF_BLUE}'>{v}</span><span class='stat-label'>{k}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin: 20px 0 10px 0; border: 0; border-top: 2px solid #eee;'>", unsafe_allow_html=True)
    def scouting_row(label, text1, text2):
        st.markdown(f"<div class='scouting-header'>{label}</div>", unsafe_allow_html=True)
        s_col1, s_col2 = st.columns(2)
        s_col1.markdown(f"<div class='note-box note-hif'>{text1}</div>", unsafe_allow_html=True)
        s_col2.markdown(f"<div class='note-box note-mod'>{text2}</div>", unsafe_allow_html=True)

    scouting_row("Styrker", p1["styrker"], p2["styrker"])
    scouting_row("Udviklingspotentiale", p1["udvikling"], p2["udvikling"])
    scouting_row("Scout Vurdering", f"<b>{p1['vurdering']}</b>", f"<b>{p2['vurdering']}</b>")
