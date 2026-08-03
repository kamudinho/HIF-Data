import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# --- CENTRAL DATA & MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, SEASON_LEAGUE_MAPPER, SEASONS, COMPETITIONS, COMPETITION_NAME
from data.utils.mapping import OPTA_EVENT_TYPES, OPTA_QUALIFIERS, get_action_label, har_qualifier
from data.players.player_mapping import player_mapping  
from utils.helpers import get_logo_img

# Snowflake database sti
DB = "KLUB_HVIDOVREIF.AXIS"

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

def draw_match_info_box(ax, scoring_team_logo, opp_team_logo, date_str, score_str, min_str):
    """Tegner info-boks ved mål-sekvenser"""
    if scoring_team_logo:
        ax_l1 = ax.inset_axes([0.02, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l1.imshow(scoring_team_logo); ax_l1.axis('off')
    ax.text(0.06, 0.10, "vs.", transform=ax.transAxes, fontsize=7, fontweight='bold', va='center')
    if opp_team_logo:
        ax_l2 = ax.inset_axes([0.10, 0.08, 0.05, 0.05], transform=ax.transAxes)
        ax_l2.imshow(opp_team_logo); ax_l2.axis('off')
    ax.text(0.03, 0.07, f"{date_str} | Stilling: {score_str} ({min_str}. min)", transform=ax.transAxes, fontsize=6, color='#444444', va='top')

def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn:
        st.warning("Kunne ikke oprette forbindelse til databasen.")
        st.stop()

    # --- SÆSON- OG HOLDVÆLGER I TOPPEN ---
    available_seasons = sorted(list(SEASONS.keys()), reverse=True)
    
    col_spacer_top, col_saeson, col_hold = st.columns([2.5, 1, 1])
    
    default_season_idx = available_seasons.index("2026/2027") if "2026/2027" in available_seasons else 0
    valgt_saeson = col_saeson.selectbox(
        "Vælg sæson", 
        available_seasons, 
        index=default_season_idx, 
        label_visibility="collapsed",
        key="saeson_select"
    )

    LIGA_IDS_LIST = []
    for comp_data in COMPETITIONS.values():
        if "wyid" in comp_data and comp_data["wyid"]:
            LIGA_IDS_LIST.append(str(comp_data["wyid"]))

    if valgt_saeson in SEASONS:
        for comp_key, uuid_val in SEASONS[valgt_saeson].items():
            if uuid_val and "dummy" not in str(uuid_val).lower():
                LIGA_IDS_LIST.append(str(uuid_val))

    LIGA_IDS = tuple(LIGA_IDS_LIST)
    liga_ids_sql = str(LIGA_IDS)

    allowed_team_names = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(COMPETITION_NAME, [])
    
    team_map = {}
    for team_name, info in TEAMS.items():
        if not allowed_team_names or team_name in allowed_team_names:
            if "opta_uuid" in info and info["opta_uuid"]:
                team_map[team_name] = info["opta_uuid"]

    if not team_map:
        team_map = {name: info["opta_uuid"] for name, info in TEAMS.items() if info.get("opta_uuid")}

    sorted_teams = sorted(list(team_map.keys()))
    default_index = sorted_teams.index("Hvidovre") if "Hvidovre" in sorted_teams else 0
    
    valgt_hold_navn = col_hold.selectbox(
        "Vælg hold", 
        sorted_teams, 
        index=default_index, 
        label_visibility="collapsed",
        key="hold_select"
    )
    valgt_uuid = team_map[valgt_hold_navn]
    hold_logo = get_logo_img(valgt_uuid)

    st.caption("Gennemgang af holdets målsekvenser (inkl. modstanderens dueller/clearinger i kampsekvensen).")

    # --- SQL HENTNING AF MÅLSEKVENSER (MED BÅDE HVIDOVRE OG MODSTANDERENS KAMP-AKTIONER) ---
    sql_seq = f"""
        WITH SeasonMatches AS (
            SELECT MATCH_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, 
                   MATCH_LOCALDATE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                   TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
        ),
        TargetGoals AS (
            SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN, SEQUENCEID, EVENT_OPTAUUID as G_EVENT_UUID
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_TYPEID = 16 AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
            AND MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM SeasonMatches)
        ),
        BaseMatchEvents AS (
            SELECT 
                e.*,
                tg.G_TIME as GOAL_TIMESTAMP,
                tg.SEQUENCEID as TARGET_SEQUENCEID,
                tg.G_MIN as GOAL_MIN,
                tg.G_EVENT_UUID,
                m.MATCH_LOCALDATE,
                m.CONTESTANTHOME_NAME,
                m.CONTESTANTAWAY_NAME,
                m.CONTESTANTHOME_OPTAUUID,
                m.CONTESTANTAWAY_OPTAUUID,
                m.TOTAL_HOME_SCORE,
                m.TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_EVENTS e
            JOIN TargetGoals tg 
                ON e.MATCH_OPTAUUID = tg.MATCH_OPTAUUID
            JOIN SeasonMatches m 
                ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            WHERE e.EVENT_TIMESTAMP <= tg.G_TIME
              AND e.EVENT_TIMESTAMP >= DATEADD('millisecond', -60000, tg.G_TIME)
        ),
        CornerCheck AS (
            SELECT MATCH_OPTAUUID, GOAL_TIMESTAMP, MIN(EVENT_TIMESTAMP) AS MIN_CORNER_TIME
            FROM BaseMatchEvents
            WHERE EVENT_TYPEID = 6
              AND EVENT_TIMESTAMP >= DATEADD('millisecond', -45000, GOAL_TIMESTAMP)
            GROUP BY MATCH_OPTAUUID, GOAL_TIMESTAMP
        ),
        DynamicWindowEvents AS (
            SELECT 
                b.*,
                COALESCE(c.MIN_CORNER_TIME, DATEADD('millisecond', -20000, b.GOAL_TIMESTAMP)) AS EFFECTIVE_START_TIME
            FROM BaseMatchEvents b
            LEFT JOIN CornerCheck c 
                ON b.MATCH_OPTAUUID = c.MATCH_OPTAUUID AND b.GOAL_TIMESTAMP = c.GOAL_TIMESTAMP
        ),
        FilteredTimeEvents AS (
            SELECT *
            FROM DynamicWindowEvents
            WHERE EVENT_TIMESTAMP >= EFFECTIVE_START_TIME
        ),
        RankedMatchEvents AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY MATCH_OPTAUUID, GOAL_TIMESTAMP 
                    ORDER BY EVENT_TIMESTAMP DESC
                ) as rn
            FROM FilteredTimeEvents
        ),
        FinalSelectedEvents AS (
            SELECT *
            FROM RankedMatchEvents
            WHERE rn <= 12
        ),
        EventQualifiers AS (
            SELECT 
                EVENT_OPTAUUID,
                LISTAGG(QUALIFIER_QID, ',') AS QUALIFIER_LIST
            FROM {DB}.OPTA_QUALIFIERS
            GROUP BY EVENT_OPTAUUID
        ),
        MatchRunningScores AS (
            SELECT 
                e.MATCH_OPTAUUID,
                e.EVENT_OPTAUUID as GOAL_EVENT_OPTAUUID,
                SUM(CASE WHEN e.EVENT_CONTESTANT_OPTAUUID = m.CONTESTANTHOME_OPTAUUID THEN 1 ELSE 0 END) 
                    OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_TIMESTAMP ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS CURRENT_HOME_SCORE,
                SUM(CASE WHEN e.EVENT_CONTESTANT_OPTAUUID = m.CONTESTANTAWAY_OPTAUUID THEN 1 ELSE 0 END) 
                    OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_TIMESTAMP ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS CURRENT_AWAY_SCORE
            FROM {DB}.OPTA_EVENTS e
            JOIN {DB}.OPTA_MATCHINFO m ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            WHERE e.EVENT_TYPEID = 16
        )
        SELECT 
            e.MATCH_OPTAUUID,
            e.SEQUENCEID,
            e.EVENT_TIMESTAMP,
            e.EVENT_TIMEMIN AS EVENT_MINUTE,
            e.PLAYER_OPTAUUID,
            e.PLAYER_NAME,
            e.EVENT_CONTESTANT_OPTAUUID,
            e.EVENT_TYPEID,
            CASE 
                WHEN e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' THEN e.EVENT_X 
                ELSE (100.0 - e.EVENT_X) 
            END as RAW_X,
            CASE 
                WHEN e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}' THEN e.EVENT_Y 
                ELSE (100.0 - e.EVENT_Y) 
            END as RAW_Y,
            e.GOAL_TIMESTAMP,
            e.G_EVENT_UUID AS GOAL_EVENT_OPTAUUID,
            e.GOAL_MIN,
            q.QUALIFIER_LIST,
            m.CONTESTANTHOME_NAME,
            m.CONTESTANTAWAY_NAME,
            m.CONTESTANTHOME_OPTAUUID,
            m.CONTESTANTAWAY_OPTAUUID,
            m.MATCH_LOCALDATE,
            m.TOTAL_HOME_SCORE AS FINAL_HOME_SCORE,
            m.TOTAL_AWAY_SCORE AS FINAL_AWAY_SCORE,
            COALESCE(rs.CURRENT_HOME_SCORE, 0) AS GOAL_HOME_SCORE,
            COALESCE(rs.CURRENT_AWAY_SCORE, 0) AS GOAL_AWAY_SCORE
        FROM FinalSelectedEvents e
        LEFT JOIN EventQualifiers q 
            ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN {DB}.OPTA_MATCHINFO m 
            ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        LEFT JOIN MatchRunningScores rs 
            ON e.G_EVENT_UUID = rs.GOAL_EVENT_OPTAUUID
        ORDER BY e.EVENT_TIMESTAMP ASC;
    """

    with st.spinner("Henter målsekvenser fra Snowflake..."):
        try:
            df_all = conn.query(sql_seq)
        except Exception as e:
            st.error(f"Fejl ved udførsel af SQL: {e}")
            st.stop()

    if df_all is None or df_all.empty:
        st.warning(f"Ingen målsekvenser fundet for {valgt_hold_navn} i sæson {valgt_saeson}.")
        return

    df_all.columns = [c.upper() for c in df_all.columns]

    # --- ROBUST OVERSKRIVNING AF NAVNE VED HJÆLP AF PLAYER_MAPPING ---
    def map_spiller_navn(row):
        p_uuid = row.get('PLAYER_OPTAUUID')
        if pd.notna(p_uuid) and str(p_uuid).strip() not in ["", "None", "nan"]:
            mapped_name = player_mapping.get_name_by_opta_uuid(p_uuid)
            if mapped_name and str(mapped_name).strip() not in ["", "Ukendt", "None", "nan"]:
                return str(mapped_name).strip()
                
        db_name = row.get('PLAYER_NAME')
        if pd.notna(db_name) and str(db_name).strip() not in ["", "None", "nan"]:
            return str(db_name).strip()
            
        return 'Ukendt'

    df_all['PLAYER_NAME'] = df_all.apply(map_spiller_navn, axis=1)

    df_all['AKTION'] = df_all.apply(get_action_label, axis=1)
    df_all['DETALJER'] = df_all['QUALIFIER_LIST'].apply(oversæt_qualifiers)

    maal_df = df_all[df_all['EVENT_TYPEID'].astype(str) == '16'].drop_duplicates(subset=['MATCH_OPTAUUID', 'GOAL_TIMESTAMP']).copy()

    opts = {}
    for _, r in maal_df.iterrows():
        seq_id = r['SEQUENCEID']
        m_uuid = r['MATCH_OPTAUUID']
        g_ts = r['GOAL_TIMESTAMP']
        key = f"{m_uuid}_{g_ts}_{seq_id}"

        dato_str = pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m')
        h_uuid = r['CONTESTANTHOME_OPTAUUID']
        a_uuid = r['CONTESTANTAWAY_OPTAUUID']
        opp_navn = r['CONTESTANTAWAY_NAME'] if h_uuid == valgt_uuid else r['CONTESTANTHOME_NAME']
        opp_uuid = a_uuid if h_uuid == valgt_uuid else h_uuid

        kamp_res = f"{int(r['FINAL_HOME_SCORE'])}-{int(r['FINAL_AWAY_SCORE'])}"

        h_maal = int(r['GOAL_HOME_SCORE'])
        a_maal = int(r['GOAL_AWAY_SCORE'])

        er_hjemmehold = (valgt_uuid == h_uuid)
        mål_stilling = f"{h_maal}-{a_maal}" if er_hjemmehold else f"{a_maal}-{h_maal}"

        raw_min = r['GOAL_MIN']
        minuttal = 1 if pd.isna(raw_min) else int(raw_min) + 1

        label_tekst = f"{dato_str}: {mål_stilling} ({minuttal}. min) vs. {opp_navn} ({kamp_res})"

        opts[key] = {
            'label': label_tekst,
            'match_id': m_uuid,
            'goal_ts': g_ts,
            'seq_id': seq_id,
            'opp_uuid': opp_uuid,
            'min': minuttal,
            'date': pd.to_datetime(r['MATCH_LOCALDATE']).strftime('%d/%m/%Y'),
            'score_str': kamp_res,
            'stilling_hjemme_ude': f"{h_maal}-{a_maal}"
        }

    if not opts:
        st.warning("Ingen målsekvenser matcher de valgte filtre.")
        return

    sk = st.selectbox("Vælg mål", list(opts.keys()), format_func=lambda x: opts[x]['label'])
    sd = opts[sk]

    tge = df_all[
        (df_all['MATCH_OPTAUUID'] == sd['match_id']) & 
        (df_all['GOAL_TIMESTAMP'] == sd['goal_ts'])
    ].sort_values('EVENT_TIMESTAMP').copy()

    # Fjern eventuelle fejlagtige målmands-registreringer ved det første hjørnespark (hvis modstanderens målmand fejlagtigt er sat på)
    if not tge.empty:
        for idx, row in tge.head(2).iterrows():
            if str(row['EVENT_CONTESTANT_OPTAUUID']) != str(valgt_uuid) and str(row.get('AKTION', '')).lower() in ['hjørnespark', 'corner']:
                # Ret konsekvent hold-id eller ryd aktionen hvis den fejlagtigt tilhører modstanderens målmand i starten
                tge.loc[idx, 'EVENT_CONTESTANT_OPTAUUID'] = valgt_uuid

    tge['sekvens_nr'] = range(1, len(tge) + 1)
    
    col_banen, col_tabel = st.columns([2.5, 1])

    with col_banen:
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#7f7f7f', line_zorder=2, linewidth=1.0)
        fig, ax = pitch.draw(figsize=(9, 4.5))

        sekvens_plot_df = tge.dropna(subset=['RAW_X', 'RAW_Y'])

        if not sekvens_plot_df.empty:
            if len(sekvens_plot_df) > 1:
                pitch.arrows(
                    sekvens_plot_df['RAW_X'].iloc[:-1], 
                    sekvens_plot_df['RAW_Y'].iloc[:-1],
                    sekvens_plot_df['RAW_X'].iloc[1:], 
                    sekvens_plot_df['RAW_Y'].iloc[1:], 
                    ax=ax, width=1.0, headwidth=2.5, color="#aaaaaa", alpha=0.8, zorder=3
                )

            for _, row in sekvens_plot_df.iterrows():
                r_x = row['RAW_X']
                r_y = row['RAW_Y']
                nr_str = str(row['sekvens_nr'])
                er_maal = (str(row['EVENT_TYPEID']) == '16')
                er_modstander = (str(row['EVENT_CONTESTANT_OPTAUUID']) != str(valgt_uuid))

                if er_maal:
                    prik_farve = '#df003b'
                    prik_str = 70
                    tekst_farve = '#333333'
                elif er_modstander:
                    prik_farve = '#999999'  # Grå cirkel til modstanderens clearinger/dueller
                    prik_str = 45
                    tekst_farve = '#777777'
                else:
                    prik_farve = 'black'
                    prik_str = 45
                    tekst_farve = '#333333'

                pitch.scatter(r_x, r_y, color=prik_farve, s=prik_str, ax=ax, zorder=4)

                ax.text(
                    r_x, r_y, nr_str,
                    fontsize=6.5, fontweight='bold', ha='center', va='center', color='white', zorder=5
                )

                navn = str(row.get('PLAYER_NAME', ''))
                if navn and navn != 'nan' and navn != 'Ukendt':
                    ax.text(
                        r_x, r_y - 2.5, navn,
                        fontsize=6, ha='center', va='top', color=tekst_farve, zorder=5
                    )

        opp_logo = get_logo_img(sd['opp_uuid'])
        draw_match_info_box(ax, hold_logo, opp_logo, sd['date'], sd['stilling_hjemme_ude'], sd['min'])

        st.pyplot(fig, use_container_width=True)

    with col_tabel:
        st.markdown("##### Aktioner i sekvensen")
        
        def get_final_label_t4(row):
            if 'AKTION' in row and pd.notna(row['AKTION']) and row['AKTION'] != "":
                return row['AKTION']
            label = get_action_label(row)
            return label if label else "Opbygning"

        tge['Aktion'] = tge.apply(get_final_label_t4, axis=1)
        
        vis_cols = ['sekvens_nr', 'PLAYER_NAME', 'Aktion']
        tabel_df = tge[vis_cols].rename(columns={
            'sekvens_nr': 'Nr.',
            'PLAYER_NAME': 'Spiller',
            'Aktion': 'Aktion'
        })
        st.dataframe(tabel_df, use_container_width=True, hide_index=True, height=380)
