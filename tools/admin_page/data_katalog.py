import streamlit as st
import pandas as pd

def vis_side(conn):
    # --- ORDBOG TIL STAT_TYPE ---
    # --- UDVIDET ORDBOG TIL STAT_TYPE FORKLARINGER ---
    stat_forklaringer = {
        # Grundlæggende kampstatistik
        "minsPlayed": "Antal spillede minutter.",
        "yellowCard": "Gule kort.",
        "secondYellow": "Andet gult kort (rødt).",
        "redCard": "Rødt kort.",
        "totalSubOn": "Indskiftninger.",
        "totalSubOff": "Udskiftninger.",
        "touches": "Antal berøringer i alt.",
        "touchesInOppBox": "Berøringer i modstanderens felt.",

        # Mål og Assists
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

        # Skud og Afslutninger
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

        # Expected Goals (xG) & Assists (xA)
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

        # Specifikke skud-detaljer (Fod/Position)
        "attRfTotal": "Samlede afslutninger med højre fod.",
        "attLfTotal": "Samlede afslutninger med venstre fod.",
        "attHdTotal": "Samlede afslutninger med hovedet.",
        "attIboxGoal": "Mål scoret inde i feltet.",
        "attOboxGoal": "Mål scoret udenfor feltet.",
        "attPenGoal": "Mål scoret på straffespark.",
        "penaltyWon": "Straffespark fremprovokeret.",
        
        # Forsvars-orienteret xG (Conceded)
        "expectedGoalsConceded": "xGC - Forventede mål indkasseret.",
        "expectedGoalsNonpenaltyConceded": "xGC - Forventede mål indkasseret (uden straffe).",
        "expectedGoalsontargetConceded": "xGOTC - xG på mål indkasseret.",
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

    # --- FANE 3: KODE-EKSEMPEL ---
    with tab_kode:
        st.subheader("Sådan bruger du STAT_TYPE i din kode")
        st.info("Brug denne metode når du skal trække specifikke tal ud til spiller- eller kampsider.")
        
        kode_eksempel = """
# Eksempel på hvordan du filtrerer xG og Assists i din data-load
def get_player_performance(conn, player_uuid):
    query = f'''
        SELECT 
            STAT_TYPE, 
            STAT_VALUE 
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHSTATS
        WHERE PLAYER_OPTAUUID = '{player_uuid}'
        AND STAT_TYPE IN ('expectedGoals', 'goalAssist', 'touchesInOppBox')
    '''
    df = conn.query(query)
    
    # Map forklaringerne på i koden
    ordbog = {
        'expectedGoals': 'xG',
        'goalAssist': 'Assists',
        'touchesInOppBox': 'Felt-aktioner'
    }
    df['Label'] = df['STAT_TYPE'].map(ordbog)
    return df
        """
        st.code(kode_eksempel, language='python')
