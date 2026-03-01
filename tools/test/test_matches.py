import streamlit as st
import pandas as pd

# 1. DIN OVERSÆTTER-ORDBOG (Tilføj selv flere stats her)
OPTA_MAP = {
    "ontargetScoringAtt": "Skud på mål",
    "totalScoringAtt": "Afslutninger",
    "totalPass": "Afleveringer",
    "accuratePass": "Succesfulde afleveringer",
    "possessionPercentage": "Besiddelse %",
    "totalTackle": "Tacklinger",
    "fkFoulWon": "Frispark begået imod",
    "outfielderBlock": "Blokerede skud",
    "expectedGoals": "xG",
    "expectedGoalsConceded": "xG Imod"
}

def format_score(val):
    if pd.isna(val) or val == "": return "" # Blank hvis ingen data
    try: return str(int(float(val)))
    except: return ""

def vis_side(data_package):
    st.subheader("KAMPOVERSIGT")
    
    df_matches = data_package.get("opta_matches")
    df_stats = data_package.get("opta_stats")
    
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    try:
        df = df_matches.copy()
        df.columns = [c.upper() for c in df.columns]
        
        # --- 2. FILTRERING AF FREMTIDIGE VS SPILLEDE ---
        # Vi tjekker på STATUS (hvis Opta sender den) eller om der er en score
        df['HAR_RESULTAT'] = df['TOTAL_HOME_SCORE'].notna()
        
        visning = st.radio("Vis:", ["Spillede kampe", "Kommende kampe"], horizontal=True)
        
        if visning == "Spillede kampe":
            df = df[df['HAR_RESULTAT'] == True]
        else:
            df = df[df['HAR_RESULTAT'] == False]

        # Dato sortering
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE', 'DATO'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            df = df.sort_values(by=dato_col, ascending=(visning == "Kommende kampe"))

        # Hold vælger
        liga_hold = sorted(list(set(df['CONTESTANTHOME_NAME'].dropna()) | set(df['CONTESTANTAWAY_NAME'].dropna())))
        valgt_hold = st.selectbox("Vælg hold:", ["Alle hold"] + liga_hold)

        # Basis formatering
        df['KAMP'] = df['CONTESTANTHOME_NAME'].astype(str) + " - " + df['CONTESTANTAWAY_NAME'].astype(str)
        df['RESULTAT'] = df.apply(lambda r: f"{format_score(r.get('TOTAL_HOME_SCORE'))} - {format_score(r.get('TOTAL_AWAY_SCORE'))}" if r['HAR_RESULTAT'] else "-", axis=1)
        df['DATO_STR'] = df[dato_col].dt.strftime('%d-%m-%Y') if dato_col else ""

        # --- 3. KOLONNE-VÆLGER (KUN VED ENKELT HOLD) ---
        vis_stats = []
        if valgt_hold != "Alle hold" and visning == "Spillede kampe":
            st.markdown("---")
            # Her kan brugeren vælge de oversatte navne
            mulige_stats = list(OPTA_MAP.values())
            vis_stats = st.multiselect("Vælg statistikker der skal vises:", mulige_stats, default=mulige_stats[:4])

        # --- 4. DATA VISNING ---
        if valgt_hold == "Alle hold":
            st.dataframe(df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)
        else:
            f_df = df[(df['CONTESTANTHOME_NAME'] == valgt_hold) | (df['CONTESTANTAWAY_NAME'] == valgt_hold)].copy()
            
            if not df_stats.empty and visning == "Spillede kampe":
                ds = df_stats.copy()
                ds.columns = [c.upper() for c in ds.columns]
                
                match_list = []
                for _, m in f_df.iterrows():
                    m_id = m.get('MATCH_OPTAUUID')
                    is_home = m['CONTESTANTHOME_NAME'] == valgt_hold
                    t_id = m.get('CONTESTANTHOME_OPTAUUID') if is_home else m.get('CONTESTANTAWAY_OPTAUUID')
                    
                    row = {"Dato": m['DATO_STR'], "Kamp": m['KAMP'], "Resultat": m['RESULTAT']}
                    
                    # Hent rå stats og oversæt dem
                    m_s = ds[(ds['MATCH_OPTAUUID'] == m_id) & (ds['CONTESTANT_OPTAUUID'] == t_id)]
                    for _, s_row in m_s.iterrows():
                        raw_name = s_row['STAT_TYPE']
                        # Hvis navnet findes i vores map, så brug det danske navn
                        if raw_name in OPTA_MAP:
                            dan_name = OPTA_MAP[raw_name]
                            if dan_name in vis_stats: # Vis kun hvis valgt i multiselect
                                row[dan_name] = s_row['STAT_TOTAL']
                    
                    match_list.append(row)

                final_df = pd.DataFrame(match_list)
                st.dataframe(final_df, use_container_width=True, hide_index=True)
            else:
                st.dataframe(f_df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Fejl i visning: {e}")
