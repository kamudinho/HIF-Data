import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# --- CENTRAL DATA & MAPPING ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, SEASON_LEAGUE_MAPPER, SEASONS, COMPETITIONS, COMPETITION_NAME
from data.utils.mapping import OPTA_EVENT_TYPES, OPTA_QUALIFIERS, get_action_label, har_qualifier
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

def draw_match_info_box(ax, hold_logo, opp_logo, sd['date'], sd['stilling_hjemme_ude'], sd['min'])
    """Tegner info-boks med logoer pænt ved siden af hinanden i venstre side"""
    if scoring_team_logo:
        ax_l1 = ax.inset_axes([0.02, 0.08, 0.04, 0.04], transform=ax.transAxes)
        ax_l1.imshow(scoring_team_logo); ax_l1.axis('off')
        
    ax.text(0.068, 0.10, "vs.", transform=ax.transAxes, fontsize=8, fontweight='bold', va='center', ha='center', color='#333333')
    
    if opp_team_logo:
        ax_l2 = ax.inset_axes([0.082, 0.08, 0.04, 0.04], transform=ax.transAxes)
        ax_l2.imshow(opp_team_logo); ax_l2.axis('off')
        
    ax.text(0.02, 0.035, f"{date_str} | Stilling: {score_str} ({min_str}. min)", transform=ax.transAxes, fontsize=8, color='#444444', va='bottom', ha='left')

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

    st.caption("Gennemgang af holdets målsekvenser")

    # --- SQL HENTNING AF MÅLSEKVENSER ---
    sql_seq = f"""
        WITH SeasonMatches AS (
            SELECT MATCH_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, 
                   MATCH_LOCALDATE, CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                   TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
            FROM {DB}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID IN {liga_ids_sql}
        ),
        TargetGoals AS (
            SELECT MATCH_OPTAUUID, EVENT_TIMESTAMP as G_TIME, EVENT_TIMEMIN as G_MIN, SEQUENCEID
            FROM {DB}.OPTA_EVENTS 
            WHERE EVENT_TYPEID = 16 AND EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
            AND MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM SeasonMatches)
        ),
        RankedMatchEvents AS (
            SELECT 
                e.*,
                tg.G_TIME as GOAL_TIMESTAMP,
                tg.SEQUENCEID as TARGET_SEQUENCEID,
                tg.G_MIN as GOAL_MIN,
                m.MATCH_LOCALDATE,
                m.CONTESTANTHOME_NAME,
                m.CONTESTANTAWAY_NAME,
                m.CONTESTANTHOME_OPTAUUID,
                m.CONTESTANTAWAY_OPTAUUID,
                m.TOTAL_HOME_SCORE,
                m.TOTAL_AWAY_SCORE,
                ROW_NUMBER() OVER (
                    PARTITION BY e.MATCH_OPTAUUID, tg.G_TIME 
                    ORDER BY e.EVENT_TIMESTAMP DESC
                ) as rn
            FROM {DB}.OPTA_EVENTS e
            JOIN TargetGoals tg 
                ON e.MATCH_OPTAUUID = tg.MATCH_OPTAUUID
            JOIN SeasonMatches m 
                ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
            WHERE e.EVENT_TIMESTAMP <= tg.G_TIME
              AND e.EVENT_TIMESTAMP >= DATEADD('millisecond', -20000, tg.G_TIME)
              AND e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
        ),
        FilteredEvents AS (
            SELECT *
            FROM RankedMatchEvents
            WHERE rn <= 7
        ),
        EventQualifiers AS (
            SELECT 
                EVENT_OPTAUUID,
                LISTAGG(QUALIFIER_QID, ',') AS QUALIFIER_LIST
            FROM {DB}.OPTA_QUALIFIERS
            GROUP BY EVENT_OPTAUUID
        ),
        PlayerNames AS (
            SELECT DISTINCT PLAYER_OPTAUUID, TRIM(FIRST_NAME) || ' ' || TRIM(LAST_NAME) as P_NAME
            FROM {DB}.OPTA_MATCH_LINEUPS
            WHERE FIRST_NAME IS NOT NULL
        )
        SELECT 
            e.MATCH_OPTAUUID,
            e.TARGET_SEQUENCEID as SEQUENCEID,
            e.EVENT_TIMESTAMP,
            e.GOAL_MIN,
            COALESCE(pn.P_NAME, 'Ukendt') as PLAYER_NAME,
            e.EVENT_TYPEID,
            e.EVENT_X as RAW_X,
            e.EVENT_Y as RAW_Y,
            e.EVENT_CONTESTANT_OPTAUUID,
            q.QUALIFIER_LIST,
            e.CONTESTANTHOME_NAME,
            e.CONTESTANTAWAY_NAME,
            e.MATCH_LOCALDATE,
            e.TOTAL_HOME_SCORE,
            e.TOTAL_AWAY_SCORE,
            e.CONTESTANTHOME_OPTAUUID,
            e.CONTESTANTAWAY_OPTAUUID,
            e.GOAL_TIMESTAMP
        FROM FilteredEvents e
        LEFT JOIN EventQualifiers q 
            ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN PlayerNames pn 
            ON e.PLAYER_OPTAUUID = pn.PLAYER_OPTAUUID
        ORDER BY e.MATCH_LOCALDATE DESC, e.GOAL_TIMESTAMP DESC, e.EVENT_TIMESTAMP ASC;
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
    df_all['AKTION'] = df_all.apply(get_action_label, axis=1)
    df_all['DETALJER'] = df_all['QUALIFIER_LIST'].apply(oversæt_qualifiers)

    match_uuids = tuple(df_all['MATCH_OPTAUUID'].unique())
    match_uuid_str = f"('{match_uuids[0]}')" if len(match_uuids) == 1 else str(match_uuids)

    sql_alle_maal = f"""
        SELECT 
            MATCH_OPTAUUID,
            EVENT_TIMESTAMP,
            EVENT_CONTESTANT_OPTAUUID,
            SEQUENCEID
        FROM {DB}.OPTA_EVENTS
        WHERE MATCH_OPTAUUID IN {match_uuid_str}
          AND EVENT_TYPEID = 16
        ORDER BY EVENT_TIMESTAMP ASC;
    """
    try:
        alle_maal_df = conn.query(sql_alle_maal)
        if alle_maal_df is not None and not alle_maal_df.empty:
            alle_maal_df.columns = [c.lower() for c in alle_maal_df.columns]
        else:
            alle_maal_df = pd.DataFrame()
    except Exception:
        alle_maal_df = pd.DataFrame()

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

        kamp_res = f"{int(r['TOTAL_HOME_SCORE'])}-{int(r['TOTAL_AWAY_SCORE'])}"

        h_maal = 0
        a_maal = 0
        if not alle_maal_df.empty:
            kamp_alle_maal = alle_maal_df[alle_maal_df['match_optauuid'] == m_uuid].sort_values('event_timestamp')
            for _, sub_m in kamp_alle_maal.iterrows():
                is_home_goal = (sub_m['event_contestant_optauuid'] == h_uuid)
                if is_home_goal:
                    h_maal += 1
                else:
                    a_maal += 1
                if sub_m['sequenceid'] == seq_id or sub_m['event_timestamp'] >= g_ts:
                    break
        
        if h_maal == 0 and a_maal == 0:
            er_hjemme = (valgt_uuid == h_uuid)
            h_maal = 1 if er_hjemme else 0
            a_maal = 0 if er_hjemme else 1

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
        (df_all['SEQUENCEID'] == sd['seq_id'])
    ].sort_values('EVENT_TIMESTAMP').copy()

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

                prik_farve = '#df003b' if er_maal else 'black'
                prik_str = 70 if er_maal else 45

                pitch.scatter(r_x, r_y, color=prik_farve, s=prik_str, ax=ax, zorder=4)

                ax.text(
                    r_x, r_y, nr_str,
                    fontsize=6.5, fontweight='bold', ha='center', va='center', color='white', zorder=5
                )

                navn = str(row.get('PLAYER_NAME', ''))
                if navn and navn != 'nan':
                    ax.text(
                        r_x, r_y - 2.5, navn,
                        fontsize=6, ha='center', va='top', color='#333333', zorder=5
                    )

        # Brug af den korrekte draw_match_info_box
        opp_logo = get_logo_img(sd['opp_uuid'])
        draw_match_info_box(pitch, ax, hold_logo, opp_logo, sd['date'], sd['stilling_hjemme_ude'], sd['min'])

        st.pyplot(fig, use_container_width=True)

    with col_tabel:
        st.markdown("##### Aktioner i sekvensen")
        
        def get_final_label_t4(row):
            if str(row['EVENT_TYPEID']) == "16" and "9" in row.get('qual_list', []):
                return "STRAFFESPARK"
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
