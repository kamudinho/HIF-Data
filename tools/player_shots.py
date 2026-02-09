import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # --- 1. SPILLER DROPDOWN I SIDEBAR ---
    # Vi henter spillere fra HIF
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    spiller_navne = sorted(hif_events['PLAYER_NAME'].dropna().unique())
    
    # Vi bruger st.sidebar til dropdownen
    with st.sidebar:
        st.markdown("---")
        st.markdown('<p class="sidebar-header">Spillervalg</p>', unsafe_allow_html=True)
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # --- 2. FILTRERING ---
    if valgt_spiller != "Alle Spillere":
        df_filtered = hif_events[hif_events['PLAYER_NAME'] == valgt_spiller]
        titel_tekst = valgt_spiller
    else:
        df_filtered = hif_events
        titel_tekst = "HIF - Alle Spillere"

    # Filtrer skud
    shot_mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    spiller_shots = df_filtered[shot_mask].copy()
    
    if spiller_shots.empty:
        st.warning(f"Ingen skud registreret for {valgt_spiller}")
        return

    # Marker mål
    spiller_shots['IS_GOAL'] = spiller_shots.apply(
        lambda r: 'goal' in str(r.get('PRIMARYTYPE', '')).lower(), axis=1
    )

    # --- 3. STATS BEREGNING ---
    s_shots = len(spiller_shots)
    s_goals = spiller_shots['IS_GOAL'].sum()
    raw_xg = pd.to_numeric(spiller_shots['XG'], errors='coerce').fillna(0).sum()
    if raw_xg > s_shots: raw_xg = raw_xg / 100
    
    # Vis stats i toppen af siden
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SKUD", s_shots)
    c2.metric("MÅL", s_goals)
    c3.metric("KONV.", f"{(s_goals/s_shots*100):.1f}%" if s_shots > 0 else "0%")
    c4.metric("xG TOTAL", f"{raw_xg:.2f}")

    # --- 4. INTERAKTIVT SKUDKORT (PLOTLY) ---
    fig = go.Figure()

    # Tegn banen (halv bane)
    # Vi laver simple linjer for at simulere feltet
    shapes = [
        dict(type="rect", x0=0, y0=60, x1=100, y1=100, line=dict(color="black", width=1)), # Bane omrids
        dict(type="rect", x0=20, y0=85, x1=80, y1=100, line=dict(color="black", width=1)), # Felt
        dict(type="rect", x0=40, y0=95, x1=60, y1=100, line=dict(color="black", width=1)), # Lille felt
    ]

    for is_goal in [False, True]:
        mask = spiller_shots['IS_GOAL'] == is_goal
        subset = spiller_shots[mask]
        
        if subset.empty: continue

        # Lav hover-tekst
        hover_info = []
        for _, row in subset.iterrows():
            modstander = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
            xg_val = round(row['XG']/100 if row['XG'] > 1 else row['XG'], 2)
            hover_info.append(f"<b>vs. {modstander}</b><br>xG: {xg_val}")

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], # I Plotly bruger vi de rå koordinater (0-100)
            y=subset['LOCATIONX'],
            mode='markers',
            name="Mål" if is_goal else "Skud",
            marker=dict(
                size=20 if is_goal else 12,
                color=HIF_RED if is_goal else 'rgba(74, 85, 104, 0.4)',
                line=dict(width=1, color='white')
            ),
            text=hover_info,
            hoverinfo="text"
        ))

    fig.update_layout(
        title=dict(text=titel_tekst.upper(), x=0.5, font=dict(size=20)),
        shapes=shapes,
        xaxis=dict(range=[0, 100], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[60, 105], showgrid=False, zeroline=False, showticklabels=False),
        width=800,
        height=600,
        plot_bgcolor='white',
        clickmode='event+select',
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)
