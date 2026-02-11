import streamlit as st
import pandas as pd
import numpy as np  # VIGTIGT: Denne skal være her!
import plotly.graph_objects as go

def get_arc(center_x, center_y, radius, start_angle, end_angle):
    """Hjælpefunktion til at generere koordinater til buer"""
    angles = np.linspace(np.radians(start_angle), np.radians(end_angle), 50)
    return center_x + radius * np.cos(angles), center_y + radius * np.sin(angles)

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    DARK_GREY = '#413B4D' 

    # 1. DATA RENS
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    
    # Tjek for kolonnenavne (Wyscout bruger ofte PLAYER_NAME)
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 2. FILTRERING
    df_filtered = hif_events if valgt_spiller == "Alle Spillere" else hif_events[hif_events[p_col] == valgt_spiller]
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)
    df_s['LOCATIONX'] = pd.to_numeric(df_s['LOCATIONX'], errors='coerce')
    df_s['LOCATIONY'] = pd.to_numeric(df_s['LOCATIONY'], errors='coerce')

    # 3. BYG PLOTLY FIGUR
    fig = go.Figure()
    lc = "#cfcfcf" # Linjefarve
    
    # Banens linjer (Halv bane)
    lines = [
        ((0, 100, 100, 0, 0), (50, 50, 100, 100, 50)), # Omrids
        ((19, 19, 81, 81), (100, 84, 84, 100)),        # Feltet
        ((36.8, 36.8, 63.2, 63.2), (100, 94.2, 94.2, 100)) # Det lille felt
    ]

    for x_coords, y_coords in lines:
        fig.add_trace(go.Scatter(x=x_coords, y=y_coords, mode='lines', 
                                 line=dict(color=lc, width=1.5), hoverinfo='skip', showlegend=False))

    # Buer med get_arc (nu virker np.linspace)
    # The D
    arc_x, arc_y = get_arc(50, 84, 9, 195, 345)
    fig.add_trace(go.Scatter(x=arc_x, y=arc_y, mode='lines', line=dict(color=lc, width=1.5), hoverinfo='skip', showlegend=False))

    # Midtercirkel
    arc_x2, arc_y2 = get_arc(50, 50, 9.15, 0, 180)
    fig.add_trace(go.Scatter(x=arc_x2, y=arc_y2, mode='lines', line=dict(color=lc, width=1.5), hoverinfo='skip', showlegend=False))

    # 4. TILFØJ PUNKTER
    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal]
        if subset.empty: continue
        
        hover_text = [
            f"<b>{row[p_col]}</b><br>Mod: {hold_map.get(row['OPPONENTTEAM_WYID'], 'Ukendt')}<br>Tid: {row['MINUTE']}'<br>Resultat: {'MÅL' if is_goal else 'SKUD'}"
            for _, row in subset.iterrows()
        ]

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'],
            y=subset['LOCATIONX'],
            mode='markers',
            marker=dict(
                size=14 if is_goal else 9,
                color=HIF_RED if is_goal else DARK_GREY,
                line=dict(width=1, color='white'),
                opacity=0.9
            ),
            text=hover_text,
            hoverinfo="text",
            showlegend=False
        ))

    # 5. LAYOUT & ZOOM
    fig.update_layout(
        xaxis=dict(range=[-2, 102], visible=False, fixedrange=True),
        yaxis=dict(range=[48, 105], visible=False, fixedrange=True),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=20, b=0),
        height=550,
        hoverlabel=dict(bgcolor="white", font_size=12)
    )

    # 6. VISNING (70% BREDDE)
    spacer_l, center, spacer_r = st.columns([0.15, 0.7, 0.15])
    with center:
        mål = len(df_s[df_s['IS_GOAL']])
        st.markdown(f"<h3 style='text-align: center; margin-bottom: 0;'>{valgt_spiller.upper()}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: grey;'>{mål} mål på {len(df_s)} afslutninger</p>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
