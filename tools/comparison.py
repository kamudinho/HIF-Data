import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# HIF Identitet
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'

# --- (Hjælpefunktioner rens_id, map_position, vis_spiller_billede, beregn_p90_stats forbliver uændrede) ---

def vis_side(df_spillere, d1, d2, career_df, d3, advanced_stats_df):
    st.markdown(f"""
        <style>
            /* Overordnet container for stats rækker */
            .stats-container {{
                display: flex;
                flex-direction: column;
                gap: 4px;
                margin-top: 15px;
            }}
            .stat-row {{
                display: flex;
                justify-content: space-between;
                padding: 5px 0;
                border-bottom: 1px solid #f0f0f0;
                align-items: center;
                min-height: 30px;
            }}
            .stat-label {{
                font-size: 0.65rem;
                color: #666;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                flex: 1;
            }}
            .stat-val {{
                font-size: 0.9rem;
                font-weight: 800;
                min-width: 45px;
            }}
            /* Justering af metrics */
            [data-testid="stMetric"] {{
                background-color: #f8f9fa;
                border-bottom: 3px solid {HIF_RED};
                border-radius: 4px;
                padding: 8px !important;
            }}
            .blue-metric [data-testid="stMetric"] {{
                border-bottom: 3px solid {HIF_BLUE} !important;
            }}
            /* Sammenligningsboks */
            .summary-box {{
                background-color: #ffffff;
                padding: 15px;
                border-radius: 10px;
                border: 1px solid #eee;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                margin-top: 20px;
                text-align: center;
                font-size: 0.85rem;
            }}
        </style>
    """, unsafe_allow_html=True)

    # ... (Hent data logik p1, p2) ...

    # --- Layout Struktur med justerede afstande ---
    # Vi bruger [1, 2.5, 0.5, 3, 0.5, 2.5, 1] for at skabe luft (gap) omkring radaren
    col_img1, col_data1, gap1, col_center, gap2, col_data2, col_img2 = st.columns([1, 2.8, 0.2, 4, 0.2, 2.8, 1])

    with col_img1:
        st.image(vis_spiller_billede(p1["img"], p1["pid"]), use_container_width=True)

    with col_data1:
        st.markdown(f"<h4 style='margin:0; color:{HIF_RED};'>{p1['navn']}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0 0 15px 0; font-size:0.75rem; color:gray;'>{p1['klub']} | {p1['pos']}</p>", unsafe_allow_html=True)
        
        m_cols = st.columns(4)
        for i, (k, v) in enumerate(p1['stats'].items()):
            m_cols[i].metric(k, v)
        
        st.markdown("<div class='stats-container'>", unsafe_allow_html=True)
        if p1['adv']:
            for k, v in p1['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-label'>{k}</span><span class='stat-val' style='color:{HIF_RED}; text-align:right;'>{v}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_center:
        # Radar Chart
        labels = ['Beslutsomhed', 'Teknik', 'Fart', 'Udholdenhed', 'Lederegenskaber', 'Aggresivitet', 'Spilintelligens']
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=p1['r']+[p1['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_RED, opacity=0.2))
        fig.add_trace(go.Scatterpolar(r=p2['r']+[p2['r'][0]], theta=labels+[labels[0]], fill='toself', line_color=HIF_BLUE, opacity=0.2))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 6], showticklabels=False, gridcolor="#eee")),
            height=350, margin=dict(l=50, r=50, t=30, b=0), showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # Opsummering
        diffs = {k: p1['scout_scores'][k] - p2['scout_scores'][k] for k in labels}
        max_p1 = max(diffs, key=diffs.get)
        max_p2 = min(diffs, key=diffs.get)
        
        st.markdown(f"""
            <div class='summary-box'>
                <strong>Sammenligning:</strong><br>
                {p1['navn']} er markant stærkere på <strong>{max_p1.lower()}</strong>, 
                mens {p2['navn']} har sin største fordel i <strong>{max_p2.lower()}</strong>.
            </div>
        """, unsafe_allow_html=True)

    with col_data2:
        st.markdown(f"<h4 style='margin:0; color:{HIF_BLUE}; text-align:right;'>{p2['navn']}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0 0 15px 0; font-size:0.75rem; color:gray; text-align:right;'>{p2['pos']} | {p2['klub']}</p>", unsafe_allow_html=True)
        
        st.markdown('<div class="blue-metric">', unsafe_allow_html=True)
        m_cols = st.columns(4)
        for i, (k, v) in enumerate(p2['stats'].items()):
            m_cols[i].metric(k, v)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<div class='stats-container'>", unsafe_allow_html=True)
        if p2['adv']:
            for k, v in p2['adv'].items():
                st.markdown(f"<div class='stat-row'><span class='stat-val' style='color:{HIF_BLUE}; text-align:left;'>{v}</span><span class='stat-label' style='text-align:right;'>{k}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_img2:
        st.image(vis_spiller_billede(p2["img"], p2["pid"]), use_container_width=True)
