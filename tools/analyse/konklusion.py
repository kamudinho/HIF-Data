import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

def beregn_status(aktuel, forventet, metric_navn):
    diff = aktuel - forventet
    tærskel = forventet * 0.1  # 10% margen
    
    if diff > tærskel:
        return "Overperformer", "normal", "#28a745"
    elif diff < -tærskel:
        return "Underperformer", "inverse", "#dc3545"
    else:
        return "Som forventet", "off", "#ffc107"

def vis_side():
    st.title("Hold Performance Opsummering")
    
    # 1. Load data (genbrug dine eksisterende funktioner)
    conn = _get_snowflake_conn()
    # Her henter vi gennemsnit for ligaen eller specifikke hold-stats
    df_wy = conn.query("SELECT * FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL") 
    
    # 2. Vælg hold
    hold_liste = ["Hvidovre", "FC Fredericia", "OB", "AC Horsens"] # Eksempel
    valgt_hold = st.selectbox("Vælg hold til analyse:", hold_liste)
    
    # 3. Definer de 5 metrics (Eksempel)
    # Vi lader som om vi har beregnet gennemsnit for det valgte hold
    metrics = {
        "Mål vs xG": {"aktuel": 1.5, "base": 1.2, "enhed": "pr. kamp"},
        "Skud vs xG": {"aktuel": 12.4, "base": 14.1, "enhed": "pr. kamp"},
        "Erobringer": {"aktuel": 45.0, "base": 42.0, "enhed": "pr. kamp"},
        "PPDA": {"aktuel": 10.5, "base": 12.0, "enhed": "intensitet"},
        "xG imod": {"aktuel": 0.9, "base": 1.1, "enhed": "pr. kamp"}
    }

    # 4. Visning i kolonner
    cols = st.columns(5)
    
    for i, (navn, data) in enumerate(metrics.items()):
        status, label_type, farve = beregn_status(data['aktuel'], data['base'], navn)
        
        with cols[i]:
            st.metric(
                label=navn, 
                value=f"{data['aktuel']} {data['enhed']}", 
                delta=f"{round(data['aktuel'] - data['base'], 2)} vs gns."
            )
            st.markdown(f"<span style='color:{farve}; font-weight:bold;'>{status}</span>", unsafe_allow_html=True)

    # 5. Visualisering (Radar Chart er genialt her)
    st.subheader("Performance Profil")
    vis_radar_chart(valgt_hold, metrics)

def vis_radar_chart(hold, metrics):
    categories = list(metrics.keys())
    values = [d['aktuel'] for d in metrics.values()]
    base_values = [d['base'] for d in metrics.values()]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself', name=hold,
        line_color='#df003b'
    ))
    fig.add_trace(go.Scatterpolar(
        r=base_values, theta=categories, fill='toself', name='Ligagennemsnit',
        line_color='gray'
    ))

    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)
