import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# --- CENTRAL DATA & MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import SEASONS, COMPETITIONS, TEAMS, SEASON_LEAGUE_MAPPER

def vis_side():
    DB = "KLUB_HVIDOVREIF.AXIS"

    st.caption("Gennemgang af holdets målsekvenser baseret på centrale indstillinger og sekvensdata.")

    # --- DROPWODNS PÅ SAMME LINJE ---
    col_s, col_t, col_h = st.columns(3)
    
    with col_s:
        valgt_saeson = st.selectbox("Vælg sæson", list(SEASONS.keys()), index=0)
    with col_t:
        valgt_turnering = st.selectbox("Vælg turnering", list(SEASONS[valgt_saeson].keys()), index=0)

    tournament_opta_uuid = SEASONS[valgt_saeson][valgt_turnering]
    turnering_info = COMPETITIONS.get(valgt_turnering, {})
    competition_wyid = turnering_info.get("wyid")

    tilladte_hold_navne = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(valgt_turnering, list(TEAMS.keys()))
    
    hold_liste = sorted([h for h in tilladte_hold_navne if h in TEAMS])
    if "Hvidovre" in hold_liste:
        hold_liste.remove("Hvidovre")
        hold_liste.insert(0, "Hvidovre")

    with col_h:
        valgt_hold_navn = st.selectbox("Vælg hold", hold_liste)
    
    valgt_hold_data = TEAMS.get(valgt_hold_navn, {})
    team_opta_uuid = valgt_hold_data.get("opta_uuid")

    if not team_opta_uuid:
        st.error(f"Kunne ikke finde Opta UUID for holdet: {valgt_hold_navn}")
        st.stop()

    conn = _get_snowflake_conn()
    if not conn:
        st.warning("Kunne ikke oprette forbindelse til databasen.")
        st.stop()

    # --- SQL-FORESPØRGSEL ---
    sql_query = f"""
        WITH MatchIDs AS (
            SELECT DISTINCT MATCH_OPTAUUID 
            FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_opta_uuid}'
        ),
        GoalSequences AS (
            SELECT DISTINCT e.SEQUENCEID, e.MATCH_OPTAUUID
            FROM {DB}.OPTA_EVENTS e
            WHERE e.MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchIDs)
            AND e.EVENT_TYPEID = 16 
            AND e.EVENT_CONTESTANT_OPTAUUID = '{team_opta_uuid}'
        ),
        EventQualifiers AS (
            SELECT 
                EVENT_OPTAUUID,
                LISTAGG(QUALIFIER_QID, ',') AS QUALIFIER_LIST
            FROM {DB}.OPTA_QUALIFIERS
            GROUP BY EVENT_OPTAUUID
        )
        SELECT 
            e.MATCH_OPTAUUID,
            e.SEQUENCEID,
            e.EVENT_TIMESTAMP,
            e.PLAYER_NAME,
            e.EVENT_TYPEID,
            LAG(e.EVENT_X, 1) OVER (PARTITION BY e.SEQUENCEID ORDER BY e.EVENT_TIMESTAMP ASC) as PREV_X_1,
            LAG(e.EVENT_Y, 1) OVER (PARTITION BY e.SEQUENCEID ORDER BY e.EVENT_TIMESTAMP ASC) as PREV_Y_1,
            LAG(e.EVENT_X, 2) OVER (PARTITION BY e.SEQUENCEID ORDER BY e.EVENT_TIMESTAMP ASC) as PREV_X_2,
            LAG(e.EVENT_Y, 2) OVER (PARTITION BY e.SEQUENCEID ORDER BY e.EVENT_TIMESTAMP ASC) as PREV_Y_2,
            e.EVENT_X as RAW_X,
            e.EVENT_Y as RAW_Y,
            q.QUALIFIER_LIST,
            m.CONTESTANTHOME_NAME,
            m.CONTESTANTAWAY_NAME
        FROM {DB}.OPTA_EVENTS e
        INNER JOIN GoalSequences gs 
            ON e.SEQUENCEID = gs.SEQUENCEID 
            AND e.MATCH_OPTAUUID = gs.MATCH_OPTAUUID
        LEFT JOIN EventQualifiers q 
            ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN {DB}.OPTA_MATCHINFO m 
            ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        ORDER BY e.SEQUENCEID, e.EVENT_TIMESTAMP ASC;
    """

    with st.spinner("Henter målsekvenser fra Snowflake..."):
        try:
            df_all = conn.query(sql_query)
        except Exception as e:
            st.error(f"Fejl ved udførsel af SQL: {e}")
            st.stop()

    if df_all is None or df_all.empty:
        st.warning(f"Ingen målsekvenser fundet for {valgt_hold_navn} i {valgt_turnering} ({valgt_saeson}).")
        st.stop()

    df_all.columns = [c.lower() for c in df_all.columns]
    df_all['kamp_label'] = df_all['contestanthome_name'] + " vs. " + df_all['contestantaway_name']
    sekvens_ids = df_all['sequenceid'].unique()

    st.markdown("---")
    
    col_sel, col_info = st.columns([2, 1])
    with col_sel:
        valgt_seq = st.selectbox(
            "Vælg målsekvens", 
            sekvens_ids, 
            format_func=lambda x: f"Sekvens ID: {x} (Kamp: {df_all[df_all['sequenceid'] == x]['kamp_label'].iloc[0]})"
        )

    if valgt_seq:
        sekvens_df = df_all[df_all['sequenceid'] == valgt_seq].sort_values(by='event_timestamp').copy()
        
        maal_row = sekvens_df[sekvens_df['event_typeid'] == 16]
        målscorer = maal_row['player_name'].iloc[0] if not maal_row.empty else "Ukendt"
        kamp_navn = sekvens_df['kamp_label'].iloc[0]

        with col_info:
            st.metric("Målscorer", str(målscorer))
            st.metric("Kamp", kamp_navn)

        st.markdown("---")

        # --- OPSETNING: BANEN TIL VENSTRE, TABELLEN TIL HØJRE ---
        col_banen, col_tabel = st.columns([1.2, 1])

        with col_banen:
            st.markdown("### Sekvensopbygning på banen")
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#7f7f7f', line_zorder=2)
            fig, ax = pitch.draw(figsize=(8, 5))

            sekvens_plot_df = sekvens_df.dropna(subset=['raw_x', 'raw_y'])

            if not sekvens_plot_df.empty:
                if len(sekvens_plot_df) > 1:
                    pitch.arrows(
                        sekvens_plot_df['raw_x'].iloc[:-1], 
                        sekvens_plot_df['raw_y'].iloc[:-1],
                        sekvens_plot_df['raw_x'].iloc[1:], 
                        sekvens_plot_df['raw_y'].iloc[1:], 
                        ax=ax, width=1.5, headwidth=3, color="#cccccc", alpha=0.8, zorder=3
                    )

                pitch.scatter(
                    sekvens_plot_df['raw_x'], sekvens_plot_df['raw_y'],
                    color='black', s=80, ax=ax, zorder=4
                )

                for _, row in sekvens_plot_df.iterrows():
                    if pd.notna(row.get('player_name')) and pd.notna(row.get('raw_x')):
                        if row.get('event_typeid') != 16:
                            ax.text(
                                row['raw_x'], row['raw_y'] + 3, row['player_name'],
                                fontsize=8, ha='center', va='bottom', color='black', zorder=5
                            )

                if not maal_row.empty:
                    m_x = maal_row['raw_x'].iloc[0]
                    m_y = maal_row['raw_y'].iloc[0]
                    m_navn = maal_row['player_name'].iloc[0]

                    pitch.scatter(
                        m_x, m_y,
                        color='#df003b', s=120, ax=ax, zorder=6
                    )
                    ax.text(
                        m_x, m_y + 3, m_navn,
                        fontsize=8, fontweight='bold', ha='center', va='bottom', color='black', zorder=7
                    )

            st.pyplot(fig, use_container_width=True)

        with col_tabel:
            st.markdown("### Aktioner i sekvensen")
            vis_cols = [c for c in ['event_timestamp', 'player_name', 'event_typeid', 'raw_x', 'raw_y'] if c in sekvens_df.columns]
            st.dataframe(sekvens_df[vis_cols], use_container_width=True, hide_index=True, height=380)
