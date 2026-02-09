import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # 1. BRUTE FORCE RENS AF KOLONNER (Fjerner usynlige tegn og mærkelig formatering)
    # Vi fjerner alt der ikke er bogstaver/tal og tvinger til STORE bogstaver
    df_events.columns = [re.sub(r'[^A-Z0-9_]', '', str(c).upper()) for c in df_events.columns]

    # 2. SPILLER DROPDOWN I SIDEBAR
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    
    # Tjek for spillernavn
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('<p class="sidebar-header">Spillerfokus</p>', unsafe_allow_html=True)
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING
    df_filtered = hif_events if valgt_spiller == "Alle Spillere" else hif_events[hif_events[p_col] == valgt_spiller]
    
    # Find skud
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 4. METRICS
    s_shots = len(df_s)
    s_goals = df_s['IS_GOAL'].sum()
    s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"

    c1, c2, c3 = st.columns(3)
    c1.metric("SKUD", s_shots)
    c2.metric("MÅL", s_goals)
    c3.metric("KONV.", s_conv)

    # 5. INTERAKTIV BANE (Plotly)
    fig = go.Figure()

    # Banens streger (Halv bane layout)
    shapes = [
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="black", width=2)),
        dict(type="rect", x0=21, y0=83, x1=79, y1=100, line=dict(color="black", width=2)),
        dict(type="rect", x0=40, y0=94, x1=60, y1=100, line=dict(color="black", width=2)),
        dict(type="path", path="M 38,83 A 12,12 0 0 0 62,83", line=dict(color="black", width=2))
    ]

    # Vi bruger en sikker måde at hente værdier på for at undgå KeyError i hover-boksen
    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal].copy()
        if subset.empty: continue
        
        # Vi laver hover-teksten her UDEN at loope manuelt over rækkerne (for at undgå KeyErrors)
        # Vi mapper modstandere via hold_map og bruger .get() sikkerhed for minutter
        opponents = subset['OPPONENTTEAM_WYID'].map(hold_map).fillna("Ukendt")
        
        # Vi bruger en list comprehension med .get() sikkerhed for rækken
        hover_text = []
        for idx, row in subset.iterrows():
            m = row.get('MINUTE', '??')
            h = opponents.get(idx, 'Ukendt')
            hover_text.append(f"<b>vs. {h}</b><br>Min: {m}")

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], 
            y=subset['LOCATIONX'],
            mode='markers',
            marker=dict(
                size=16 if is_goal else 10,
                color=HIF_RED if is_goal else 'rgba(74, 85, 104, 0.4)',
                line=dict(width=1, color='white')
            ),
            text=hover_text,
            hoverinfo="text",
            showlegend=False
        ))

    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False, fixedrange=True),
        yaxis=dict(range=[50, 105], visible=False, fixedrange=True),
        plot_bgcolor='white',
        margin=dict(l=10, r=10, t=20, b=10),
        height=600,
        hovermode='closest'
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
