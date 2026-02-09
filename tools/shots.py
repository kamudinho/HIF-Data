import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'
    BG_WHITE = '#ffffff'

    # --- 1. RENS KOLONNER (Sikrer mod KeyError) ---
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]

    # --- 2. DROPDOWN (Vælg Modstander) ---
    opp_ids = sorted([int(tid) for tid in df_events['OPPONENTTEAM_WYID'].unique() if tid != HIF_ID])
    dropdown_options = [("Alle Kampe", None)]
    for mid in opp_ids:
        navn = hold_map.get(mid, f"Ukendt Hold (ID: {mid})")
        dropdown_options.append((navn, mid))

    valgt_navn, valgt_id = st.selectbox("Vælg modstander", options=dropdown_options, format_func=lambda x: x[0])

    # --- 3. FILTRERING ---
    if valgt_id is not None:
        df_events_filtered = df_events[(df_events['TEAM_WYID'] == HIF_ID) & (df_events['OPPONENTTEAM_WYID'] == valgt_id)]
        stats_df = df_kamp[(df_kamp['TEAM_WYID'] == HIF_ID) & (df_kamp['MATCH_WYID'].isin(df_events_filtered['MATCH_WYID'].unique()))].copy()
        titel_tekst = f"HIF vs. {valgt_navn}"
    else:
        df_events_filtered = df_events[df_events['TEAM_WYID'] == HIF_ID]
        stats_df = df_kamp[df_kamp['TEAM_WYID'] == HIF_ID].copy()
        titel_tekst = "HIF vs. Alle"

    # --- 4. STATS BEREGNING ---
    if not stats_df.empty:
        s_shots = int(pd.to_numeric(stats_df['SHOTS'], errors='coerce').fillna(0).sum())
        s_goals = int(pd.to_numeric(stats_df['GOALS'], errors='coerce').fillna(0).sum())
        raw_xg = pd.to_numeric(stats_df['XG'], errors='coerce').fillna(0).sum()
        if raw_xg > 100: raw_xg = raw_xg / 100 
        s_xg = f"{raw_xg:.2f}"
        s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"
    else:
        s_shots, s_goals, s_xg, s_conv = 0, 0, "0.00", "0.0%"

    # --- 5. INTERAKTIV BANE (Med buen og midtercirklen) ---
    fig = go.Figure()

    # Vi tegner banens geometri manuelt for at ramme mplsoccer looket 1:1
    shapes = [
        # Halv bane ramme (0-100 koordinater)
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="#1a1a1a", width=1.5)),
        # Straffesparksfelt
        dict(type="rect", x0=21, y0=83, x1=79, y1=100, line=dict(color="#1a1a1a", width=1.5)),
        # Lille felt
        dict(type="rect", x0=40, y0=94, x1=60, y1=100, line=dict(color="#1a1a1a", width=1.5)),
        # BUEN VED FELTKANT
        dict(type="path", path="M 37.5,83 A 12,12 0 0 0 62.5,83", line=dict(color="#1a1a1a", width=1.5)),
        # HALV MIDTERCIRKEL
        dict(type="path", path="M 35,50 A 15,15 0 0 1 65,50", line=dict(color="#1a1a1a", width=1.5))
    ]

    # --- 6. TEGN SKUD ---
    shot_mask = df_events_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    hif_shots = df_events_filtered[shot_mask].copy()
    
    if not hif_shots.empty:
        # Tjek for mål
        hif_shots['IS_GOAL'] = hif_shots.apply(lambda r: 'goal' in str(r.get('PRIMARYTYPE', '')).lower(), axis=1)
        
        for is_goal in [False, True]:
            subset = hif_shots[hif_shots['IS_GOAL'] == is_goal]
            if subset.empty: continue
            
            # Lav boks-indhold (Tooltip)
            hover_text = []
            for _, row in subset.iterrows():
                m_navn = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
                minut = row['MINUTE']
                hover_text.append(f"<b>Modstander:</b> {m_navn}<br><b>Minut:</b> {minut}")

            fig.add_trace(go.Scatter(
                x=subset['LOCATIONY'], 
                y=subset['LOCATIONX'],
                mode='markers',
                marker=dict(
                    size=18 if is_goal else 10,
                    color=HIF_RED if is_goal else '#4a5568',
                    opacity=0.9 if is_goal else 0.3,
                    line=dict(width=1, color='white')
                ),
                text=hover_text,
                hoverinfo="text",
                showlegend=False
            ))

    # --- 7. LAYOUT (Stats og Titel i toppen) ---
    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False, fixedrange=True),
        yaxis=dict(range=[48, 116], visible=False, fixedrange=True),
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        hoverlabel=dict(bgcolor="white", font_size=12)
    )

    # Titel
    fig.add_annotation(x=50, y=114, text=titel_tekst.upper(), showarrow=False, font=dict(size=14, color="#333", family="Arial Black"))
    
    # Stats-linjen
    s_labels = ["SKUD", "MÅL", "KONV.", "xG"]
    s_vals = [s_shots, s_goals, s_conv, s_xg]
    x_pos = [15, 35, 55, 75]
    
    for i in range(4):
        fig.add_annotation(x=x_pos[i], y=110, text=f"<b>{s_vals[i]}</b><br><span style='font-size:10px'>{s_labels[i]}</span>", 
                           showarrow=False, font=dict(size=14, color=HIF_RED))

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
