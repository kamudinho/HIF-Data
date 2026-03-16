import streamlit as st
import pandas as pd

HIF_OPTA_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}

    st.markdown("### 🏃 Fysisk Overblik (F53A Data)")

    # --- TRIN 1: METADATA ---
    @st.cache_data(ttl=600)
    def get_matches():
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
        st.warning("Ingen kampe fundet.")
        return

    # SIKRING: Konvertér til datetime hvis det ikke allerede er det
    df_matches['MATCH_DATE'] = pd.to_datetime(df_matches['MATCH_DATE'])

    # Nu virker .dt accessor
    df_matches['LABEL'] = df_matches['MATCH_DATE'].dt.strftime('%d/%m-%Y') + " (ID: " + df_matches['MATCH_SSIID'].str[:6] + ")"
    valgt_label = st.selectbox("Vælg Kamp:", df_matches['LABEL'].unique())
    m = df_matches[df_matches['LABEL'] == valgt_label].iloc[0]
    v_ssiid = m['MATCH_SSIID']

    # --- TRIN 2: TEAM DATA ---
    @st.cache_data(ttl=600)
    def get_team_stats(ssiid):
        # Vi bruger en f-string og sørger for at ssiid er en ren string
        q = f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM WHERE TRIM(MATCH_SSIID) = '{ssiid}'"
        return conn.query(q)

    df_teams = get_team_stats(v_ssiid)

    if not df_teams.empty:
        st.write("---")
        hif_team_id = m['HOME_SSIID'] if m['HOMEOPTA_UUID'] == HIF_OPTA_UUID else m['AWAY_SSIID']
        
        c1, c2 = st.columns(2)
        # Sørg for at vi kun itererer over unikke hold rækker
        for idx, row in df_teams.iterrows():
            is_hif = (str(row['TEAM_SSIID']) == str(hif_team_id))
            with (c1 if is_hif else c2):
                st.metric(
                    label=f"{row['TEAM_NAME']}", 
                    value=f"{row['TEAMDISTANCE']/1000:.2f} km"
                )

    # --- TRIN 3: PLAYER DATA ---
    @st.cache_data(ttl=300)
    def get_player_stats(ssiid):
        q = f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE TRIM(MATCH_SSIID) = '{ssiid}'"
        return conn.query(q)

    df_players = get_player_stats(v_ssiid)

    if not df_players.empty:
        st.write("---")
        df_players['DISPLAY_NAME'] = df_players['PLAYER_SSIID'].map(name_map).fillna(df_players['PLAYER_NAME'])
        
        # Hold vælger baseret på de navne der findes i TEAM tabellen
        team_names = df_teams['TEAM_NAME'].unique().tolist()
        valgt_hold_navn = st.radio("Vis spillere for:", team_names, horizontal=True)
        
        # Find ID for det valgte holdnavn
        t_id = df_teams[df_teams['TEAM_NAME'] == valgt_hold_navn]['TEAM_SSIID'].iloc[0]
        df_display = df_players[df_players['TEAM_SSIID'] == t_id].copy()

        if not df_display.empty:
            st.dataframe(
                df_display[['DISPLAY_NAME', 'JERSEY', 'DISTANCE', 'TOP_SPEED', 'SPRINTS']].sort_values('DISTANCE', ascending=False),
                column_config={
                    "DISTANCE": st.column_config.NumberColumn("Meter", format="%.0f"),
                    "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/h")
                },
                use_container_width=True, hide_index=True
            )
