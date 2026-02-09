import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import plotly.express as px
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # 1. RENS DATA OG TVING KOLONNENAVNE
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    
    # 2. SPILLER DROPDOWN I SIDEBAR
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'NAVN'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('<p class="sidebar-header">Spillerfokus</p>', unsafe_allow_html=True)
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING
    if valgt_spiller != "Alle Spillere":
        df_filtered = hif_events[hif_events[p_col] == valgt_spiller].copy()
    else:
        df_filtered = hif_events.copy()

    # Find skud
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 4. STATS
    s_shots = len(df_s)
    s_goals = df_s['IS_GOAL'].sum()
    s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"

    st.subheader(f"Afslutninger: {valgt_spiller}")
    c1, c2, c3 = st.columns(3)
    c1.metric("SKUD", s_shots)
    c2.metric("MÅL", s_goals)
    c3.metric("KONV.", s_conv)

    # 5. DEN PROFESSIONELLE BANE (Interaktiv med Plotly)
    # Vi bruger Plotly til at tegne banen præcis som mplsoccer, så du får hover-effekten
    fig = go.Figure()

    # Tegn banens linjer (præcis som VerticalPitch)
    shapes = [
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="black", width=2)), # Halv bane
        dict(type="rect", x0=20, y0=83.2, x1=80, y1=100, line=dict(color="black", width=2)), # Felt
        dict(type="rect", x0=40, y0=94.2, x1=60, y1=100, line=dict(color="black", width=2)), # Lille felt
        dict(type="circle", x0=38, y0=78, x1=62, y1=88, line=dict(color="black", width=2)), # Bue
    ]

    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal]
        if subset.empty: continue
        
        # Lav hover-tekst ("vs. xx" og "Min: xx")
        hover_text = []
        for _, row in subset.iterrows():
            opp = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
            minut = row['MINUTE'] # Nu ved vi den er der!
            hover_text.append(f"<b>vs. {opp}</b><br>Min: {minut}")

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], 
            y=subset['LOCATIONX'],
            mode='markers',
            marker=dict(
                size=18 if is_goal else 12,
                color=HIF_RED if is_goal else 'rgba(74, 85, 104, 0.5)',
                line=dict(width=1, color='white')
            ),
            text=hover_text,
            hoverinfo="text",
            showlegend=False
        ))

    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False),
        yaxis=dict(range=[50, 105], visible=False),
        plot_bgcolor='white',
        height=650,
        margin=dict(l=0, r=0, t=0, b=0),
        hoverlabel=dict(bgcolor="white", font_size=16)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 6. TABEL
    st.markdown("---")
    vis_df = df_s.copy()
    vis_df['MODSTANDER'] = vis_df['OPPONENTTEAM_WYID'].map(hold_map)
    vis_df['RESULTAT'] = vis_df['IS_GOAL'].map({True: '⚽ MÅL', False: '❌ Skud'})
    
    # Her tvinger vi visning af MINUTE
    st.dataframe(
        vis_df[['MINUTE', 'MODSTANDER', 'RESULTAT']].sort_values('MINUTE', ascending=False),
        hide_index=True,
        use_container_width=True
    )
