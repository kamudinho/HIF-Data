import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    DARK_GREY = '#413B4D' 

    # 1. RENS KOLONNER
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    
    # 2. SPILLERVALG I SIDEBAR
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING
    df_filtered = hif_events if valgt_spiller == "Alle Spillere" else hif_events[hif_events[p_col] == valgt_spiller]
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 4. BYG DEN INTERAKTIVE BANE (Med buer)
    fig = go.Figure()

    # Vi tegner banens geometri
    shapes = [
        # Halv bane omridset
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="#1A202C", width=2)),
        # Straffesparksfeltet
        dict(type="rect", x0=21, y0=83, x1=79, y1=100, line=dict(color="#1A202C", width=2)),
        # Det lille felt
        dict(type="rect", x0=40, y0=94, x1=60, y1=100, line=dict(color="#1A202C", width=2)),
        
        # BUEN VED FELTET (The D)
        # Vi tegner en ark fra x=38 til x=62 ved y=83
        dict(type="path", 
             path="M 37.5,83 A 10,10 0 0 0 62.5,83", 
             line=dict(color="#1A202C", width=2)),
        
        # MIDTERCIRKLEN (Halv)
        # Vi tegner en ark ved midterlinjen (y=50)
        dict(type="path", 
             path="M 35,50 A 15,15 0 0 1 65,50", 
             line=dict(color="#1A202C", width=2)),
             
        # Midterlinjen
        dict(type="line", x0=0, y0=50, x1=100, y1=50, line=dict(color="#1A202C", width=2))
    ]

    # 5. TILFØJ SKUD-PUNKTER
    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal]
        if subset.empty: continue
        
        hover_text = []
        for _, row in subset.iterrows():
            opp = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
            minut = row['MINUTE']
            res_txt = "Mål" if is_goal else "Afslutning"
            hover_text.append(
                f"<b>Kamp:</b> {opp} vs. HIF<br>"
                f"<b>Spiller:</b> {valgt_spiller}<br>"
                f"<b>Min:</b> {minut}<br>"
                f"<b>Resultat:</b> {res_txt}"
            )

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], 
            y=subset['LOCATIONX'],
            mode='markers',
            marker=dict(
                size=18 if is_goal else 12,
                color=HIF_RED if is_goal else DARK_GREY,
                opacity=0.8,
                line=dict(width=1, color='white')
            ),
            text=hover_text,
            hoverinfo="text",
            showlegend=False
        ))

    # Layout indstillinger
    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False, fixedrange=True),
        yaxis=dict(range=[45, 105], visible=False, fixedrange=True),
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=50, b=0),
        height=700,
        hoverlabel=dict(bgcolor="white", font_size=14, bordercolor="#1A202C")
    )

    # Tilføj en pæn titel med stats
    mål_antal = len(df_s[df_s['IS_GOAL']])
    skud_antal = len(df_s)
    fig.add_annotation(
        x=50, y=108,
        text=f"<b>{valgt_spiller.upper()}</b><br>{mål_antal} Mål på {skud_antal} Afslutninger",
        showarrow=False, font=dict(size=16, color="#1A202C")
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
