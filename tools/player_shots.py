import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # 1. RENS KOLONNER OG TVING NAVNE
    # Vi fjerner alt "støj" og tvinger navne til store bogstaver
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    
    # 2. SPILLER DROPDOWN I SIDEBAR
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('**VÆLG SPILLER**')
        valgt_spiller = st.selectbox("HIF Spillere", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING
    df_filtered = hif_events if valgt_spiller == "Alle Spillere" else hif_events[hif_events[p_col] == valgt_spiller]
    
    # Find skud ved at kigge efter 'shot' i PRIMARYTYPE
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 4. INTERAKTIVT KORT (Plotly)
    fig = go.Figure()

    # Bane-design (Hvid bane, sorte linjer)
    shapes = [
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="black", width=2)),
        dict(type="rect", x0=21, y0=83, x1=79, y1=100, line=dict(color="black", width=2)),
        dict(type="rect", x0=40, y0=94, x1=60, y1=100, line=dict(color="black", width=2)),
        dict(type="path", path="M 38,83 A 12,12 0 0 0 62,83", line=dict(color="black", width=2))
    ]

    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal].copy()
        if subset.empty: continue
        
        # SIKKER HENTNING AF DATA TIL BOKSEN
        # Vi bruger .values for at undgå Index/Key-problemer i loopet
        opp_ids = subset['OPPONENTTEAM_WYID'].values
        minutes = subset['MINUTE'].values
        loc_x = subset['LOCATIONX'].values
        loc_y = subset['LOCATIONY'].values
        
        hover_text = []
        for i in range(len(subset)):
            modstander = hold_map.get(opp_ids[i], "Ukendt")
            minut = minutes[i]
            hover_text.append(f"<b>vs. {modstander}</b><br>Min: {minut}")

        fig.add_trace(go.Scatter(
            x=loc_y, 
            y=loc_x,
            mode='markers',
            marker=dict(
                size=18 if is_goal else 12,
                color=HIF_RED if is_goal else 'rgba(74, 85, 104, 0.4)',
                line=dict(width=1.5, color='white')
            ),
            text=hover_text,
            hoverinfo="text"
        ))

    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False, fixedrange=True),
        yaxis=dict(range=[50, 105], visible=False, fixedrange=True),
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=30, b=0),
        height=600,
        showlegend=False,
        hovermode='closest'
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
