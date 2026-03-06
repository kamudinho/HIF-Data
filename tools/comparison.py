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

def beregn_stats_90(pid, adv_df):
    """Henter totaler og omregner til pr. 90 minutter for en spiller."""
    # Standard værdier hvis ingen data findes
    default_stats = {
        "xG": 0.0, "xG Assist": 0.0, "Driblinger": 0.0, "Progressive løb": 0.0,
        "Interceptions": 0.0, "Vundne dueller %": 0.0, "Key Passes": 0.0,
        "Touch i feltet": 0.0, "Erhvervninger": 0.0, "Afleveringer %": 0.0
    }
    
    if adv_df is None or adv_df.empty:
        return default_stats
    
    # Match på spiller
    p_stats = adv_df[adv_df['PLAYER_WYID'].apply(rens_id) == rens_id(pid)]
    if p_stats.empty:
        return default_stats
    
    row = p_stats.iloc[0]
    mins = float(row.get('MINUTESONFIELD', 0))
    
    # Hjælpefunktion til 90-minutters beregning
    def p90(val):
        if mins < 45: return 0.0 # Undgå vilde statistikker for spillere med få minutter
        return round((float(val) / mins) * 90, 2)

    # Beregning af procenter
    def pct(success, total):
        if float(total) == 0: return 0.0
        return round((float(success) / float(total)) * 100, 1)

    return {
        "xG": p90(row.get('XGSHOT', 0)),
        "xG Assist": p90(row.get('XGASSIST', 0)),
        "Driblinger": p90(row.get('DRIBBLES', 0)),
        "Progressive løb": p90(row.get('PROGRESSIVERUN', 0)),
        "Interceptions": p90(row.get('INTERCEPTIONS', 0)),
        "Vundne dueller %": pct(row.get('DUELSWON', 0), row.get('DUELS', 0)),
        "Key Passes": p90(row.get('KEYPASSES', 0)),
        "Touch i feltet": p90(row.get('TOUCHINBOX', 0)),
        "Erhvervninger": p90(row.get('RECOVERIES', 0)),
        "Afleveringer %": pct(row.get('SUCCESSFULPASSES', 0), row.get('PASSES', 0))
    }

def vis_side(df_spillere, d1, d2, career_df, d3, advanced_stats_df):
    # ... (Din eksisterende CSS herover er bibeholdt) ...
    st.markdown(f"""
        <style>
            .stat-row {{
                display: flex;
                justify-content: space-between;
                padding: 4px 0;
                border-bottom: 1px solid #eee;
                font-size: 0.8rem;
            }}
            .stat-label {{ color: #666; font-weight: bold; text-transform: uppercase; font-size: 0.7rem; }}
            .stat-val-red {{ color: {HIF_RED}; font-weight: 800; }}
            .stat-val-blue {{ color: {HIF_BLUE}; font-weight: 800; }}
        </style>
    """, unsafe_allow_html=True)

    # ... (Hentning af p1 og p2 via hent_data eksisterer her) ...
    # Vi antager p1 og p2 er hentet korrekt som i din kode

    # HENT AVANCEREDE STATS
    p1_adv = beregn_stats_90(p1['pid'], advanced_stats_df)
    p2_adv = beregn_stats_90(p2['pid'], advanced_stats_df)

    # Layout: Billede - Data - Radar - Data - Billede
    col_img1, col_data1, col_radar, col_data2, col_img2 = st.columns([1, 2.8, 4.4, 2.8, 1])

    with col_img1:
        st.image(vis_spiller_billede(p1["img"], p1["pid"]), use_container_width=True)
    
    with col_data1:
        st.markdown(f"<h5 style='margin:0; color:{HIF_RED};'>{p1['navn']}</h5>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0; font-size:0.75rem;'>{p1['pos']}</p>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("KAMPE", p1['stats']['KAMPE'])
        m2.metric("MÅL", p1['stats']['MÅL'])
        m3.metric("ASS", p1['stats']['ASS'])
        m4.metric("MIN", p1['stats']['MIN'])
        
        # Avancerede stats for Spiller 1
        st.write("")
        for label, val in p1_adv.items():
            st.markdown(f"<div class='stat-row'><span class='stat-label'>{label}</span><span class='stat-val-red'>{val}</span></div>", unsafe_allow_html=True)

    with col_radar:
        # (Din eksisterende Plotly Radar kode her)
        labels = ['Fart', 'Teknik', 'Beslutsomhed', 'Spilintelligens', 'Aggresivitet', 'Lederegenskaber', 'Attitude', 'Udholdenhed']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', name=p1['navn'], line_color=HIF_RED))
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', name=p2['navn'], line_color=HIF_BLUE))
        fig.update_layout(height=350, margin=dict(l=40, r=40, t=20, b=20), polar=dict(radialaxis=dict(visible=False, range=[0, 6])), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_data2:
        st.markdown(f"<h5 style='margin:0; color:{HIF_BLUE}; text-align:right;'>{p2['navn']}</h5>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:right; margin:0; font-size:0.75rem;'>{p2['pos']}</p>", unsafe_allow_html=True)
        st.markdown('<div class="blue-metric">', unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("KAMPE", p2['stats']['KAMPE'])
        m2.metric("MÅL", p2['stats']['MÅL'])
        m3.metric("ASS", p2['stats']['ASS'])
        m4.metric("MIN", p2['stats']['MIN'])
        st.markdown('</div>')
        
        # Avancerede stats for Spiller 2
        st.write("")
        for label, val in p2_adv.items():
            st.markdown(f"<div class='stat-row'><span class='stat-val-blue'>{val}</span><span class='stat-label'>{label}</span></div>", unsafe_allow_html=True)

    with col_img2:
        st.image(vis_spiller_billede(p2["img"], p2["pid"]), use_container_width=True)
