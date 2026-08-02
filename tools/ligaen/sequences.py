import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# --- CENTRAL DATA & MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, SEASON_LEAGUE_MAPPER
from data.utils.mapping import OPTA_EVENT_TYPES, OPTA_QUALIFIERS, get_action_label, har_qualifier

# --- KONFIGURATION (HVIDOVRE-APP) ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASONNAME = "2026/2027"
TEAM_WYID = 7490
COMPETITION_WYID = (328,)
LIGA_IDS = "('2mb332vncy4450vu14paj8844', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"

def oversæt_qualifiers(qual_str):
    if not qual_str or pd.isna(qual_str):
        return ""
    q_ids = str(qual_str).split(",")
    tekster = []
    for qid in q_ids:
        qid_clean = qid.strip()
        if qid_clean.isdigit():
            q_int = int(qid_clean)
            if q_int in OPTA_QUALIFIERS:
                tekster.append(OPTA_QUALIFIERS[q_int])
    return ", ".join(tekster)

def vis_side(dp=None):
    st.caption("Gennemgang af holdets målsekvenser fra bolden vindes, til målet falder.")

    conn = _get_snowflake_conn()
    if not conn:
        st.warning("Kunne ikke oprette forbindelse til databasen.")
        st.stop()

    # Hent hold til dropdown baseret på TEAMS
    hold_liste = sorted(list(TEAMS.keys()))
    if "Hvidovre" in hold_liste:
        hold_liste.remove("Hvidovre")
        hold_liste.insert(0, "Hvidovre")

    # --- 2 KOLONNER PÅ SAMME LINJE: Hold og Målsekvens ---
    col_h, col_s = st.columns(2)
    
    with col_h:
        valgt_hold_navn = st.selectbox("Vælg hold", hold_liste, key="seq_valgt_hold")
    
    valgt_hold_data = TEAMS.get(valgt_hold_navn, {})
    team_opta_uuid = valgt_hold_data.get("opta_uuid")

    if not team_opta_uuid:
        st.error(f"Kunne ikke finde Opta UUID for holdet: {valgt_hold_navn}")
        st.stop()

    # --- SQL-FORESPØRGSEL ---
    sql_query = f"""
        WITH MatchIDs AS (
            SELECT DISTINCT MATCH_OPTAUUID 
            FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_NAME = '{SEASONNAME}'
              AND TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}
        ),
        GoalEvents AS (
            SELECT DISTINCT 
                e.SEQUENCEID, 
                e.MATCH_OPTAUUID,
                e.EVENT_TIMESTAMP as GOAL_TIMESTAMP
            FROM {DB}.OPTA_EVENTS e
            WHERE e.MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchIDs)
            AND e.EVENT_TYPEID = 16 
            AND e.EVENT_CONTESTANT_OPTAUUID = '{team_opta_uuid}'
        ),
        SequenceBounds AS (
            SELECT 
                g.SEQUENCEID,
                g.MATCH_OPTAUUID,
                g.GOAL_TIMESTAMP,
                MIN(e.EVENT_TIMESTAMP) AS SEQ_START_TIMESTAMP
            FROM GoalEvents g
            JOIN {DB}.OPTA_EVENTS e ON g.SEQUENCEID = e.SEQUENCEID AND g.MATCH_OPTAUUID = e.MATCH_OPTAUUID
            GROUP BY g.SEQUENCEID, g.MATCH_OPTAUUID, g.GOAL_TIMESTAMP
        ),
        FilteredEvents AS (
            SELECT e.*
            FROM {DB}.OPTA_EVENTS e
            JOIN SequenceBounds sb 
                ON e.SEQUENCEID = sb.SEQUENCEID 
                AND e.MATCH_OPTAUUID = sb.MATCH_OPTAUUID
            WHERE e.EVENT_TIMESTAMP >= sb.SEQ_START_TIMESTAMP 
              AND e.EVENT_TIMESTAMP <= sb.GOAL_TIMESTAMP
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
            e.EVENT_X as RAW_X,
            e.EVENT_Y as RAW_Y,
            q.QUALIFIER_LIST,
            m.CONTESTANTHOME_NAME,
            m.CONTESTANTAWAY_NAME,
            m.MATCH_TIMESTAMP,
            m.HOMESCORECURRENT,
            m.AWAYSCORECURRENT
        FROM FilteredEvents e
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
        with col_s:
            st.selectbox("Vælg målsekvens", ["Ingen sekvenser fundet"], key="seq_empty_dropdown")
        st.warning(f"Ingen målsekvenser fundet for {valgt_hold_navn} i sæson {SEASONNAME}.")
        return

    df_all.columns = [c.lower() for c in df_all.columns]
    df_all['kamp_label'] = df_all['contestanthome_name'] + " vs. " + df_all['contestantaway_name']
    
    # Oversæt event_typeid ved hjælp af central OPTA_EVENT_TYPES mapping
    df_all['aktion'] = df_all['event_typeid'].map(OPTA_EVENT_TYPES).fillna("Ukendt (" + df_all['event_typeid'].astype(str) + ")")
    df_all['detaljer'] = df_all['qualifier_list'].apply(oversæt_qualifiers)

    sekvens_ids = df_all['sequenceid'].unique()

    with col_s:
        valgt_seq = st.selectbox(
            "Vælg målsekvens", 
            sekvens_ids, 
            key="seq_main_dropdown",
            format_func=lambda x: f"ID: {x} ({df_all[df_all['sequenceid'] == x]['kamp_label'].iloc[0]})"
        )

    if valgt_seq:
        sekvens_df = df_all[df_all['sequenceid'] == valgt_seq].sort_values(by='event_timestamp').copy()
        
        maal_row = sekvens_df[sekvens_df['event_typeid'] == 16]
        målscorer = maal_row['player_name'].iloc[0] if not maal_row.empty else "Ukendt"
        kamp_navn = sekvens_df['kamp_label'].iloc[0]
        
        match_ts = sekvens_df['event_timestamp'].iloc[0] if 'match_timestamp' in sekvens_df.columns else ""
        dato_str = pd.to_datetime(match_ts).strftime('%d/%m/%Y') if pd.notna(match_ts) else ""

        # --- OPSETNING: BANEN TIL VENSTRE, TABELLEN TIL HØJRE ---
        col_banen, col_tabel = st.columns([2, 1])

        with col_banen:
            st.markdown("##### Sekvensopbygning på banen (fra bolden vindes)")
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#7f7f7f', line_zorder=2)
            fig, ax = pitch.draw(figsize=(8, 4.2))

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

            st.markdown(
                f"<div style='display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: #555; background-color: #fcfcfc; padding: 6px 10px; border-radius: 4px; border: 1px solid #eaeaea; margin-top: -5px;'>"
                f"<span><b>Målscorer:</b> {målscorer}</span>"
                f"<span><b>Kamp:</b> {kamp_navn}</span>"
                f"<span>{dato_str}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        with col_tabel:
            st.markdown("##### Aktioner i sekvensen")
            vis_cols = [c for c in ['player_name', 'aktion', 'detaljer'] if c in sekvens_df.columns]
            
            tabel_df = sekvens_df[vis_cols].rename(columns={
                'player_name': 'Spiller',
                'aktion': 'Aktion',
                'detaljer': 'Detaljer'
            })
            st.dataframe(tabel_df, use_container_width=True, hide_index=True, height=380)
