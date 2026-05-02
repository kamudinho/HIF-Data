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

    # --- FANE 3: INTERAKTIV KODE-GENERATOR ---
    with tab_kode:
        st.subheader("Interaktiv SQL & Python Generator")
        st.write("Vælg de stats du vil bruge, for at generere din kode:")

        # 1. Checkboxes til valg af stats (baseret på din ordbog)
        # Vi sorterer dem alfabetisk så de er lette at finde
        mulige_stats = sorted(list(stat_forklaringer.keys()))
        valgte_stats = st.multiselect("Vælg statistikker:", mulige_stats, default=["expectedGoals", "goalAssist"])

        if valgte_stats:
            # Lav formateret streng til SQL: 'stat1', 'stat2'
            sql_list = ", ".join([f"'{s}'" for s in valgte_stats])
            
            # Lav formateret dict til Python mapping
            python_mapping = "{\n" + ",\n".join([f"        '{s}': '{stat_forklaringer[s]}'" for s in valgte_stats]) + "\n    }"

            st.markdown("### 1. SQL Query")
            st.info("Kopier denne query til din Snowflake-funktion:")
            sql_kode = f"""
SELECT 
    PLAYER_NAME,
    STAT_TYPE,
    SUM(STAT_VALUE) as TOTAL
FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHSTATS
WHERE STAT_TYPE IN ({sql_list})
AND TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o' -- Sæson 25/26
GROUP BY PLAYER_NAME, STAT_TYPE
            """
            st.code(sql_kode, language="sql")

            st.markdown("### 2. Python Mapping")
            st.info("Brug dette i din Streamlit-app til at give flotte navne:")
            python_kode = f"""
# Definer navne baseret på dine valg i kataloget
stat_map = {python_mapping}

# Påfør navne på dit dataframe
df['Visningsnavn'] = df['STAT_TYPE'].map(stat_map)
            """
            st.code(python_kode, language="python")
        else:
            st.warning("Vælg mindst én statistik for at generere kode.")
