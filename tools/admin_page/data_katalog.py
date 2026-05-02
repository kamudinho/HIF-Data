import streamlit as st
import pandas as pd

def vis_side(conn):
    """
    Viser datakataloget med forklaringer på STAT_TYPE.
    """
    # --- ORDBOG TIL STAT_TYPE FORKLARINGER ---
    # Du kan løbende udvide denne liste, når du finder nye stats i din Snowflake
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

    # --- FORBINDELSES-STATUS ---
    try:
        status = conn.query("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_WAREHOUSE()")
        col1, col2, col3 = st.columns(3)
        col1.metric("Bruger", status.iloc[0,0])
        col2.metric("Rolle", status.iloc[0,1])
        col3.metric("Warehouse", status.iloc[0,4])
    except Exception as e:
        st.error(f"🚨 Kunne ikke hente forbindelsesstatus: {e}")

    st.divider()

    # --- TABELVALG OG KOLONNEOVERSIGT ---
    tabeller = ['OPTA_MATCHEXPECTEDGOALS', 'OPTA_MATCHSTATS', 'OPTA_PLAYERS']
    valgt_tabel = st.selectbox("Vælg tabel for at se tilgængelige kolonner:", tabeller)

    if valgt_tabel:
        st.subheader(f"Oversigt for {valgt_tabel}")
        
        # Metadata Query
        query_cols = f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM KLUB_HVIDOVREIF.INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{valgt_tabel}' 
            AND TABLE_SCHEMA = 'AXIS'
            ORDER BY ORDINAL_POSITION
        """
        
        try:
            df_cols = conn.query(query_cols)
            if not df_cols.empty:
                st.dataframe(df_cols, use_container_width=True, hide_index=True)
                
                # --- STAT_TYPE OVERSIGT MED FORKLARINGER ---
                if "STATS" in valgt_tabel or "EXPECTED" in valgt_tabel:
                    st.write("#### Eksisterende data-typer (STAT_TYPE) med forklaring")
                    
                    # Hent unikke stat_types fra Snowflake
                    query_stats = f"SELECT DISTINCT STAT_TYPE FROM KLUB_HVIDOVREIF.AXIS.{valgt_tabel} LIMIT 200"
                    df_stats = conn.query(query_stats)
                    
                    # Tilføj forklaringen ved at mappe mod vores ordbog
                    df_stats['Forklaring'] = df_stats['STAT_TYPE'].map(stat_forklaringer).fillna("Ingen forklaring fundet - kontakt admin")
                    
                    # Vis som en tabel hvor STAT_TYPE og Forklaring står ved siden af hinanden
                    st.dataframe(
                        df_stats[['STAT_TYPE', 'Forklaring']], 
                        use_container_width=True, 
                        hide_index=True
                    )
            else:
                st.warning(f"Ingen kolonner fundet for {valgt_tabel}.")
                
        except Exception as e:
            st.error(f"❌ Fejl ved indlæsning: {e}")

    # Diagnose expander
    with st.expander("System Diagnose"):
        st.write(f"Sæson: 2025/2026")
        st.write(f"Konfiguration: {st.secrets['connections']['snowflake']['database']}")
