import streamlit as st
import pandas as pd

HIF_OPTA_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

def vis_side(conn, name_map=None):
    if name_map is None:
        name_map = {}

    st.markdown("### 🏃 Fysisk Overblik")

    @st.cache_data(ttl=600)
    def get_matches():
        # Vi fjerner YEAR filteret helt for at undgå fejl mellem tal/strenge,
        # og sorterer i stedet bare efter STARTTIME for at få de nyeste.
        query = f"""
        SELECT 
            TRIM(MATCH_SSIID) as MATCH_SSIID,
            STARTTIME,
            HOME_SSIID,
            AWAY_SSIID,
            HOMEOPTA_UUID,
            AWAY_OPTAUUID,
            HOME_SCORE,
            AWAY_SCORE,
            YEAR
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA
        WHERE (HOMEOPTA_UUID = '{HIF_OPTA_UUID}' OR AWAY_OPTAUUID = '{HIF_OPTA_UUID}')
        ORDER BY STARTTIME DESC
        LIMIT 25
        """
        return conn.query(query)
    
    df_matches = get_matches()

    if df_matches.empty:
        st.warning("Ingen kampe fundet for Hvidovre i 2025/2026.")
        return

    # Konvertér STARTTIME til datetime (vigtigt for din .dt fejl tidligere)
    df_matches['DATE_TIME'] = pd.to_datetime(df_matches['DATE_TIME'])

    # Lav en pæn label
    df_matches['LABEL'] = df_matches['DATE_TIME'].dt.strftime('%d/%m-%Y') + " (ID: " + df_matches['MATCH_SSIID'].str[:6] + ")"
    
    valgt_label = st.selectbox("Vælg Kamp:", df_matches['LABEL'].unique())
    m = df_matches[df_matches['LABEL'] == valgt_label].iloc[0]
    v_ssiid = m['MATCH_SSIID']

    # --- TRIN 2: TEAM DATA ---
    @st.cache_data(ttl=600)
    def get_team_stats(ssiid):
        return conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_TEAM WHERE TRIM(MATCH_SSIID) = '{ssiid}'")

    df_teams = get_team_stats(v_ssiid)

    if df_teams.empty:
        st.info("Metadata fundet, men de fysiske hold-statistikker (F53A) er ikke klar endnu.")
        return

    # --- TRIN 3: PLAYER DATA ---
    @st.cache_data(ttl=300)
    def get_player_stats(ssiid):
        return conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_F53A_GAME_PLAYER WHERE TRIM(MATCH_SSIID) = '{ssiid}'")

    df_players = get_player_stats(v_ssiid)

    if not df_players.empty:
        st.write("---")
        # Navne-mapning
        df_players['DISPLAY_NAME'] = df_players['PLAYER_SSIID'].map(name_map).fillna(df_players['PLAYER_NAME'])
        
        # Find ud af hvilket SSIID der er Hvidovre
        hif_team_id = m['HOME_SSIID'] if m['HOMEOPTA_UUID'] == HIF_OPTA_UUID else m['AWAY_SSIID']
        
        # Radio buttons baseret på de faktiske navne i TEAM tabellen
        team_names = df_teams['TEAM_NAME'].unique().tolist()
        valgt_hold_navn = st.radio("Vis spillere for:", team_names, horizontal=True)
        
        t_id = df_teams[df_teams['TEAM_NAME'] == valgt_hold_navn]['TEAM_SSIID'].iloc[0]
        df_display = df_players[df_players['TEAM_SSIID'] == t_id].copy()

        st.dataframe(
            df_display[['DISPLAY_NAME', 'DISTANCE', 'TOP_SPEED', 'SPRINTS']].sort_values('DISTANCE', ascending=False),
            column_config={
                "DISTANCE": st.column_config.NumberColumn("Meter", format="%.0f"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/h")
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.error("Spiller-data er endnu ikke tilgængelig for denne kamp.")
