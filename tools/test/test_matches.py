import streamlit as st
import pandas as pd
from datetime import datetime

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

        # --- 1. FILTRE ---
        col_nav1, col_nav2 = st.columns([2, 2])
        with col_nav1:
            visning = st.radio("Vis:", ["Spillede kampe", "Kommende kampe"], horizontal=True)

        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE', 'DATO'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            nu = datetime.now()
            df = df[df[dato_col] <= nu] if visning == "Spillede kampe" else df[df[dato_col] > nu]
            df = df.sort_values(by=dato_col, ascending=False)

        # Find alle unikke holdnavne
        liga_hold = sorted(list(set(df['CONTESTANTHOME_NAME'].dropna()) | set(df['CONTESTANTAWAY_NAME'].dropna())))
        with col_nav2:
            valgt_hold = st.selectbox("Vælg hold:", ["Alle hold"] + liga_hold)

        # Formatering af basis-tabel
        df['KAMP'] = df['CONTESTANTHOME_NAME'] + " - " + df['CONTESTANTAWAY_NAME']
        df['RESULTAT'] = df.apply(lambda r: f"{int(r.get('TOTAL_HOME_SCORE', 0))} - {int(r.get('TOTAL_AWAY_SCORE', 0))}" if visning == "Spillede kampe" else "-", axis=1)
        df['DATO_STR'] = df[dato_col].dt.strftime('%d-%m-%Y') if dato_col else ""

        # --- 2. LOGIK FOR VISNING ---
        
        if valgt_hold == "Alle hold":
            st.dataframe(df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)
        
        else:
            # Filtrér kampe for det valgte hold
            f_df = df[(df['CONTESTANTHOME_NAME'] == valgt_hold) | (df['CONTESTANTAWAY_NAME'] == valgt_hold)].copy()
            
            # Hvis vi har Opta stats, prøver vi at bygge den brede tabel
            if df_stats is not None and not df_stats.empty and visning == "Spillede kampe":
                df_s = df_stats.copy()
                df_s.columns = [c.upper() for c in df_s.columns]
                
                match_list = []
                for _, m in f_df.iterrows():
                    m_uuid = m.get('MATCH_OPTAUUID')
                    # Find holdets UUID i denne specifikke kamp
                    is_home = m['CONTESTANTHOME_NAME'] == valgt_hold
                    t_uuid = m.get('CONTESTANTHOME_OPTAUUID') if is_home else m.get('CONTESTANTAWAY_OPTAUUID')
                    
                    row = {"Dato": m['DATO_STR'], "Kamp": m['KAMP'], "Resultat": m['RESULTAT']}
                    
                    # Hent alle stats for kampen og holdet
                    stats_subset = df_s[(df_s['MATCH_OPTAUUID'] == m_uuid) & (df_s['CONTESTANT_OPTAUUID'] == t_uuid)]
                    
                    if not stats_subset.empty:
                        for _, s_row in stats_subset.iterrows():
                            row[s_row['STAT_TYPE']] = s_row['STAT_TOTAL']
                        match_list.append(row)
                    else:
                        # Hvis ingen stats findes, tilføj rækken alligevel med tomme stats
                        match_list.append(row)

                if match_list:
                    final_df = pd.DataFrame(match_list)
                    # Flyt basis-kolonner forrest
                    cols = ["Dato", "Kamp", "Resultat"]
                    other_cols = [c for c in final_df.columns if c not in cols]
                    st.dataframe(final_df[cols + other_cols], use_container_width=True, hide_index=True)
                else:
                    st.info(f"Ingen udvidet data fundet for {valgt_hold}. Viser basis-oversigt.")
                    st.dataframe(f_df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)
            else:
                # Standard visning for kommende kampe eller hvis stats mangler
                st.dataframe(f_df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Fejl: {e}")
