import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#df003b'

    # Standardiser kolonner
    df_events.columns = [c.upper() for c in df_events.columns]

    # --- 1. SPILLER DROPDOWN I SIDEBAR ---
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'NAVN'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    with st.sidebar:
        st.markdown("---")
        st.markdown('<p class="sidebar-header">Spillerfokus</p>', unsafe_allow_html=True)
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # --- 2. FILTRERING ---
    if valgt_spiller != "Alle Spillere":
        df_filtered = hif_events[hif_events[p_col] == valgt_spiller]
        titel_tekst = valgt_spiller
    else:
        df_filtered = hif_events
        titel_tekst = "HIF - Alle Spillere"

    # Find skud
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    spiller_shots = df_filtered[mask].copy()
    
    if spiller_shots.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    spiller_shots['IS_GOAL'] = spiller_shots.apply(
        lambda r: 'goal' in str(r.get('PRIMARYTYPE', '')).lower(), axis=1
    )

    # --- 3. STATS BEREGNING ---
    s_shots = len(spiller_shots)
    s_goals = spiller_shots['IS_GOAL'].sum()
    s_conv = f"{(s_goals / s_shots * 100):.1f}%" if s_shots > 0 else "0.0%"

    c1, c2, c3 = st.columns(3)
    c1.metric("SKUD", s_shots)
    c2.metric("MÅL", s_goals)
    c3.metric("KONVERTERING", s_conv)

    # --- 4. PLOTLY BANE (Professionelt look) ---
    fig = go.Figure()

    # Banens optegning (Svarer til mplsoccer VerticalPitch)
    shapes = [
        # Ydre ramme (halv bane)
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=dict(color="#1a1a1a", width=2)),
        # Feltet
        dict(type="rect", x0=20, y0=83.5, x1=80, y1=100, line=dict(color="#1a1a1a", width=2)),
        # Lille felt
        dict(type="rect", x0=40, y0=94.2, x1=60, y1=100, line=dict(color="#1a1a1a", width=2)),
        # Straffesparksfelt bue (simuleret)
        dict(type="path", path="M 38,83.5 Q 50,75 62,83.5", line=dict(color="#1a1a1a", width=2))
    ]

    # Tegn skud og mål
    for is_goal in [False, True]:
        subset = spiller_shots[spiller_shots['IS_GOAL'] == is_goal]
        if subset.empty: continue

        hover_text = []
        for _, row in subset.iterrows():
            modstander = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt")
            minut = row.get('MINUTE', '??')
            hover_text.append(f"<b>vs. {modstander}</b><br>Min: {minut}")

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], # Wyscout Y er bredden
            y=subset['LOCATIONX'], # Wyscout X er længden
            mode='markers',
            marker=dict(
                size=18 if is_goal else 12,
                color=HIF_RED if is_goal else 'rgba(74, 85, 104, 0.5)',
                line=dict(width=1.5, color='white')
            ),
            text=hover_text,
            hoverinfo="text",
            name="Mål" if is_goal else "Skud"
        ))

    # Layout indstillinger
    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-5, 105], visible=False),
        yaxis=dict(range=[50, 105], visible=False),
        width=800,
        height=600,
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=40, b=0),
        title=dict(text=titel_tekst.upper(), x=0.5, font=dict(size=18, color='#333')),
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=14, font_family="Arial")
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- 5. TABEL (Uden XG) ---
    st.markdown("### Kampoversigt")
    vis_df = spiller_shots.copy()
    vis_df['Modstander'] = vis_df['OPPONENTTEAM_WYID'].map(hold_map)
    vis_df['Type'] = vis_df['IS_GOAL'].map({True: '⚽ MÅL', False: '❌ Skud'})
    
    # Vi bruger kun kolonner der findes
    cols = ['MINUTE', 'Modstander', 'Type']
    st.dataframe(vis_df[cols].sort_values('MINUTE', ascending=False), hide_index=True, use_container_width=True)
