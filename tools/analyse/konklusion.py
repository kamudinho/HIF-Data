#HIF-Data/tools/analyse/konklusion.py

import streamlit as st
import pandas as pd
from data.utils.team_mapping import (
    TEAMS,
    COMPETITIONS,
    SEASONS,
    SEASON_LEAGUE_MAPPER,
    COMPETITION_NAME,
    TOURNAMENTCALENDAR_NAME as SAESON_NAVN,
)
from data.data_load import _get_snowflake_conn

# Metric-definitioner brugt i "Alle hold"-leaderboardet.
# (label, kolonne, ascending=True hvis LAVEST er bedst, decimaler, suffix, kategori)
METRIC_DEFS = [
    ("Mål scoret", "GOALS", False, 0, "", "Afslutningsspil"),
    ("Expected Goals (xG)", "XG", False, 1, "", "Afslutningsspil"),
    ("Skud i alt", "SHOTS_TOTAL", False, 0, "", "Afslutningsspil"),
    ("Skudpræcision", "SHOT_ACCURACY", False, 1, "%", "Afslutningsspil"),
    ("Assists", "ASSISTS", False, 0, "", "Afslutningsspil"),
    ("Expected Assists (xA)", "XA", False, 2, "", "Afslutningsspil"),
    ("Store chancer skabt", "BIG_CHANCES_CREATED", False, 0, "", "Afslutningsspil"),
    ("Store chancer misset", "BIG_CHANCES_MISSED", True, 0, "", "Afslutningsspil"),
    ("Ramt stolpe/overligger", "WOODWORK", False, 0, "", "Afslutningsspil"),

    ("Boldbesiddelse", "POSS", False, 1, "%", "Opbygningsspil"),
    ("Berøringer i alt", "TOUCHES", False, 0, "", "Opbygningsspil"),
    ("Afleveringspræcision", "PASS_ACCURACY", False, 1, "%", "Opbygningsspil"),
    ("Berøringer i modst. felt", "BOX_TOUCHES", False, 0, "", "Opbygningsspil"),

    ("Tackling-succes", "TACKLE_SUCCESS", False, 1, "%", "Defensivt spil"),
    ("Klareringer", "CLEARANCES", False, 0, "", "Defensivt spil"),
    ("Offsides fanget", "OFFSIDES_WON", False, 0, "", "Defensivt spil"),
    ("PPDA (lavest = mest pres)", "PPDA", True, 2, "", "Defensivt spil"),
    ("xG imod (lavest = bedst)", "XG_AGAINST", True, 2, "", "Defensivt spil"),
    ("Frispark begået (færrest bedst)", "FOULS_CONCEDED", True, 0, "", "Defensivt spil"),

    ("Redninger", "SAVES", False, 0, "", "Målmand & dødbolde"),
    ("Clean sheets", "CLEAN_SHEETS", False, 0, "", "Målmand & dødbolde"),
    ("Mål imod (færrest bedst)", "GOALS_CONCEDED", True, 0, "", "Målmand & dødbolde"),
    ("Straffe reddet", "PENALTY_SAVES", False, 0, "", "Målmand & dødbolde"),
    ("Hjørnespark taget", "CORNERS_TAKEN", False, 0, "", "Målmand & dødbolde"),
    ("Hjørnespark imod (færrest bedst)", "CORNERS_CONCEDED", True, 0, "", "Målmand & dødbolde"),

    ("Gule kort (færrest bedst)", "YELLOW_CARDS", True, 0, "", "Disciplin"),
    ("Røde kort (færrest bedst)", "RED_CARDS", True, 0, "", "Disciplin"),
]

def vis_side(dp=None):
    # --- 1. SETUP ---
    DB = "KLUB_HVIDOVREIF.AXIS"

    LIGA_UUID = SEASONS.get(SAESON_NAVN, {}).get(COMPETITION_NAME)

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke forbinde til Snowflake.")
        return

    if not LIGA_UUID:
        st.warning(f"Ingen turnerings-UUID fundet for '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'. Tjek SEASONS-mappingen i team_mapping.py.")
        return

    # --- 2. SQL: OPTA_MATCHSTATS (hovedstatistik) ---
    sql = f'''
    WITH MatchStats AS (
        SELECT 
            UPPER(TRIM(CONTESTANT_OPTAUUID)) as TEAM_ID,

            -- Afslutningsspil
            SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) as GOALS,
            SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS_TOTAL,
            SUM(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS_ON_TARGET,
            SUM(CASE WHEN STAT_TYPE = 'blockedScoringAtt' THEN STAT_TOTAL ELSE 0 END) as SHOTS_BLOCKED,
            SUM(CASE WHEN STAT_TYPE = 'goalAssist' THEN STAT_TOTAL ELSE 0 END) as ASSISTS,

            -- Opbygningsspil
            AVG(CASE WHEN STAT_TYPE = 'possessionPercentage' AND STAT_TOTAL > 0 
                     THEN CAST(STAT_TOTAL AS FLOAT) END) as POSS,
            SUM(CASE WHEN STAT_TYPE = 'accuratePass' THEN STAT_TOTAL ELSE 0 END) as PASSES_ACCURATE,
            SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) as PASSES_TOTAL,
            SUM(CASE WHEN STAT_TYPE = 'cornerTaken' THEN STAT_TOTAL ELSE 0 END) as CORNERS_TAKEN,
            MAX(CASE WHEN STAT_TYPE = 'formationUsed' THEN STAT_TOTAL ELSE NULL END) as FORMATION,

            -- Defensivt spil
            SUM(CASE WHEN STAT_TYPE = 'wonTackle' THEN STAT_TOTAL ELSE 0 END) as TACKLES_WON,
            SUM(CASE WHEN STAT_TYPE = 'totalTackle' THEN STAT_TOTAL ELSE 0 END) as TACKLES_TOTAL,
            SUM(CASE WHEN STAT_TYPE = 'totalClearance' THEN STAT_TOTAL ELSE 0 END) as CLEARANCES,
            SUM(CASE WHEN STAT_TYPE = 'totalOffside' THEN STAT_TOTAL ELSE 0 END) as OFFSIDES_WON,
            SUM(CASE WHEN STAT_TYPE = 'fkFoulWon' THEN STAT_TOTAL ELSE 0 END) as FOULS_WON,
            SUM(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN STAT_TOTAL ELSE 0 END) as FOULS_CONCEDED,

            -- Målmand & dødbolde
            SUM(CASE WHEN STAT_TYPE = 'saves' THEN STAT_TOTAL ELSE 0 END) as SAVES,
            SUM(CASE WHEN STAT_TYPE = 'cleanSheet' THEN STAT_TOTAL ELSE 0 END) as CLEAN_SHEETS,
            SUM(CASE WHEN STAT_TYPE = 'goalsConceded' THEN STAT_TOTAL ELSE 0 END) as GOALS_CONCEDED,
            SUM(CASE WHEN STAT_TYPE = 'penaltySave' THEN STAT_TOTAL ELSE 0 END) as PENALTY_SAVES,
            SUM(CASE WHEN STAT_TYPE = 'penaltyWon' THEN STAT_TOTAL ELSE 0 END) as PENALTIES_WON,
            SUM(CASE WHEN STAT_TYPE = 'penaltyConceded' THEN STAT_TOTAL ELSE 0 END) as PENALTIES_CONCEDED,
            SUM(CASE WHEN STAT_TYPE = 'ownGoals' THEN STAT_TOTAL ELSE 0 END) as OWN_GOALS,

            -- Disciplin
            SUM(CASE WHEN STAT_TYPE = 'totalYellowCard' THEN STAT_TOTAL ELSE 0 END) as YELLOW_CARDS,
            SUM(CASE WHEN STAT_TYPE = 'secondYellow' THEN STAT_TOTAL ELSE 0 END) as SECOND_YELLOWS,
            SUM(CASE WHEN STAT_TYPE = 'totalRedCard' THEN STAT_TOTAL ELSE 0 END) as RED_CARDS

        FROM {DB}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    ),
    ExpectedStats AS (
        SELECT 
            UPPER(TRIM(CONTESTANT_OPTAUUID)) as TEAM_ID,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN STAT_VALUE ELSE 0 END) as XG,
            SUM(CASE WHEN STAT_TYPE = 'expectedGoalsConceded' THEN STAT_VALUE ELSE 0 END) as XG_AGAINST,
            SUM(CASE WHEN STAT_TYPE = 'expectedAssists' THEN STAT_VALUE ELSE 0 END) as XA,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_VALUE ELSE 0 END) as BIG_CHANCES_CREATED,
            SUM(CASE WHEN STAT_TYPE = 'bigChanceMissed' THEN STAT_VALUE ELSE 0 END) as BIG_CHANCES_MISSED,
            SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN STAT_VALUE ELSE 0 END) as BOX_TOUCHES,
            SUM(CASE WHEN STAT_TYPE = 'hitWoodwork' THEN STAT_VALUE ELSE 0 END) as WOODWORK,
            SUM(CASE WHEN STAT_TYPE = 'touches' THEN STAT_VALUE ELSE 0 END) as TOUCHES
        FROM {DB}.OPTA_MATCHEXPECTEDGOALS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    ),
    CornersAgainst AS (
        SELECT 
            UPPER(TRIM(s1.CONTESTANT_OPTAUUID)) as TEAM_ID,
            SUM(CASE WHEN s2.STAT_TYPE = 'cornerTaken' THEN s2.STAT_TOTAL ELSE 0 END) as CORNERS_CONCEDED
        FROM {DB}.OPTA_MATCHSTATS s1
        JOIN {DB}.OPTA_MATCHSTATS s2 
            ON s1.MATCH_OPTAUUID = s2.MATCH_OPTAUUID 
            AND UPPER(TRIM(s1.CONTESTANT_OPTAUUID)) <> UPPER(TRIM(s2.CONTESTANT_OPTAUUID))
        WHERE s1.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
          AND s2.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        GROUP BY 1
    )
    SELECT m.*, 
        COALESCE(e.XG, 0) as XG, 
        COALESCE(e.XG_AGAINST, 0) as XG_AGAINST,
        COALESCE(e.XA, 0) as XA,
        COALESCE(e.BIG_CHANCES_CREATED, 0) as BIG_CHANCES_CREATED,
        COALESCE(e.BIG_CHANCES_MISSED, 0) as BIG_CHANCES_MISSED,
        COALESCE(e.BOX_TOUCHES, 0) as BOX_TOUCHES,
        COALESCE(e.WOODWORK, 0) as WOODWORK,
        COALESCE(e.TOUCHES, 0) as TOUCHES,
        COALESCE(c.CORNERS_CONCEDED, 0) as CORNERS_CONCEDED
    FROM MatchStats m
    LEFT JOIN ExpectedStats e ON m.TEAM_ID = e.TEAM_ID
    LEFT JOIN CornersAgainst c ON m.TEAM_ID = c.TEAM_ID
    '''

    NUMERIC_COLS = [
        'GOALS', 'SHOTS_TOTAL', 'SHOTS_ON_TARGET', 'SHOTS_BLOCKED', 'ASSISTS',
        'POSS', 'PASSES_ACCURATE', 'PASSES_TOTAL', 'CORNERS_TAKEN', 'CORNERS_CONCEDED',
        'TACKLES_WON', 'TACKLES_TOTAL', 'CLEARANCES', 'OFFSIDES_WON', 'FOULS_WON', 'FOULS_CONCEDED',
        'SAVES', 'CLEAN_SHEETS', 'GOALS_CONCEDED', 'PENALTY_SAVES', 'PENALTIES_WON', 'PENALTIES_CONCEDED', 'OWN_GOALS',
        'YELLOW_CARDS', 'SECOND_YELLOWS', 'RED_CARDS',
        'XG', 'XG_AGAINST', 'XA', 'BIG_CHANCES_CREATED', 'BIG_CHANCES_MISSED', 'BOX_TOUCHES', 'WOODWORK', 'TOUCHES'
    ]

    try:
        df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df.columns = [str(c).upper() for c in df.columns]

        for col in NUMERIC_COLS:
            if col in df.columns:
                df[col] = df[col].astype(float)

        if df['POSS'].mean() < 1:
            df['POSS'] = df['POSS'] * 100

        df['SHOT_ACCURACY'] = (df['SHOTS_ON_TARGET'] / df['SHOTS_TOTAL'].replace(0, pd.NA)) * 100
        df['PASS_ACCURACY'] = (df['PASSES_ACCURATE'] / df['PASSES_TOTAL'].replace(0, pd.NA)) * 100
        df['TACKLE_SUCCESS'] = (df['TACKLES_WON'] / df['TACKLES_TOTAL'].replace(0, pd.NA)) * 100

    except Exception as e:
        st.error(f"SQL Fejl: {e}")
        return

    if df.empty:
        st.warning(f"Ingen kampstatistik fundet for turneringen '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'.")
        return

    # --- 2b. SQL: PPDA fra Wyscout ---
    wyid = COMPETITIONS.get(COMPETITION_NAME, {}).get("wyid")

    if '/' in SAESON_NAVN:
        y_start, y_end = SAESON_NAVN.split('/')
    else:
        y_start, y_end = SAESON_NAVN, str(int(SAESON_NAVN) + 1)
    saeson_start = f"{y_start}-07-01"
    saeson_slut = f"{y_end}-06-30"

    df['PPDA'] = pd.NA

    if wyid:
        try:
            ppda_sql = f'''
                SELECT tm.TEAM_WYID, AVG(md.PPDA) as PPDA
                FROM {DB}.WYSCOUT_TEAMMATCHES tm
                LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md 
                    ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID
                WHERE tm.COMPETITION_WYID = {wyid}
                AND tm.DATE BETWEEN '{saeson_start}' AND '{saeson_slut}'
                GROUP BY tm.TEAM_WYID
            '''
            df_ppda = conn.query(ppda_sql) if hasattr(conn, 'query') else pd.read_sql(ppda_sql, conn)
            df_ppda.columns = [str(c).upper() for c in df_ppda.columns]

            wyid_to_uuid = {
                info.get('team_wyid'): str(info.get('opta_uuid')).strip().upper()
                for info in TEAMS.values() if info.get('team_wyid') and info.get('opta_uuid')
            }
            df_ppda['TEAM_ID'] = df_ppda['TEAM_WYID'].map(wyid_to_uuid)
            df_ppda['PPDA'] = df_ppda['PPDA'].astype(float)

            df = df.drop(columns=['PPDA']).merge(df_ppda[['TEAM_ID', 'PPDA']], on='TEAM_ID', how='left')
        except Exception as e:
            st.caption(f"Kunne ikke hente PPDA fra Wyscout: {e}")

    # --- 3. UI STYLING ---
    st.markdown("""
        <style>
        .analysis-card { 
            border: 1px solid #e6e6e6; 
            padding: 20px; 
            border-radius: 5px; 
            margin-bottom: 20px; 
            background-color: white;
            min-height: 250px;
        }
        .section-title { font-weight: bold; margin-bottom: 10px; font-size: 1.2rem; border-bottom: 2px solid #C8102E; padding-bottom: 5px; }
        .conclusion-text { color: #C8102E; font-weight: bold; margin-top: 15px; text-transform: uppercase; font-size: 0.85rem; }
        .stat-line { margin-bottom: 8px; font-size: 0.95rem; }
        table { text-align: center !important; }
        th { text-align: center !important; }
        td { text-align: center !important; }
        /* Gør Hold-kolonnen bredere og sikrer at den gælder på tværs af tabeller */
        [data-testid="stDataFrame"] th:nth-child(1), 
        [data-testid="stDataFrame"] td:nth-child(1) {
            min-width: 180px !important;
            max-width: 220px !important;
            white-space: normal !important;
            text-align: left !important;
        }
        [data-testid="stDataFrame"] th:nth-child(1) {
            text-align: left !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 4. HJÆLPEFUNKTIONER ---
    uuid_to_name = {
        str(info.get('opta_uuid')).strip().upper(): name
        for name, info in TEAMS.items() if info.get('opta_uuid')
    }

    def get_ordinal(n):
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

    def get_rank(col, ascending=False):
        temp = df.dropna(subset=[col]).sort_values(col, ascending=ascending).reset_index(drop=True)
        try:
            rank = temp[temp['TEAM_ID'] == target_uuid].index[0] + 1
            return get_ordinal(rank)
        except Exception:
            return "**?**"

    def get_leader_and_worst(col, ascending=False):
        if col not in df.columns:
            return None, None, None, None
        temp = df.dropna(subset=[col])
        if temp.empty:
            return None, None, None, None
        
        temp_best = temp.sort_values(col, ascending=ascending)
        best = temp_best.iloc[0]
        best_name = uuid_to_name.get(best['TEAM_ID'], best['TEAM_ID'])
        
        temp_worst = temp.sort_values(col, ascending=not ascending)
        worst = temp_worst.iloc[0]
        worst_name = uuid_to_name.get(worst['TEAM_ID'], worst['TEAM_ID'])
        
        return best_name, best[col], worst_name, worst[col]

    def safe_val(val, decimals=1, suffix=""):
        if pd.isna(val):
            return "N/A"
        return f"{val:.{decimals}f}{suffix}"

    # --- 5. FILTRERING ---
    hold_navne = SEASON_LEAGUE_MAPPER.get(SAESON_NAVN, {}).get(COMPETITION_NAME, [])
    hold_options = {n: TEAMS[n].get("opta_uuid") for n in hold_navne if n in TEAMS}

    if not hold_options:
        st.warning(f"Ingen hold fundet for '{COMPETITION_NAME}' i sæsonen '{SAESON_NAVN}'. Tjek SEASON_LEAGUE_MAPPER og TEAMS i team_mapping.py.")
        return

    manglende = [n for n in hold_navne if n not in TEAMS]
    if manglende:
        st.caption(f"Følgende hold i SEASON_LEAGUE_MAPPER mangler stamdata i TEAMS og vises ikke: {', '.join(manglende)}")

    # --- 5b. TOP LINJE: DROPDOWN OG SEGMENTED CONTROL I TO KOLONNER ---
    col_top1, col_top2 = st.columns([1, 1])

    with col_top1:
        valgt_navn = st.selectbox("Vælg hold", sorted(hold_options.keys()))

    with col_top2:
        visning = st.segmented_control(
            " ",
            ["Enkelt hold", "Alle hold (bedste og dårligste pr. metric)", "Holdtabel (Y-akse)"],
            default="Enkelt hold",
            selection_mode="single"
        )

    target_uuid = str(hold_options[valgt_navn]).strip().upper()

    if visning == "Alle hold (bedste og dårligste pr. metric)":
        rows = []
        for label, col, ascending, decimals, suffix, kategori in METRIC_DEFS:
            best_team, best_val, worst_team, worst_val = get_leader_and_worst(col, ascending=ascending)
            if best_team is None:
                continue
            rows.append({
                "Kategori": kategori,
                "Metric": label,
                "Bedste hold": best_team,
                "Bedste værdi": safe_val(best_val, decimals, suffix),
                "Dårligste hold": worst_team,
                "Dårligste værdi": safe_val(worst_val, decimals, suffix),
            })

        if not rows:
            st.warning("Ingen data at vise for de valgte metrics.")
            return

        df_leaders = pd.DataFrame(rows)
        for kategori in df_leaders['Kategori'].unique():
            st.markdown(f"**{kategori}**")
            st.dataframe(
                df_leaders[df_leaders['Kategori'] == kategori][['Metric', 'Bedste hold', 'Bedste værdi', 'Dårligste hold', 'Dårligste værdi']],
                hide_index=True,
                use_container_width=True,
            )
        return

    elif visning == "Holdtabel (Y-akse)":
        kategorier = []
        for _, _, _, _, _, cat in METRIC_DEFS:
            if cat not in kategorier:
                kategorier.append(cat)

        raw_team_data = []
        for _, r in df.iterrows():
            t_name = uuid_to_name.get(r['TEAM_ID'], r['TEAM_ID'])
            row_data = {"Hold": t_name, "TEAM_ID": r['TEAM_ID']}
            for label, col, _, _, _, _ in METRIC_DEFS:
                if col in r:
                    row_data[col] = r[col]
                else:
                    row_data[col] = pd.NA
            raw_team_data.append(row_data)

        if not raw_team_data:
            st.warning("Ingen data at vise i tabellen.")
            return

        df_raw_teams = pd.DataFrame(raw_team_data)

        for cat in kategorier:
            st.markdown(f"### {cat}")
            cat_defs = [m for m in METRIC_DEFS if m[5] == cat]
            
            display_rows = []
            
            for _, r in df_raw_teams.iterrows():
                t_name = r["Hold"]
                row_disp = {"Hold": t_name}
                
                for label, col, ascending, decimals, suffix, _ in cat_defs:
                    val = r[col]
                    row_disp[label] = safe_val(val, decimals, suffix)
                display_rows.append(row_disp)
            
            df_cat = pd.DataFrame(display_rows).set_index("Hold")
            
            def style_cells(data):
                styled = pd.DataFrame('', index=data.index, columns=data.columns)
                for col_name in data.columns:
                    col_key = next((m[1] for m in cat_defs if m[0] == col_name), None)
                    if not col_key:
                        continue
                    temp_sorted = df_raw_teams.dropna(subset=[col_key]).sort_values(col_key, ascending=next(m[2] for m in cat_defs if m[0] == col_name)).reset_index(drop=True)
                    for idx, row in data.iterrows():
                        orig_row = df_raw_teams[df_raw_teams['Hold'] == idx]
                        if orig_row.empty:
                            continue
                        t_id = orig_row.iloc[0]['TEAM_ID']
                        val = orig_row.iloc[0][col_key]
                        if pd.isna(val):
                            continue
                        try:
                            rank_idx = temp_sorted[temp_sorted['TEAM_ID'] == t_id].index[0] + 1
                            total_n = len(temp_sorted)
                            if rank_idx == 1:
                                styled.loc[idx, col_name] = 'background-color: rgba(40, 167, 69, 0.35); text-align: center;'
                            elif rank_idx == 2:
                                styled.loc[idx, col_name] = 'background-color: rgba(40, 167, 69, 0.22); text-align: center;'
                            elif rank_idx == 3:
                                styled.loc[idx, col_name] = 'background-color: rgba(40, 167, 69, 0.12); text-align: center;'
                            elif rank_idx == total_n:
                                styled.loc[idx, col_name] = 'background-color: rgba(220, 53, 69, 0.35); text-align: center;'
                            elif rank_idx == total_n - 1:
                                styled.loc[idx, col_name] = 'background-color: rgba(220, 53, 69, 0.22); text-align: center;'
                            elif rank_idx == total_n - 2:
                                styled.loc[idx, col_name] = 'background-color: rgba(220, 53, 69, 0.12); text-align: center;'
                            else:
                                styled.loc[idx, col_name] = 'text-align: center;'
                        except Exception:
                            styled.loc[idx, col_name] = 'text-align: center;'
                return styled

            styled_df = df_cat.style.apply(style_cells, axis=None).set_properties(**{'text-align': 'center'})
            st.dataframe(styled_df, use_container_width=True, height=470, hide_index=False)
        return

    # --- 6. ENKELT HOLD-VISNING ---
    row_match = df[df['TEAM_ID'] == target_uuid]
    if row_match.empty:
        st.warning(f"Ingen data fundet for {valgt_navn}.")
        return
    row = row_match.iloc[0]

    goals_val = row.get('GOALS', 0)
    xg_val = row.get('XG', 0)
    diff = goals_val - xg_val
    if diff > 2.0:
        præstation_tekst = "overpræsterer markant (flere mål end xG)"
    elif diff > 0.5:
        præstation_tekst = "overpræsterer (flere mål end xG)"
    elif diff < -2.0:
        præstation_tekst = "underpræsterer markant (færre mål end xG)"
    elif diff < -0.5:
        præstation_tekst = "underpræsterer (færre mål end xG)"
    else:
        præstation_tekst = "præsterer normalt i forhold til xG"

    col1, col2 = st.columns(2)

    with col2:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Afslutningsspil</div>
            <div class="stat-line">• {get_rank('GOALS')} flest mål scoret ({int(row['GOALS'])})</div>
            <div class="stat-line">• {get_rank('XG')} højeste expected goals ({row['XG']:.1f} xG)</div>
            <div class="stat-line">• Forskel: {row['GOALS'] - row['XG']:.1f} mål vs xG</div>
            <div class="stat-line">• {get_rank('SHOTS_TOTAL')} flest skud i alt ({int(row['SHOTS_TOTAL'])})</div>
            <div class="stat-line">• Skudpræcision: {safe_val(row['SHOT_ACCURACY'], suffix='%')}</div>
            <div class="stat-line">• {get_rank('BIG_CHANCES_CREATED')} flest store chancer skabt ({int(row['BIG_CHANCES_CREATED'])})</div>
            <div class="stat-line">• Ramt stolpe/overligger: {int(row['WOODWORK'])}</div>
            <div class="conclusion-text">Konklusion – {valgt_navn} {præstation_tekst} med {goals_val:.0f} mål mod {xg_val:.1f} xG.</div>
        </div>
        """, unsafe_allow_html=True)

    with col1:
        f_raw = str(int(row['FORMATION'])) if pd.notnull(row['FORMATION']) else "N/A"
        f_pretty = "-".join(list(f_raw)) if f_raw != "N/A" and len(f_raw) > 2 else f_raw

        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Opbygningsspil</div>
            <div class="stat-line">• {get_rank('POSS')} højeste boldbesiddelse ({row['POSS']:.1f}%)</div>
            <div class="stat-line">• {get_rank('TOUCHES')} flest berøringer i alt ({int(row['TOUCHES'])})</div>
            <div class="stat-line">• Afleveringspræcision: {safe_val(row['PASS_ACCURACY'], suffix='%')}</div>
            <div class="stat-line">• {get_rank('XA', ascending=False)} højeste expected assists ({row['XA']:.2f} xA)</div>
            <div class="stat-line">• {get_rank('BOX_TOUCHES')} flest berøringer i modstanderens felt ({int(row['BOX_TOUCHES'])})</div>
            <div class="stat-line">• Foretrukken formation: {f_pretty}</div>
            <div class="conclusion-text">Konklusion – Benytter primært en {f_pretty} struktur.</div>
        </div>
        """, unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    with col3:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Defensivt spil</div>
            <div class="stat-line">• Tackling-succes: {safe_val(row['TACKLE_SUCCESS'], suffix='%')} ({int(row['TACKLES_WON'])}/{int(row['TACKLES_TOTAL'])})</div>
            <div class="stat-line">• {get_rank('CLEARANCES')} flest klareringer ({int(row['CLEARANCES'])})</div>
            <div class="stat-line">• {get_rank('OFFSIDES_WON')} flest offsides fanget ({int(row['OFFSIDES_WON'])})</div>
            <div class="stat-line">• {get_rank('PPDA', ascending=True)} laveste PPDA ({safe_val(row['PPDA'], decimals=2)})</div>
            <div class="stat-line">• {get_rank('XG_AGAINST', ascending=True)} laveste xG imod ({safe_val(row['XG_AGAINST'], decimals=2)})</div>
            <div class="stat-line">• Frispark: {int(row['FOULS_WON'])} vundet / {int(row['FOULS_CONCEDED'])} begået</div>
            <div class="conclusion-text">Konklusion – Presser med en PPDA på {safe_val(row['PPDA'], decimals=2)}.</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Målmand & dødbolde</div>
            <div class="stat-line">• {get_rank('SAVES')} flest redninger ({int(row['SAVES'])})</div>
            <div class="stat-line">• {get_rank('CLEAN_SHEETS')} flest clean sheets ({int(row['CLEAN_SHEETS'])})</div>
            <div class="stat-line">• {get_rank('GOALS_CONCEDED', ascending=True)} færrest mål imod ({int(row['GOALS_CONCEDED'])})</div>
            <div class="stat-line">• Straffe: {int(row['PENALTIES_WON'])} vundet / {int(row['PENALTIES_CONCEDED'])} imod ({int(row['PENALTY_SAVES'])} reddet)</div>
            <div class="stat-line">• Hjørnespark: {int(row['CORNERS_TAKEN'])} taget / {int(row['CORNERS_CONCEDED'])} imod</div>
            <div class="stat-line">• Selvmål: {int(row['OWN_GOALS'])}</div>
            <div class="conclusion-text">Konklusion – {int(row['CLEAN_SHEETS'])} clean sheets og {int(row['GOALS_CONCEDED'])} mål imod.</div>
        </div>
        """, unsafe_allow_html=True)

    col5, _ = st.columns(2)

    with col5:
        total_kort = int(row['YELLOW_CARDS'] + row['SECOND_YELLOWS'] + row['RED_CARDS'])
        st.markdown(f"""
        <div class="analysis-card">
            <div class="section-title">Disciplin</div>
            <div class="stat-line">• {get_rank('YELLOW_CARDS', ascending=True)} færrest gule kort ({int(row['YELLOW_CARDS'])})</div>
            <div class="stat-line">• Direkte røde kort: {int(row['RED_CARDS'])}</div>
            <div class="stat-line">• Udvisninger efter 2. gule: {int(row['SECOND_YELLOWS'])},</div>
            <div class="stat-line">• {get_rank('FOULS_CONCEDED', ascending=True)} færrest frispark begået ({int(row['FOULS_CONCEDED'])})</div>
            <div class="conclusion-text">Konklusion – {total_kort} kort i alt denne sæson.</div>
        </div>
        """, unsafe_allow_html=True)
