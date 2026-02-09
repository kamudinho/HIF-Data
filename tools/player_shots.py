import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # 1. RENS KOLONNER (Tving alt til STORE bogstaver for at undgå KeyError)
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]

    # 2. SPILLER DROPDOWN I SIDEBAR
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    
    # Tjek om vi skal bruge PLAYER_NAME eller PLAYER_WYID (altid store bogstaver nu)
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('**SPILLERVALG**')
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING (Brug STORE bogstaver for kolonnenavne)
    df_filtered = hif_events if valgt_spiller == "Alle Spillere" else hif_events[hif_events[p_col] == valgt_spiller]
    
    # Her er rettelsen: Vi leder efter 'PRIMARYTYPE' (STORE)
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    # 'PRIMARYTYPE' igen
    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 4. PLOTLY BANE (Med din klik-boks)
    fig = go.Figure()

    # Bane-design (Sort/Hvid halvbane)
    shapes = [
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="black", width=2)),
        dict(type="rect", x0=21, y0=83, x1=79, y1=100, line=dict(color="black", width=2)),
        dict(type="rect", x0=40, y0=94, x1=60, y1=100, line=dict(color="black", width=2)),
        dict(type="path", path="M 38,83 A 12,12 0 0 0 62,83", line=dict(color="black", width=2))
    ]

    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal].copy()
        if subset.empty: continue
        
        hover_text = []
        for _, row in subset.iterrows():
            # Brug STORE bogstaver her: OPPONENTTEAM_WYID og MINUTE
            modstander = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
            minut = row['MINUTE']
            hover_text.append(f"<b>vs. {modstander}</b><br>Min: {minut}")

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], 
            y=subset['LOCATIONX'],
            mode='markers',
            marker=dict(
                size=18 if is_goal else 12,
                color=HIF_RED if is_goal else 'rgba(74, 85, 104, 0.4)',
                line=dict(width=1, color='white')
            ),
            text=hover_text,
            hoverinfo="text"
        ))

    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False, fixedrange=True),
        yaxis=dict(range=[50, 105], visible=False, fixedrange=True),
        plot_bgcolor='white',
        margin=dict(l=10, r=10, t=20, b=10),
        height=600,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
