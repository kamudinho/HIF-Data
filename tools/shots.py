import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # 1. RENS DATA
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    
    # 2. DROPDOWN (Modstander)
    opp_ids = sorted([int(tid) for tid in df_events['OPPONENTTEAM_WYID'].unique() if tid != HIF_ID])
    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        navn = hold_map.get(mid, f"Ukendt Hold")
        dropdown_options.append((navn, mid))

    valgt_navn, valgt_id = st.selectbox("Vælg modstander", options=dropdown_options, format_func=lambda x: x[0])

    # 3. FILTRERING
    df_f = df_events[(df_events['TEAM_WYID'] == HIF_ID)]
    if valgt_id:
        df_f = df_f[df_f['OPPONENTTEAM_WYID'] == valgt_id]
        titel_tekst = f"HIF VS. {valgt_navn}"
    else:
        titel_tekst = "HIF VS. ALLE"

    # 4. SKUD DATA
    mask = df_f['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_f[mask].copy()
    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # 5. STATS
    total_shots = len(df_s)
    total_goals = df_s['IS_GOAL'].sum()
    conv_rate = f"{(total_goals/total_shots*100):.1f}%" if total_shots > 0 else "0.0%"

    # 6. TEGN BANEN (Med de manglende cirkler)
    fig = go.Figure()

    # Geometri (Wyscout: 0-100)
    shapes = [
        # Rammen
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="black", width=2)),
        # Straffesparksfelt
        dict(type="rect", x0=21.1, y0=83.2, x1=78.9, y1=100, line=dict(color="black", width=2)),
        # Lille felt
        dict(type="rect", x0=40.2, y0=94.2, x1=59.8, y1=100, line=dict(color="black", width=2)),
        # Målet
        dict(type="rect", x0=45, y0=100, x1=55, y1=101.5, line=dict(color="black", width=2)),
        
        # BUEN VED FELTET (The D) - Præcis bue
        dict(type="path", path="M 37,83.2 A 12,12 0 0 0 63,83.2", line=dict(color="black", width=2)),
        
        # MIDTERCIRKLEN (Halv)
        dict(type="path", path="M 32,50 A 18,18 0 0 1 68,50", line=dict(color="black", width=2)),
        
        # Midterlinjen
        dict(type="line", x0=0, y0=50, x1=100, y1=50, line=dict(color="black", width=2))
    ]

    # Tilføj skud
    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal]
        if subset.empty: continue
        
        hover_text = [f"<b>Modstander:</b> {hold_map.get(row['OPPONENTTEAM_WYID'], 'Ukendt')}<br><b>Minut:</b> {row['MINUTE']}" for _, row in subset.iterrows()]

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], y=subset['LOCATIONX'],
            mode='markers',
            marker=dict(
                size=18 if is_goal else 12,
                color=HIF_RED if is_goal else '#4a5568',
                opacity=0.9 if is_goal else 0.4,
                line=dict(width=1, color='white')
            ),
            text=hover_text,
            hoverinfo="text"
        ))

    # Layout og Stats i toppen
    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False, fixedrange=True),
        yaxis=dict(range=[48, 115], visible=False, fixedrange=True),
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=0, b=0),
        height=700,
        showlegend=False
    )

    # Stats Annotations
    stats_data = [
        (20, total_shots, "SKUD"),
        (40, total_goals, "MÅL"),
        (60, conv_rate, "KONV."),
        (80, "0.00", "xG TOTAL")
    ]
    
    fig.add_annotation(x=50, y=112, text=f"<b>{titel_tekst}</b>", showarrow=False, font=dict(size=18))
    
    for x, val, lab in stats_data:
        fig.add_annotation(x=x, y=107, text=f"<span style='color:{HIF_RED}; font-size:20px'><b>{val}</b></span><br><span style='color:gray; font-size:10px'><b>{lab}</b></span>", showarrow=False)

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
