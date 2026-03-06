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
    # --- CSS: STØRRE SKRIFT & NYE BOKSE ---
    st.markdown(f"""
        <style>
            .header-box {{ height: 50px; display: flex; flex-direction: column; justify-content: center; }}
            .player-title {{ margin: 0 !important; font-size: 1.3rem; font-weight: 800; }}
            .player-sub {{ margin: 0 !important; font-size: 0.85rem; color: gray; text-transform: uppercase; }}
            
            .metrics-box {{ height: 60px; margin-bottom: 15px; }}
            [data-testid="stMetricValue"] {{ font-size: 1.1rem !important; font-weight: 800 !important; }}
            [data-testid="stMetricLabel"] {{ font-size: 0.7rem !important; }}
            
            .stat-row {{ 
                display: flex; justify-content: space-between; padding: 0 6px;
                border-bottom: 1px solid #eee; align-items: center; height: 38px;
            }}
            .stat-label {{ font-size: 0.75rem; color: #666; font-weight: bold; }}
            .stat-val {{ font-size: 1rem; font-weight: 800; }}

            /* Note-bokse styling */
            .note-box {{
                margin-top: 10px; padding: 10px; border-radius: 6px; border: 1px solid #eee;
                font-size: 0.85rem; line-height: 1.4; min-height: 60px;
            }}
            .note-title {{ font-size: 0.7rem; font-weight: bold; text-transform: uppercase; color: #999; margin-bottom: 4px; }}
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
        # Henter de nye tekstfelter fra scouting_db
        return {
            "navn": navn, "pid": n['PID_CLEAN'], "img": "", # Billede hentes via d3 i hovedloop
            "r": [n.get(k, 0.1) for k in ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']],
            "styrker": n.get('Styrker', 'Ingen data'),
            "udvikling": n.get('Udvikling', 'Ingen data'),
            "vurdering": n.get('Vurdering', 'Ingen data'),
            "scout_scores": {k: n.get(k, 0) for k in ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']}
        }

    # Dataopsamling (forenklet til demonstration af layout)
    p1_base = hent_data(s1_navn)
    p2_base = hent_data(s2_navn)
    
    # Her ville du normalt merge med career_df og advanced_stats_df som i dine tidligere scripts
    # For at holde koden fokuseret på dine layout-ønsker, bruger vi p1/p2 referencerne herunder:
    
    col_img1, col_data1, col_center, col_data2, col_img2 = st.columns([1, 3, 4, 3, 1], vertical_alignment="top")

    # SPILLER 1
    with col_img1:
        st.image(vis_spiller_billede("", p1_base["pid"]), use_container_width=True)

    with col_data1:
        st.markdown(f"<div class='header-box'><p class='player-title' style='color:{HIF_RED};'>{p1_base['navn']}</p><p class='player-sub'>Hvidovre IF</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='metrics-box'>", unsafe_allow_html=True)
        st.columns(4)[0].metric("K", "12") # Eksempelværdier
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Tabel
        st.markdown(f"<div class='stat-row'><span class='stat-label'>XG P90</span><span class='stat-val' style='color:{HIF_RED}'>0.42</span></div>", unsafe_allow_html=True)
        
        # NYE BOKSE
        st.markdown(f"<div class='note-box'><div class='note-title'>Styrker</div>{p1_base['styrker']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='note-box'><div class='note-title'>Udvikling</div>{p1_base['udvikling']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='note-box' style='background:#fff0f0;'><div class='note-title'>Vurdering</div>{p1_base['vurdering']}</div>", unsafe_allow_html=True)

    # CENTER
    with col_center:
        fig = go.Figure()
        # ... Radar logik ...
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("<div style='text-align:center; font-weight:bold; color:#777;'>DATATJEK</div>", unsafe_allow_html=True)

    # SPILLER 2
    with col_data2:
        st.markdown(f"<div class='header-box' style='text-align:right;'><p class='player-title' style='color:{HIF_BLUE};'>{p2_base['navn']}</p><p class='player-sub'>Modstander</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='metrics-box blue-metric'>", unsafe_allow_html=True)
        st.columns(4)[0].metric("K", "10")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Tabel
        st.markdown(f"<div class='stat-row'><span class='stat-val' style='color:{HIF_BLUE}'>0.38</span><span class='stat-label'>XG P90</span></div>", unsafe_allow_html=True)

        # NYE BOKSE
        st.markdown(f"<div class='note-box' style='text-align:right;'><div class='note-title'>Styrker</div>{p2_base['styrker']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='note-box' style='text-align:right;'><div class='note-title'>Udvikling</div>{p2_base['udvikling']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='note-box' style='background:#f0f4ff; text-align:right;'><div class='note-title'>Vurdering</div>{p2_base['vurdering']}</div>", unsafe_allow_html=True)

    with col_img2:
        st.image(vis_spiller_billede("", p2_base["pid"]), use_container_width=True)
