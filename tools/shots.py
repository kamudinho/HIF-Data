import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # --- 1. RENS KOLONNER ---
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    
    # --- 2. DROPDOWN ---
    opp_ids = sorted([int(tid) for tid in df_events['OPPONENTTEAM_WYID'].unique() if tid != HIF_ID])
    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        navn = hold_map.get(mid, f"Ukendt Hold")
        dropdown_options.append((navn, mid))

    valgt_navn, valgt_id = st.selectbox("Vælg modstander", options=dropdown_options, format_func=lambda x: x[0])

    # --- 3. FILTRERING ---
    df_f = df_events[df_events['TEAM_WYID'] == HIF_ID]
    if valgt_id:
        df_f = df_f[df_f['OPPONENTTEAM_WYID'] == valgt_id]
        titel_tekst = f"HIF VS. {valgt_navn}"
    else:
        titel_tekst = "HIF VS. ALLE"

    shot_mask = df_f['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_f[shot_mask].copy()
    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)

    # --- 4. STATS ---
    total_shots = len(df_s)
    total_goals = df_s['IS_GOAL'].sum()
    conv_rate = f"{(total_goals/total_shots*100):.1f}%" if total_shots > 0 else "0.0%"

    # --- 5. INTERAKTIV BANE (Med faste cirkler) ---
    fig = go.Figure()

    # Her tegner vi banen. Path bruger SVG-format:
    # M = Move to, L = Line to, A = Arc to
    shapes = [
        # Rammen (0 til 100)
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="black", width=1.5)),
        # Straffesparksfelt
        dict(type="rect", x0=20, y0=83, x1=80, y1=100, line=dict(color="black", width=1.5)),
        # Lille felt
        dict(type="rect", x0=40, y0=94, x1=60, y1=100, line=dict(color="black", width=1.5)),
        
        # BUEN VED FELTKANTEN (The D)
        dict(type="path", 
             path="M 37,83 A 13,13 0 0 0 63,83", 
             line=dict(color="black", width=1.5)),
        
        # MIDTERCIRKLEN (Halv cirkel ved midterlinjen)
        dict(type="path", 
             path="M 32,50 A 18,18 0 0 1 68,50", 
             line=dict(color="black", width=1.5)),
             
        # Midterlinjen
        dict(type="line", x0=0, y0=50, x1=100, y1=50, line=dict(color="black", width=1.5))
    ]

    # Tilføj skud-punkter
    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal]
        if subset.empty: continue
        
        # Tooltip-tekst
        hover_text = []
        for _, row in subset.iterrows():
            opp = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
            minut = row['MINUTE']
            hover_text.append(f"<b>Modstander:</b> {opp}<br><b>Minut:</b> {minut}")

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], 
            y=subset['LOCATIONX'],
            mode='markers',
            marker=dict(
                size=18 if is_goal else 12,
                color=HIF_RED if is_goal else '#4a5568',
                opacity=0.8,
                line=dict(width=1, color='white')
            ),
            text=hover_text,
            hoverinfo="text",
            showlegend=False
        ))

    # --- 6. LAYOUT ---
    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False, fixedrange=True),
        yaxis=dict(range=[48, 118], visible=False, fixedrange=True),
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=0, b=0),
        height=650,
        hoverlabel=dict(bgcolor="white", font_size=14, bordercolor="black")
    )

    # Titel og Stats i toppen
    fig.add_annotation(x=50, y=115, text=f"<b>{titel_tekst}</b>", showarrow=False, font=dict(size=18))
    
    stats_pos = [15, 35, 55, 75]
    vals = [total_shots, total_goals, conv_rate, "0.00"]
    labels = ["SKUD", "MÅL", "KONV.", "xG"]
    
    for i in range(4):
        fig.add_annotation(
            x=stats_pos[i], y=110, 
            text=f"<b style='color:{HIF_RED}; font-size:20px'>{vals[i]}</b><br><span style='font-size:10px; color:gray'>{labels[i]}</span>",
            showarrow=False
        )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
