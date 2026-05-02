import streamlit as st
import pandas as pd

def vis_side(conn):
    stat_forklaringer = {
        # --- Grundlæggende kampstatistik ---
        "minsPlayed": "Antal spillede minutter.",
        "yellowCard": "Gule kort.",
        "secondYellow": "Andet gult kort (rødt).",
        "redCard": "Rødt kort.",
        "totalSubOn": "Indskiftninger.",
        "totalSubOff": "Udskiftninger.",
        "touches": "Antal berøringer i alt.",
        "touchesInOppBox": "Berøringer i modstanderens felt.",
        "possessionPercentage": "Boldbesiddelse i procent.",

        # --- Mål og Assists ---
        "goals": "Antal scorede mål i alt.",
        "ownGoals": "Selvemål.",
        "goalsOpenplay": "Mål scoret i åbent spil.",
        "goalFastbreak": "Mål scoret på kontraangreb.",
        "goalAssist": "Målgivende aflevering (Assist).",
        "secondGoalAssist": "Anden-assist (afleveringen før assisten).",
        "goalAssistOpenplay": "Assist i åbent spil.",
        "goalAssistSetplay": "Assist på dødbolde.",
        "goalAssistDeadball": "Assist på dødbolde (frispark/hjørne).",
        "goalAssistIntentional": "Bevidst målgivende aflevering.",
        "assistOwnGoal": "Fremprovokeret selvmål.",
        "assistPenaltyWon": "Fremprovokeret straffespark (der fører til mål).",
        "assistFreeKickWon": "Fremprovokeret frispark (der fører til mål).",

        # --- Skud og Afslutninger ---
        "totalScoringAtt": "Samlede afslutninger (skud på mål, ved siden af og blokerede).",
        "ontargetScoringAtt": "Skud indenfor rammen.",
        "shotOffTarget": "Skud udenfor rammen.",
        "blockedScoringAtt": "Blokerede skudforsøg.",
        "hitWoodwork": "Skud på stolpe eller overligger.",
        "postScoringAtt": "Afslutning der rammer stolpen.",
        "totalAttAssist": "Chancer skabt (aflevering til skud).",
        "ontargetAttAssist": "Chancer skabt til skud på mål.",
        "offtargetAttAssist": "Chancer skabt til skud ved siden af mål.",
        "attOpenplay": "Afslutninger i åbent spil.",
        "attSetpiece": "Afslutninger på dødbolde.",
        "attFastbreak": "Afslutninger på kontraangreb.",
        "bigChanceCreated": "Store chancer skabt.",
        "bigChanceScored": "Store chancer omsat til mål.",
        "bigChanceMissed": "Store chancer brændt.",

        # --- Afleveringer, Tacklinger & Forsvar ---
        "accuratePass": "Succesfulde afleveringer.",
        "totalPass": "Afleveringer i alt.",
        "totalTackle": "Tacklinger i alt.",
        "wonTackle": "Vundne tacklinger.",
        "totalClearance": "Rensninger (clearinger).",
        "interceptions": "Bolderobringer (interceptions).",
        "fkFoulLost": "Frispark begået.",
        "fkFoulWon": "Frispark vundet.",
        "totalOffside": "Offsides i alt.",
        "cornerTaken": "Hjørnespark taget.",
        "wonCorners": "Hjørnespark vundet.",
        "lostCorners": "Hjørnespark givet væk.",
        "totalThrows": "Indkast.",

        # --- Målmand & Defensiv ---
        "saves": "Redninger.",
        "cleanSheet": "Rent bur (ingen mål lukket ind).",
        "goalsConceded": "Mål lukket ind.",
        "penaltySave": "Straffespark reddet.",
        "penaltyFaced": "Straffespark stået overfor.",
        "penaltyConceded": "Straffespark begået.",
        "penGoalsConceded": "Mål lukket ind på straffe.",

        # --- Expected Goals (xG) & Assists (xA) ---
        "expectedGoals": "xG - Samlet forventede mål.",
        "expectedGoalsNonpenalty": "xG - Forventede mål uden straffespark.",
        "expectedGoalsOpenplay": "xG - Forventede mål i åbent spil.",
        "expectedGoalsSetplay": "xG - Forventede mål på dødbolde.",
        "expectedGoalsFreekick": "xG - Forventede mål på direkte frispark.",
        "expectedGoalsHd": "xG - Forventede mål på hovedstød.",
        "expectedGoalsRf": "xG - Forventede mål med højre fod.",
        "expectedGoalsLf": "xG - Forventede mål med venstre fod.",
        "expectedGoalsontarget": "xG på mål (xGOT) - Værdien af skuddets placering.",
        "expectedAssists": "xA - Forventede assists.",
        "expectedAssistsOpenplay": "xA - Forventede assists i åbent spil.",
        "expectedAssistsSetplay": "xA - Forventede assists på dødbolde.",

        # --- Specifikke detaljer ---
        "attRfTotal": "Samlede afslutninger med højre fod.",
        "attLfTotal": "Samlede afslutninger med venstre fod.",
        "attHdTotal": "Samlede afslutninger med hovedet.",
        "penaltyWon": "Straffespark vundet (fremprovokeret).",
        "formationUsed": "Holdets formation.",
    }

    # 1. Forbindelses-status (Hurtigt overblik)
    try:
        status = conn.query("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE()")
        st.caption(f"Forbundet som: {status.iloc[0,0]} ({status.iloc[0,1]})")
    except:
        pass

    # Lav faner
    tab_struktur, tab_stats, tab_kode = st.tabs(["📋 Tabelstruktur", "📊 Stat_Type Forklaringer", "💻 Kode-eksempel"])

    # --- FANE 1: TABELSTRUKTUR ---
    with tab_struktur:
        tabeller = ['OPTA_MATCHEXPECTEDGOALS', 'OPTA_MATCHSTATS', 'OPTA_PLAYERS']
        valgt_tabel = st.selectbox("Vælg tabel for at se kolonner:", tabeller)
        
        if valgt_tabel:
            query_cols = f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM KLUB_HVIDOVREIF.INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{valgt_tabel}' AND TABLE_SCHEMA = 'AXIS'
                ORDER BY ORDINAL_POSITION
            """
            df_cols = conn.query(query_cols)
            st.dataframe(df_cols, use_container_width=True, hide_index=True)

    # --- FANE 2: STAT_TYPE FORKLARINGER ---
    with tab_stats:
        st.subheader("Oversættelse af Opta Stats")
        try:
            # 1. Hent unikke typer
            st_query = "SELECT DISTINCT STAT_TYPE FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHSTATS"
            df_st = conn.query(st_query)
            
            # 2. Lav en kopi af din ordbog med små bogstaver for at sikre match
            stat_forklaringer_lower = {k.lower(): v for k, v in stat_forklaringer.items()}
            
            # 3. Map ved at konvertere Snowflake-kolonnen til små bogstaver midlertidigt
            df_st['Forklaring'] = df_st['STAT_TYPE'].str.lower().map(stat_forklaringer_lower).fillna("-")
            
            # 4. Vis resultatet
            st.dataframe(df_st.sort_values('STAT_TYPE'), use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"Kunne ikke hente stat-typer: {e}")

    # --- FANE 3: KODE-GENERATOR TIL DIN ARKITEKTUR ---
    with tab_kode:
        st.subheader("🚀 Hvidovre SQL-Architect")
        st.write("Vælg de metrics du vil have med i din CTE-baserede SQL query:")

        # Vi lader dig vælge de stats, du vil have ind i din UniqueMatchStats CTE
        mulige_stats = sorted(list(stat_forklaringer.keys()))
        valgte_stats = st.multiselect(
            "Vælg metrics til SQL-beregning:", 
            mulige_stats, 
            default=["goals", "touchesInOppBox", "accuratePass"]
        )

        if valgte_stats:
            # Dynamisk generering af CASE statements til SQL
            case_statements = "\n".join([
                f"                MAX(CASE WHEN STAT_TYPE = '{s}' THEN STAT_TOTAL ELSE 0 END) as {s.upper()}," 
                for s in valgte_stats
            ]).rstrip(',') # Fjerner det sidste komma

            # Dynamisk generering af SUM statements til LeagueStats
            sum_statements = "\n".join([
                f"                SUM({s.upper()}) as TOTAL_{s.upper()}," 
                for s in valgte_stats
            ]).rstrip(',')

            st.markdown("### 1. Tilpas din SQL Query")
            st.info("Denne query er bygget til din `vis_side()` struktur med CTEs:")
            
            sql_gen = f"""
sql = f'''
    WITH UniqueMatchStats AS (
        SELECT 
            MATCH_OPTAUUID,
            CONTESTANT_OPTAUUID,
{case_statements}
        FROM {{DB}}.OPTA_MATCHSTATS
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{{LIGA_UUID}}'
        GROUP BY 1, 2
    ),
    LeagueStats AS (
        SELECT 
            CONTESTANT_OPTAUUID,
{sum_statements}
        FROM UniqueMatchStats
        GROUP BY 1
    )
    SELECT * FROM LeagueStats
'''
            """
            st.code(sql_gen, language="python")

            st.markdown("### 2. Tilpas din Python Logik")
            st.info("Tilføj disse kolonner til din 'Numerisk vask' sektion:")
            
            python_cols = ", ".join([f"'TOTAL_{s.upper()}'" for s in valgte_stats])
            python_gen = f"""
# Tilføj til din liste over kolonner der skal vaskes:
cols_to_fix = [{python_cols}]

# Hjælpefunktion til visning (get_rank_and_val):
# r_stat, v_stat = get_rank_and_val('TOTAL_{valgte_stats[0].upper()}')
            """
            st.code(python_gen, language="python")

            st.success("Kopier SQL-delen ind i din `sql = f\"\"\"...\"\"\"` blok.")
        else:
            st.warning("Vælg mindst én stat for at generere koden.")
