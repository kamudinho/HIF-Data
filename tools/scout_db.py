import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def rens_id(val):
    if pd.isna(val) or val == "": return ""
    return str(val).split('.')[0].strip()

def rens_metrik(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        v = int(float(str(val).replace(',', '.')))
        return max(0, min(v, 6)) # Sikrer værdi mellem 0 og 6
    except: return 0

@st.dialog("Spillerprofil", width="large")
def vis_profil(p_data, full_df, career_df):
    clean_p_id = rens_id(p_data.get('PLAYER_WYID', ''))
    historik = full_df[full_df['PLAYER_WYID'] == clean_p_id].copy()
    
    # Header
    h1, h2 = st.columns([1, 4])
    with h1:
        st.image(p_data.get('VIS_BILLEDE', "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"), width=115)
    with h2:
        st.markdown(f"## {p_data.get('NAVN', 'Ukendt Spiller')}")
        st.info(f"**{p_data.get('KLUB', 'Ukendt Klub')}** | {p_data.get('POSITION_VISNING', 'N/A')} | Snit: {p_data.get('RATING_AVG', 0)}")

    t1, t2, t3, t4, t5 = st.tabs(["Seneste", "Historik", "Udvikling", "Stats", "Radar"])
    
    with t1:
        metrics = [("Teknik", "TEKNIK"), ("Fart", "FART"), ("Aggresivitet", "AGGRESIVITET"), ("Attitude", "ATTITUDE"),
                   ("Udholdenhed", "UDHOLDENHED"), ("Leder", "LEDEREGENSKABER"), ("Beslutning", "BESLUTSOMHED"), ("Intelligens", "SPILINTELLIGENS")]
        m_cols = st.columns(4)
        for i, (label, col) in enumerate(metrics):
            val = rens_metrik(p_data.get(col, 0))
            m_cols[i % 4].metric(label, val)
        
        st.divider()
        c1, c2 = st.columns(2)
        c1.success(f"**Styrker:**\n\n{p_data.get('STYRKER', '-')}")
        c2.info(f"**Vurdering:**\n\n{p_data.get('VURDERING', '-')}")

    with t4:
        if career_df is not None and not career_df.empty:
            df_p = career_df[career_df['PLAYER_WYID'] == clean_p_id].copy()
            if not df_p.empty:
                mapping = {'SEASONNAME': 'Sæson', 'TEAMNAME': 'Klub', 'COMPETITIONNAME': 'Turnering', 'APPEARANCES': 'Kampe', 'GOAL': 'Mål'}
                show_cols = [c for c in mapping.keys() if c in df_p.columns]
                st.dataframe(df_p[show_cols].rename(columns=mapping), use_container_width=True, hide_index=True)
            else:
                st.write("Ingen stats fundet i Snowflake.")

    with t5:
        cats = ['Beslutning', 'Fart', 'Aggresivitet', 'Attitude', 'Udholdenhed', 'Leder', 'Teknik', 'Intelligens']
        keys = ['BESLUTSOMHED', 'FART', 'AGGRESIVITET', 'ATTITUDE', 'UDHOLDENHED', 'LEDEREGENSKABER', 'TEKNIK', 'SPILINTELLIGENS']
        vals = [rens_metrik(p_data.get(k, 0)) for k in keys]
        
        fig = go.Figure(go.Scatterpolar(r=vals + [vals[0]], theta=cats + [cats[0]], fill='toself', fillcolor='rgba(223,0,59,0.3)', line=dict(color='#df003b')))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 6])), showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

def vis_side(scout_df, players_local, sql_players, career_df):
    if scout_df is None or scout_df.empty:
        st.info("Ingen data i scouting_db.csv")
        return

    df = scout_df.copy()
    df['PLAYER_WYID'] = df['PLAYER_WYID'].apply(rens_id)
    
    # Billed-map
    img_map = {}
    if sql_players is not None and not sql_players.empty:
        img_map = dict(zip(sql_players['PLAYER_WYID'], sql_players['IMAGEDATAURL']))

    # Forbered visning
    df['VIS_BILLEDE'] = df['PLAYER_WYID'].apply(lambda x: img_map.get(x, "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"))
    
    # Tag kun nyeste rapport per spiller
    f_df = df.sort_values('DATO', ascending=False).drop_duplicates('PLAYER_WYID')
    
    # Tabel-konfiguration
    col_map = {'VIS_BILLEDE': ' ', 'NAVN': 'Navn', 'KLUB': 'Klub', 'RATING_AVG': 'Rating', 'SCOUT': 'Scout'}
    disp_df = f_df[list(col_map.keys())].rename(columns=col_map)
    
    event = st.dataframe(
        disp_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        height=350,
        column_config={" ": st.column_config.ImageColumn(" ")}
    )

    if len(event.selection.rows) > 0:
        idx = event.selection.rows[0]
        spiller_data = f_df.iloc[idx]
        vis_profil(spiller_data, df, career_df)
