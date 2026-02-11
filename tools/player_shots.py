import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(df_events, df_kamp, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'
    DARK_GREY = '#413B4D' 

    # 1. RENS KOLONNER
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    
    # 2. SPILLERVALG
    hif_events = df_events[df_events['TEAM_WYID'] == HIF_ID].copy()
    p_col = 'PLAYER_NAME' if 'PLAYER_NAME' in hif_events.columns else 'PLAYER_WYID'
    spiller_navne = sorted(hif_events[p_col].dropna().unique())
    
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        valgt_spiller = st.selectbox("Vælg spiller", options=["Alle Spillere"] + spiller_navne)

    # 3. FILTRERING
    df_filtered = hif_events if valgt_spiller == "Alle Spillere" else hif_events[hif_events[p_col] == valgt_spiller]
    mask = df_filtered['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)
    df_s = df_filtered[mask].copy()
    
    if df_s.empty:
        st.warning(f"Ingen skud fundet for {valgt_spiller}")
        return

    df_s['IS_GOAL'] = df_s['PRIMARYTYPE'].astype(str).str.contains('goal', case=False, na=False)
    df_s['LOCATIONX'] = pd.to_numeric(df_s['LOCATIONX'], errors='coerce')
    df_s['LOCATIONY'] = pd.to_numeric(df_s['LOCATIONY'], errors='coerce')

    # 4. BYG PLOTLY FIGUR (Bane-geometri)
    fig = go.Figure()

    # Vi tegner banens linjer manuelt i Plotly (Wyscout dimensioner)
    line_cfg = dict(color="#cfcfcf", width=1.5)
    
    shapes = [
        # Ydre ramme (øverste halvdel)
        dict(type="rect", x0=0, y0=50, x1=100, y1=100, line=line_cfg),
        # Feltet
        dict(type="rect", x0=19, y0=84, x1=81, y1=100, line=line_cfg),
        # Det lille felt
        dict(type="rect", x0=36.8, y0=94.2, x1=63.2, y1=100, line=line_cfg),
        # Målet
        dict(type="rect", x0=45, y0=100, x1=55, y1=100.5, line=line_cfg, fillcolor="#cfcfcf"),
        # Midterlinje
        dict(type="line", x0=0, y0=50, x1=100, y1=50, line=line_cfg),
        # Straffesparksfelt bue (The D)
        dict(type="path", path="M 36.8,84 A 10,10 0 0 1 63.2,84", line=line_cfg),
        # Midtercirkel bue
        dict(type="path", path="M 35,50 A 15,15 0 0 1 65,50", line=line_cfg)
    ]

    # 5. TILFØJ SKUD-PUNKTER
    for is_goal in [False, True]:
        subset = df_s[df_s['IS_GOAL'] == is_goal]
        if subset.empty: continue
        
        hover_text = []
        for _, row in subset.iterrows():
            opp = hold_map.get(row['OPPONENTTEAM_WYID'], "Ukendt modstander")
            minut = row['MINUTE']
            res_txt = "MÅL" if is_goal else "AFSLUTNING"
            hover_text.append(
                f"<b>{row[p_col]}</b><br>"
                f"Mod: {opp}<br>"
                f"Tid: {minut}'<br>"
                f"Resultat: <b>{res_txt}</b>"
            )

        fig.add_trace(go.Scatter(
            x=subset['LOCATIONY'], # Wyscout X er lodret, så vi mapper Y til Plotly X
            y=subset['LOCATIONX'], # Wyscout Y er vandret, så vi mapper X til Plotly Y
            mode='markers',
            marker=dict(
                size=14 if is_goal else 9,
                color=HIF_RED if is_goal else DARK_GREY,
                symbol='circle',
                line=dict(width=1, color='white'),
                opacity=0.9
            ),
            text=hover_text,
            hoverinfo="text",
            name="Mål" if is_goal else "Skud"
        ))

    # 6. LAYOUT (Zoomet ind og centreret)
    fig.update_layout(
        shapes=shapes,
        xaxis=dict(range=[-2, 102], visible=False, fixedrange=True),
        yaxis=dict(range=[48, 105], visible=False, fixedrange=True),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=20, b=0),
        height=500,
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Monospace")
    )

    # 7. VISNING I 70% BREDDE (For at matche de andre sider)
    spacer_l, center, spacer_r = st.columns([0.15, 0.7, 0.15])
    
    with center:
        # Pæn overskrift indeni center-kolonnen
        mål = len(df_s[df_s['IS_GOAL']])
        st.markdown(f"<h3 style='text-align: center;'>{valgt_spiller.upper()}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: grey;'>{mål} mål på {len(df_s)} skud</p>", unsafe_allow_html=True)
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
