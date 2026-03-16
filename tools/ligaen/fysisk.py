import streamlit as st
import pandas as pd

# Hvidovre Opta UUID til at finde kampene i metadata
HIF_OPTA_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}

    st.markdown("### 🏃 Fysisk Overblik (F53A Data)")

    # --- TRIN 1: METADATA (Find kampen) ---
    @st.cache_data(ttl=600)
    def get_matches():
        # Vi joiner den overordnede GAME metadata med din specifikke F53A_GAME tabel
        query = f"""
        SELECT 
            TRIM(g.MATCH_SSIID) as MATCH_SSIID,
            g.MATCH_DATE,
            g.HOME_SSIID,
            g.AWAY_SSIID,
            m.HOMEOPTA_UUID,
            m.AWAY_OPTAUUID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME g
        JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m ON TRIM(g.MATCH_SSIID) = TRIM(m.MATCH_SSIID)
        WHERE m.HOMEOPTA_UUID = '{HIF_OPTA_UUID}' OR m.AWAY_OPTAUUID = '{HIF_OPTA_UUID}'
        ORDER BY g.MATCH_DATE DESC
        """
        return conn.query(query)

    df_matches = get_matches()

    if df_matches.empty:
        st.warning("Ingen kampe fundet i F53A-tabellerne for Hvidovre.")
        return

    # Valg af kamp
    df_matches['LABEL'] = df_matches['MATCH_DATE'].dt.strftime('%d/%m-%Y') + " (ID: " + df_matches['MATCH_SSIID'].str[:6] + ")"
    valgt_label = st.selectbox("Vælg Kamp (Metadata):", df_matches['LABEL'].unique())
    m = df_matches[df_matches['LABEL'] == valgt_label].iloc[0]
    v_ssiid = m['MATCH_SSIID']

    # --- TRIN 2: TEAM DATA (Hold-statistik) ---
    @st.cache_data(ttl=600)
    def get_team_stats(ssiid):
        return conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM WHERE TRIM(MATCH_SSIID) = '{ssiid}'")

    df_teams = get_team_stats(v_ssiid)

    if not df_teams.empty:
        st.write("---")
        # Find Hvidovres række i team-tabellen
        hif_team_id = m['HOME_SSIID'] if m['HOMEOPTA_UUID'] == HIF_OPTA_UUID else m['AWAY_SSIID']
        
        c1, c2 = st.columns(2)
        for idx, row in df_teams.iterrows():
            is_hif = (str(row['TEAM_SSIID']) == str(hif_team_id))
            with (c1 if is_hif else c2):
                st.metric(
                    label=f"{'🏠' if is_hif else '🚌'} {row['TEAM_NAME']}", 
                    value=f"{row['TEAMDISTANCE']/1000:.2f} km",
                    delta="Hvidovre IF" if is_hif else "Modstander"
                )
                with st.expander("Team Fordeling"):
                    st.write(f"Sprints: {row['TEAMPERCENTDISTANCEHIGHSPEEDSPRINTING']:.1f}%")
                    st.write(f"Jogging: {row['TEAMPERCENTDISTANCEJOGGING']:.1f}%")
                    st.write(f"Walking: {row['TEAMPERCENTDISTANCEWALKING']:.1f}%")

    # --- TRIN 3: PLAYER DATA (Individuelle stats) ---
    @st.cache_data(ttl=300)
    def get_player_stats(ssiid):
        query = f"""
        SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER 
        WHERE TRIM(MATCH_SSIID) = '{ssiid}'
        """
        return conn.query(query)

    df_players = get_player_stats(v_ssiid)

    if not df_players.empty:
        st.write("---")
        # Mapper navne fra din CSV/dictionary
        df_players['DISPLAY_NAME'] = df_players['PLAYER_SSIID'].map(name_map).fillna(df_players['PLAYER_NAME'])
        
        # Filtrer på det hold man vil se
        valgt_hold_navn = st.radio("Vis spillere for:", df_teams['TEAM_NAME'].unique(), horizontal=True)
        t_id = df_teams[df_teams['TEAM_NAME'] == valgt_hold_navn]['TEAM_SSIID'].iloc[0]
        
        df_display = df_players[df_players['TEAM_SSIID'] == t_id].copy()

        # Metrics for top-performers
        p1, p2, p3 = st.columns(3)
        top_dist = df_display.loc[df_display['DISTANCE'].idxmax()]
        top_speed = df_display.loc[df_display['TOP_SPEED'].idxmax()]
        
        p1.metric("Længst", top_dist['DISPLAY_NAME'], f"{top_dist['DISTANCE']/1000:.2f} km")
        p2.metric("Hurtigst", top_speed['DISPLAY_NAME'], f"{top_speed['TOP_SPEED']:.1f} km/h")
        p3.metric("Sprints", int(df_display['SPRINTS'].sum()))

        # Tabelvisning
        st.dataframe(
            df_display[['DISPLAY_NAME', 'JERSEY', 'DISTANCE', 'TOP_SPEED', 'SPRINTS', 'SPEEDRUNS']].sort_values('DISTANCE', ascending=False),
            column_config={
                "DISPLAY_NAME": "Spiller",
                "JERSEY": "Nr.",
                "DISTANCE": st.column_config.NumberColumn("Meter", format="%.0f"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/h"),
                "SPRINTS": "Sprints",
                "SPEEDRUNS": "Speedruns"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.error("Kunne ikke finde spiller-data (F53A_GAME_PLAYER) for denne kamp.")
