import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# --- CENTRAL DATA & MAPPING (KUN 1. DIVISION / NORDICBET LIGA) ---
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS, SEASON_LEAGUE_MAPPER
from data.utils.mapping import OPTA_EVENT_TYPES, OPTA_QUALIFIERS, get_action_label, har_qualifier

# --- KONFIGURATION (HVIDOVRE-APP) ---
DB = "KLUB_HVIDOVREIF.AXIS"
SEASONNAME = "2026/2027"
TEAM_WYID = 7490
COMPETITION_WYID = (328,)
COMP_MAP = { 335: "Superliga", 328: "NordicBet Liga", 329: "2. division", 43319: "3. division", 331: "Oddset Pokalen", 1305: "U19 Ligaen" }
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
    st.caption("Gennemgang af holdets målsekvenser fra bolden vindes, til målet falder (kun NordicBet Liga).")

    conn = _get_snowflake_conn()
    if not conn:
        st.warning("Kunne ikke oprette forbindelse til databasen.")
        st.stop()

    hold_liste = sorted(list(TEAMS.keys()))
    if "Hvidovre" in hold_liste:
        hold_liste.remove("Hvidovre")
        hold_liste.insert(0, "Hvidovre")

    col_h, col_s = st.columns(2)
    
    with col_h:
        valgt_hold_navn = st.selectbox("Vælg hold", hold_liste, key="seq_valgt_hold")
    
    valgt_hold_data = TEAMS.get(valgt_hold_navn, {})
    team_opta_uuid = valgt_hold_data.get("opta_uuid")

    if not team_opta_uuid:
        st.error(f"Kunne ikke finde Opta UUID for holdet: {valgt_hold_navn}")
        st.stop()

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
        RankedMatchEvents AS (
            SELECT 
                e.*,
                g.GOAL_TIMESTAMP,
                g.SEQUENCEID as TARGET_SEQUENCEID,
                ROW_NUMBER() OVER (
                    PARTITION BY e.MATCH_OPTAUUID, g.GOAL_TIMESTAMP 
                    ORDER BY e.EVENT_TIMESTAMP DESC
                ) as rn
            FROM {DB}.OPTA_EVENTS e
            JOIN GoalEvents g 
                ON e.MATCH_OPTAUUID = g.MATCH_OPTAUUID
            WHERE e.EVENT_TIMESTAMP <= g.GOAL_TIMESTAMP
              AND e.EVENT_TIMESTAMP >= DATEADD('millisecond', -20000, g.GOAL_TIMESTAMP)
              AND e.EVENT_CONTESTANT_OPTAUUID = '{team_opta_uuid}'
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
        )
        SELECT 
            e.MATCH_OPTAUUID,
            e.TARGET_SEQUENCEID as SEQUENCEID,
            e.EVENT_TIMESTAMP,
            e.PLAYER_NAME,
            e.EVENT_TYPEID,
            e.EVENT_X as RAW_X,
            e.EVENT_Y as RAW_Y,
            e.EVENT_CONTESTANT_OPTAUUID,
            q.QUALIFIER_LIST,
            m.CONTESTANTHOME_NAME,
            m.CONTESTANTAWAY_NAME,
            m.MATCH_DATE_FULL,
            m.TOTAL_HOME_SCORE AS FINAL_HOME_SCORE,
            m.TOTAL_AWAY_SCORE AS FINAL_AWAY_SCORE,
            m.CONTESTANTHOME_OPTAUUID
        FROM FilteredEvents e
        LEFT JOIN EventQualifiers q 
            ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN {DB}.OPTA_MATCHINFO m 
            ON e.MATCH_OPTAUUID = m.MATCH_OPTAUUID
        ORDER BY m.MATCH_DATE_FULL ASC, e.EVENT_TIMESTAMP ASC;
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

    # Klargør kolonner til get_action_label
    df_all.columns = [c.upper() for c in df_all.columns]
    df_all['QUAL_LIST'] = df_all['QUALIFIER_LIST']
    df_all['AKTION'] = df_all.apply(get_action_label, axis=1)
    df_all['DETALJER'] = df_all['QUALIFIER_LIST'].apply(oversæt_qualifiers)

    # Filtrer hændelser fra, hvor aktionen returnerer None (ukendte/uinteressante hændelser)
    df_all = df_all[df_all['AKTION'].notna()].copy()

    # Gør kolonnenavnene små igen til resten af Streamlit-siden
    df_all.columns = [c.lower() for c in df_all.columns]

    if df_all.empty:
        st.warning("Ingen gyldige aktioner fundet efter filtrering.")
        return

    unikke_kampe = df_all[['match_optauuid', 'match_date_full', 'contestanthome_name', 'contestantaway_name', 'contestanthome_optauuid']].drop_duplicates()
    unikke_kampe = unikke_kampe.sort_values(by='match_date_full').reset_index(drop=True)
    unikke_kampe['kamp_nummer'] = range(1, len(unikke_kampe) + 1)
    
    kamp_nr_dict = dict(zip(unikke_kampe['match_optauuid'], unikke_kampe['kamp_nummer']))
    df_all['kamp_nummer'] = df_all['match_optauuid'].map(kamp_nr_dict)

    maal_df = df_all[df_all['event_typeid'].astype(str) == '16'].copy()
    maal_df = maal_df.sort_values(by=['match_date_full', 'event_timestamp']).drop_duplicates(subset=['sequenceid'])

    dropdown_data = []

    for _, m_row in maal_df.iterrows():
        seq_id = m_row['sequenceid']
        m_uuid = m_row['match_optauuid']
        k_nr = m_row['kamp_nummer']
        
        home_name = m_row['contestanthome_name']
        away_name = m_row['contestantaway_name']
        home_uuid = m_row['contestanthome_optauuid']
        
        er_hjemmehold = (team_opta_uuid == home_uuid)
        modstander = away_name if er_hjemmehold else home_name

        kamp_alle_maal = maal_df[maal_df['match_optauuid'] == m_uuid].sort_values('event_timestamp')
        
        h_maal = 0
        a_maal = 0
        for _, sub_m in kamp_alle_maal.iterrows():
            is_home_goal = (sub_m['event_contestant_optauuid'] == home_uuid)
            if is_home_goal:
                h_maal += 1
            else:
                a_maal += 1
                
            if sub_m['sequenceid'] == seq_id:
                break

        if er_hjemmehold:
            aktuel_stilling = f"{h_maal}-{a_maal}"
        else:
            aktuel_stilling = f"{a_maal}-{h_maal}"

        f_home = int(m_row['final_home_score']) if pd.notna(m_row.get('final_home_score')) else 0
        f_away = int(m_row['final_away_score']) if pd.notna(m_row.get('final_away_score')) else 0
        slut_res = f"{f_home}-{f_away}" if er_hjemmehold else f"{f_away}-{f_home}"

        label_tekst = f"Kamp {k_nr}: {aktuel_stilling} vs. {modstander} ({slut_res})"
        
        dropdown_data.append({
            'sequenceid': seq_id,
            'label': label_tekst,
            'kamp_nr': k_nr,
            'modstander': modstander,
            'aktuel_stilling': aktuel_stilling,
            'slut_res': slut_res,
            'kamp_navn': f"{home_name} vs. {away_name}",
            'dato': pd.to_datetime(m_row['match_date_full']).strftime('%d/%m/%Y') if pd.notna(m_row['match_date_full']) else ""
        })

    if not dropdown_data:
        st.warning("Ingen målsekvenser matcher de valgte filtre.")
        return

    dropdown_df = pd.DataFrame(dropdown_data)
    sekvens_ids = dropdown_df['sequenceid'].tolist()

    with col_s:
        valgt_seq = st.selectbox(
            "Vælg målsekvens", 
            sekvens_ids, 
            key="seq_main_dropdown",
            format_func=lambda x: dropdown_df[dropdown_df['sequenceid'] == x]['label'].iloc[0]
        )

    if valgt_seq:
        sekvens_df = df_all[df_all['sequenceid'] == valgt_seq].sort_values(by='event_timestamp').copy()
        sekvens_df['sekvens_nr'] = range(1, len(sekvens_df) + 1)
        
        info_row = dropdown_df[dropdown_df['sequenceid'] == valgt_seq].iloc[0]
        maal_row = sekvens_df[sekvens_df['event_typeid'].astype(str) == '16']
        målscorer = maal_row['player_name'].iloc[0] if not maal_row.empty else "Ukendt"

        col_banen, col_tabel = st.columns([2, 1])

        with col_banen:
            st.markdown(f"##### Kamp {info_row['kamp_nr']} ({info_row['aktuel_stilling']} vs. {info_row['modstander']}): Sekvensopbygning")
            
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#7f7f7f', line_zorder=2, linewidth=1.0)
            fig, ax = pitch.draw(figsize=(9, 4.5))

            sekvens_plot_df = sekvens_df.dropna(subset=['raw_x', 'raw_y'])

            if not sekvens_plot_df.empty:
                if len(sekvens_plot_df) > 1:
                    pitch.arrows(
                        sekvens_plot_df['raw_x'].iloc[:-1], 
                        sekvens_plot_df['raw_y'].iloc[:-1],
                        sekvens_plot_df['raw_x'].iloc[1:], 
                        sekvens_plot_df['raw_y'].iloc[1:], 
                        ax=ax, width=1.0, headwidth=2.5, color="#aaaaaa", alpha=0.8, zorder=3
                    )

                for _, row in sekvens_plot_df.iterrows():
                    r_x = row['raw_x']
                    r_y = row['raw_y']
                    nr_str = str(row['sekvens_nr'])
                    er_maal = (str(row['event_typeid']) == '16')

                    prik_farve = '#df003b' if er_maal else 'black'
                    prik_str = 70 if er_maal else 45

                    pitch.scatter(r_x, r_y, color=prik_farve, s=prik_str, ax=ax, zorder=4)

                    ax.text(
                        r_x, r_y, nr_str,
                        fontsize=6.5, fontweight='bold', ha='center', va='center', color='white', zorder=5
                    )

                    navn = str(row.get('player_name', ''))
                    if navn and navn != 'nan':
                        ax.text(
                            r_x, r_y - 2.5, navn,
                            fontsize=6, ha='center', va='top', color='#333333', zorder=5
                        )

            st.pyplot(fig, use_container_width=True)

            st.markdown(
                f"<div style='display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: #555; background-color: #fcfcfc; padding: 6px 10px; border-radius: 4px; border: 1px solid #eaeaea; margin-top: -5px;'>"
                f"<span><b>Målscorer:</b> {målscorer}</span>"
                f"<span><b>Slutresultat:</b> {info_row['slut_res']}</span>"
                f"<span><b>Kamp:</b> {info_row['kamp_navn']} ({info_row['dato']})</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        with col_tabel:
            st.markdown("##### Aktioner i sekvensen")
            vis_cols = [c for c in ['sekvens_nr', 'player_name', 'aktion', 'detaljer'] if c in sekvens_df.columns]
            
            tabel_df = sekvens_df[vis_cols].rename(columns={
                'sekvens_nr': 'Nr.',
                'player_name': 'Spiller',
                'aktion': 'Aktion',
                'detaljer': 'Detaljer'
            })
            st.dataframe(tabel_df, use_container_width=True, hide_index=True, height=380)
