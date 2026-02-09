import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # 1. STANDARDISER DATA
    df_events.columns = df_events.columns.str.strip().str.upper()

    # 2. SPILLER DROPDOWN I SIDEBAR
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('<p class="sidebar-header">Spillerfokus</p>', unsafe_allow_html=True)
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING
    df_filtered = hif_events if valgt_spiller == "Alle Spillere" else hif_events[hif_events[p_col] == valgt_spiller]
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 4. STATS (Vises som Streamlit metrics)
    s_shots = len(df_s)
    s_goals = df_s['IS_GOAL'].sum()
    s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"

    c1, c2, c3 = st.columns(3)
    c1.metric("SKUD", s_shots)
    c2.metric("MÅL", s_goals)
    c3.metric("KONV.", s_conv)

    # 5. INTERAKTIV BANE (Plotly)
    fig = go.Figure()

    # Tegn banen (halv bane, hvid med sorte linjer)
    shapes = [
        # Ydre linje
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="black", width=2)),
        # Feltet
        dict(type="rect", x0=21, y0=83, x1=79, y1=100, line=dict(color="black", width=2)),
        # Lille felt
        dict(type="rect", x0=40, y0=94, x1=60, y1=100, line=dict(color="black", width=2)),
        # Buen (straffesparksfelt)
        dict(type="path", path="M 38,83 A 12,12 0 0 0 62,83", line=dict(color="black", width=2))
    ]

    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal]
        if subset.empty: continue
        
        # Lav boks-indholdet (Hoverlabel)
        hover_text = []
        for _, row in subset.iterrows():
            modstander = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
            minut = row['MINUTE']
            hover_text.append(f"<b>vs. {modstander}</b><br>Min: {minut}")

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], # Wyscout bredde
            y=subset['LOCATIONX'], # Wyscout længde
            mode='markers',
            marker=dict(
                size=16 if is_goal else 10,
                color=HIF_RED if is_goal else 'rgba(74, 85, 104, 0.4)',
                line=dict(width=1, color='white')
            ),
            text=hover_text,
            hoverinfo="text", # Dette gør, at kun vores boks vises
            name="Mål" if is_goal else "Skud"
        ))

    # Konfiguration af banens udseende
    fig.update_layout(
        title=dict(text=valgt_spiller.upper(), x=0.5, font=dict(size=16)),
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False, fixedrange=True),
        yaxis=dict(range=[50, 105], visible=False, fixedrange=True),
        plot_bgcolor='white',
        margin=dict(l=20, r=20, t=50, b=20),
        height=600,
        showlegend=False,
        hovermode='closest',
        clickmode='event' # Aktiverer boksen ved klik/tryk
    )

    # Vis kortet i Streamlit
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
