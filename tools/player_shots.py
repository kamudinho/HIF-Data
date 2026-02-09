import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # 1. FIX KOLONNENAVNE VED POSITION (Index-baseret)
    # Da vi ved fra dit billede at MINUTE er nr. 2, tvinger vi navngivningen:
    cols = list(df_events.columns)
    # Vi omdøber den kolonne der fysisk ligger på plads nr. 2 til 'MINUTE_STRICT'
    df_events = df_events.rename(columns={cols[1]: 'MINUTE_STRICT'})
    # Vi gør det samme for de andre vigtige kolonner for en sikkerheds skyld
    df_events.columns = df_events.columns.str.strip().str.upper()

    # 2. SPILLER DROPDOWN I SIDEBAR
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('**Spillerfokus**')
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING
    df_filtered = hif_events if valgt_spiller == "Alle Spillere" else hif_events[hif_events[p_col] == valgt_spiller]
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 4. PLOTLY BANE (Med den boks du bad om)
    fig = go.Figure()

    # Bane-design (Hvid/Sort halvbane)
    shapes = [
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="black", width=2)),
        dict(type="rect", x0=21, y0=83, x1=79, y1=100, line=dict(color="black", width=2)),
        dict(type="rect", x0=40, y0=94, x1=60, y1=100, line=dict(color="black", width=2)),
        dict(type="path", path="M 38,83 A 12,12 0 0 0 62,83", line=dict(color="black", width=2))
    ]

    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal].copy()
        if subset.empty: continue
        
        # Vi henter minuttet fra vores omdøbte kolonne 'MINUTE_STRICT'
        # Vi bruger .iloc for at være 100% sikre på positionen
        hover_text = []
        for _, row in subset.iterrows():
            modstander = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
            minut_val = row['MINUTE_STRICT'] 
            hover_text.append(f"<b>vs. {modstander}</b><br>Min: {minut_val}")

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
