import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # Standardiser kolonnenavne så vi undgår KeyError
    df_events.columns = [c.upper() for c in df_events.columns]

    # --- 1. SPILLER DROPDOWN I SIDEBAR ---
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    
    # Vi tjekker om PLAYER_NAME findes, ellers bruger vi PLAYER_WYID
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('<p class="sidebar-header">Spillervalg</p>', unsafe_allow_html=True)
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # --- 2. FILTRERING ---
    if valgt_spiller != "Alle Spillere":
        df_filtered = hif_events[hif_events[p_col] == valgt_spiller]
        titel_tekst = valgt_spiller
    else:
        df_filtered = hif_events
        titel_tekst = "HIF - Alle Spillere"

    # Find skud (vi tjekker både PRIMARYTYPE og SUBTYPE)
    mask = (df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)) | \
           (df_filtered.get('SUBTYPE', pd.Series()).astype(str).str.contains('shot', case=False, na=False))
    
    spiller_shots = df_filtered[mask].copy()
    
    if spiller_shots.empty:
        st.warning(f"Ingen skud registreret for {valgt_spiller}")
        return

    spiller_shots['IS_GOAL'] = spiller_shots.apply(
        lambda r: 'goal' in str(r.get('PRIMARYTYPE', '')).lower(), axis=1
    )

    # --- 3. STATS BEREGNING (Sikker håndtering af XG) ---
    s_shots = len(spiller_shots)
    s_goals = spiller_shots['IS_GOAL'].sum()
    
    # Hvis 'XG' ikke findes, sætter vi det til 0 i stedet for at crashe
    if 'XG' in spiller_shots.columns:
        raw_xg = pd.to_numeric(spiller_shots['XG'], errors='coerce').fillna(0).sum()
        if raw_xg > s_shots: raw_xg = raw_xg / 100
    else:
        raw_xg = 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SKUD", s_shots)
    c2.metric("MÅL", s_goals)
    c3.metric("KONV.", f"{(s_goals/s_shots*100):.1f}%" if s_shots > 0 else "0%")
    c4.metric("xG TOTAL", f"{raw_xg:.2f}")

    # --- 4. PLOTLY KORT ---
    fig = go.Figure()
    # Bane-optegning (Lidt mere detaljeret)
    fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=100, line=dict(color="black"))
    fig.add_shape(type="rect", x0=20, y0=85, x1=80, y1=100, line=dict(color="black"))
    fig.add_shape(type="circle", x0=40, y0=80, x1=60, y1=90, line=dict(color="black"))

    for is_goal in [False, True]:
        m = spiller_shots['IS_GOAL'] == is_goal
        subset = spiller_shots[m]
        if subset.empty: continue

        hover_info = []
        for _, row in subset.iterrows():
            opp = hold_map.get(row['OPPONENTTEAM_WYID'], "Modstander")
            xg = round(row['XG']/100 if 'XG' in row and row['XG'] > 1 else row.get('XG', 0), 2)
            hover_info.append(f"<b>vs. {opp}</b><br>xG: {xg}")

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], y=subset['LOCATIONX'],
            mode='markers',
            marker=dict(size=15 if is_goal else 10, color=HIF_RED if is_goal else '#4a5568', opacity=0.8),
            text=hover_info, hoverinfo="text"
        ))

    fig.update_layout(yaxis=dict(range=[50, 105]), xaxis=dict(range=[0, 100]), height=600, plot_bgcolor='white')
    st.plotly_chart(fig, use_container_width=True)
