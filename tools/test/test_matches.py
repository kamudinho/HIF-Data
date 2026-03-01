import streamlit as st
import pandas as pd

# 1. DIN OVERSÆTTER-ORDBOG
OPTA_MAP = {
    "ontargetScoringAtt": "Skud på mål",
    "totalScoringAtt": "Afslutninger",
    "totalPass": "Afleveringer",
    "accuratePass": "Succesfulde afleveringer",
    "possessionPercentage": "Besiddelse %",
    "totalTackle": "Tacklinger",
    "fkFoulWon": "Frispark vundet",
    "outfielderBlock": "Blokerede skud",
    "expectedGoals": "xG",
    "expectedGoalsConceded": "xG Imod"
}

def format_score(val):
    if pd.isna(val) or val == "": return "" 
    try: return str(int(float(val)))
    except: return ""

def vis_side(data_package):
    # Branding / Header
    st.subheader("KAMPOVERSIGT")
    
    df_matches = data_package.get("opta_matches")
    df_stats = data_package.get("opta_stats")
    
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    try:
        df = df_matches.copy()
        df.columns = [c.upper() for c in df.columns]
        df['HAR_RESULTAT'] = df['TOTAL_HOME_SCORE'].notna()

        # --- NY SEKTION: KONTROLPANEL I 3 KOLONNER ---
        col1, col2, col3 = st.columns([1, 1, 2]) # [Bredde, Bredde, Dobbelt bredde]

        with col1:
            visning = st.radio("Status:", ["Spillede", "Kommende"], horizontal=True)
        
        # Filtrer data baseret på radio-valg med det samme
        if visning == "Spillede":
            df = df[df['HAR_RESULTAT'] == True]
        else:
            df = df[df['HAR_RESULTAT'] == False]

        with col2:
            liga_hold = sorted(list(set(df['CONTESTANTHOME_NAME'].dropna()) | set(df['CONTESTANTAWAY_NAME'].dropna())))
            valgt_hold = st.selectbox("Vælg hold:", ["Alle hold"] + liga_hold)

        with col3:
            vis_stats = []
            if valgt_hold != "Alle hold" and visning == "Spillede":
                mulige_stats = list(OPTA_MAP.values())
                vis_stats = st.multiselect("Vælg kolonner:", mulige_stats, default=mulige_stats[:4])
            else:
                st.write("") # Holder pladsen hvis intet hold er valgt

        st.markdown("---") # Visuel adskillelse fra kontrollere til tabel

        # --- DATA BEHANDLING ---
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE', 'DATO'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            df = df.sort_values(by=dato_col, ascending=(visning == "Kommende"))

        df['KAMP'] = df['CONTESTANTHOME_NAME'].astype(str) + " - " + df['CONTESTANTAWAY_NAME'].astype(str)
        df['RESULTAT'] = df.apply(lambda r: f"{format_score(r.get('TOTAL_HOME_SCORE'))} - {format_score(r.get('TOTAL_AWAY_SCORE'))}" if r['HAR_RESULTAT'] else "-", axis=1)
        df['DATO_STR'] = df[dato_col].dt.strftime('%d-%m-%Y') if dato_col else ""

        # --- VISNING AF TABEL ---
        if valgt_hold == "Alle hold":
            st.dataframe(df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)
        else:
            f_df = df[(df['CONTESTANTHOME_NAME'] == valgt_hold) | (df['CONTESTANTAWAY_NAME'] == valgt_hold)].copy()
            
            if not df_stats.empty and visning == "Spillede":
                ds = df_stats.copy()
                ds.columns = [c.upper() for c in ds.columns]
                
                match_list = []
                for _, m in f_df.iterrows():
                    m_id = m.get('MATCH_OPTAUUID')
                    is_home = m['CONTESTANTHOME_NAME'] == valgt_hold
                    t_id = m.get('CONTESTANTHOME_OPTAUUID') if is_home else m.get('CONTESTANTAWAY_OPTAUUID')
                    
                    row = {"Dato": m['DATO_STR'], "Kamp": m['KAMP'], "Resultat": m['RESULTAT']}
                    
                    m_s = ds[(ds['MATCH_OPTAUUID'] == m_id) & (ds['CONTESTANT_OPTAUUID'] == t_id)]
                    for _, s_row in m_s.iterrows():
                        raw_name = s_row['STAT_TYPE']
                        if raw_name in OPTA_MAP:
                            dan_name = OPTA_MAP[raw_name]
                            if dan_name in vis_stats:
                                row[dan_name] = s_row['STAT_TOTAL']
                    
                    match_list.append(row)

                final_df = pd.DataFrame(match_list)
                st.dataframe(final_df, use_container_width=True, hide_index=True)
            else:
                st.dataframe(f_df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Fejl i visning: {e}")
