import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    # Mørk farve til afslutninger som i dit billede
    DARK_GREY = '#413B4D' 

    # 1. RENS DATA
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

    # 4. BYG DEN INTERAKTIVE BANE (Plotly)
    fig = go.Figure()

    # Tegn banens linjer (Som i dit billede: Mørkeblå/Sorte linjer på hvid baggrund)
    shapes = [
        # Bane omridset (Halv bane)
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="#1A202C", width=2)),
        # Straffesparksfeltet
        dict(type="rect", x0=20, y0=83, x1=80, y1=100, line=dict(color="#1A202C", width=2)),
        # Det lille felt
        dict(type="rect", x0=40, y0=94, x1=60, y1=100, line=dict(color="#1A202C", width=2)),
        # Målet (den lille boks øverst)
        dict(type="rect", x0=45, y0=100, x1=55, y1=102, line=dict(color="#1A202C", width=2)),
        # Buen ved feltet
        dict(type="path", path="M 35,83 A 15,15 0 0 0 65,83", line=dict(color="#1A202C", width=2)),
        # Midtercirkel (halv)
        dict(type="path", path="M 35,50 A 15,15 0 0 1 65,50", line=dict(color="#1A202C", width=2))
    ]

    # Tilføj skud-punkter
    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal]
        if subset.empty: continue
        
        # Lav den boks-tekst du har i dit billede
        hover_text = []
        for _, row in subset.iterrows():
            opp = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
            minut = row['MINUTE']
            resultat = "Mål" if is_goal else "Misset"
            # Formatet fra dit billede "Test 2.png"
            hover_text.append(
                f"Kamp: {opp} vs. HIF<br>"
                f"Spiller: {valgt_spiller}<br>"
                f"Min: {minut}<br>"
                f"Resultat: {resultat}"
            )

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], 
            y=subset['LOCATIONX'],
            mode='markers',
            marker=dict(
                size=22 if is_goal else 15,
                color=HIF_RED if is_goal else DARK_GREY,
                opacity=0.8,
                line=dict(width=1.5, color='white')
            ),
            text=hover_text,
            hoverinfo="text",
            showlegend=False
        ))

    # Layout indstillinger for at ramme dit billede
    fig.update_layout(
        title=dict(
            text=f"<b>Hvidovre IF</b><br>Sæsonoversigt - {valgt_spiller}<br>{len(df_s[df_s['IS_GOAL']])} Mål | {len(df_s)} Skud",
            x=0.5, y=0.95, xanchor='center', font=dict(size=18, color='#1A202C')
        ),
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False, fixedrange=True),
        yaxis=dict(range=[45, 105], visible=False, fixedrange=True),
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=100, b=0),
        height=750,
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_family="Arial",
            bordercolor="#1A202C"
        )
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
