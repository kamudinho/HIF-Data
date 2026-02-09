import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    
    # --- 1. DATAVASK & SIDEBAR ---
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'NAVN'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # --- 2. FILTRERING ---
    if valgt_spiller != "Alle Spillere":
        df_filtered = hif_events[hif_events[p_col] == valgt_spiller].copy()
        titel_tekst = valgt_spiller.upper()
    else:
        df_filtered = hif_events.copy()
        titel_tekst = "HIF - ALLE SPILLERE"

    # Find skud
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # --- 3. STATS BEREGNING ---
    s_shots = len(df_s)
    s_goals = df_s['IS_GOAL'].sum()
    s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"
    # Vi lader xG ligge da den ikke er i din event-fil

    # --- 4. INTERAKTIV BANE (MPLSOCCER STYLE) ---
    fig = go.Figure()

    # Tegn banens linjer præcis som VerticalPitch (halv bane)
    # Vi bruger 0-68 (bredde) og 0-105 (længde)
    shapes = [
        # Ydre ramme
        dict(type="rect", x0=0, y0=60, x1=68, y1=105, line=dict(color="#1a1a1a", width=2)),
        # Straffesparksfelt
        dict(type="rect", x0=13.84, y0=88.5, x1=54.16, y1=105, line=dict(color="#1a1a1a", width=2)),
        # Lille felt
        dict(type="rect", x0=24.84, y0=99.5, x1=43.16, y1=105, line=dict(color="#1a1a1a", width=2)),
        # Buen ved feltet
        dict(type="path", path="M 28.5,88.5 A 9.15,9.15 0 0 1 39.5,88.5", line=dict(color="#1a1a1a", width=2))
    ]

    # Tilføj skud-prikker
    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal]
        if subset.empty: continue

        hover_text = []
        for _, row in subset.iterrows():
            opp = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
            minut = row['MINUTE']
            hover_text.append(f"<b>vs. {opp}</b><br>Min: {minut}")

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'] * 0.68,
            y=subset['LOCATIONX'] * 1.05,
            mode='markers',
            marker=dict(
                size=18 if is_goal else 10,
                color=HIF_RED if is_goal else '#4a5568',
                opacity=0.9 if is_goal else 0.4,
                line=dict(width=1, color='white')
            ),
            text=hover_text,
            hoverinfo="text",
            showlegend=False
        ))

    # Layout og Annotations (Stats i toppen)
    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-2, 70], visible=False, fixedrange=True),
        yaxis=dict(range=[60, 116], visible=False, fixedrange=True),
        plot_bgcolor='white',
        width=800, height=600,
        margin=dict(l=0, r=0, t=0, b=0),
        hoverlabel=dict(bgcolor="white", font_size=14, font_family="Arial")
    )

    # Tilføj Tekst (Titel og Stats) ligesom i dit Matplotlib plot
    fig.add_annotation(x=34, y=114, text=titel_tekst, showarrow=False, font=dict(size=16, color="#333", family="Arial Black"))
    
    # Stats rækken
    stats_labels = [f"<b>{s_shots}</b><br><span style='font-size:10px;color:gray'>SKUD</span>", 
                    f"<b>{s_goals}</b><br><span style='font-size:10px;color:gray'>MÅL</span>", 
                    f"<b>{s_conv}</b><br><span style='font-size:10px;color:gray'>KONV.</span>"]
    x_pos = [20, 34, 48]
    
    for i in range(3):
        fig.add_annotation(x=x_pos[i], y=110, text=stats_labels[i], showarrow=False, font=dict(size=18, color=HIF_RED))

    # Vis banen
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
