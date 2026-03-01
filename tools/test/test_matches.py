import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(dp):
    st.subheader("KAMPOVERSIGT")
    
    # 1. HENT DATA
    df_matches = dp.get("opta_matches", pd.DataFrame()).copy()
    df_stats = dp.get("opta_stats", pd.DataFrame()).copy()
    
    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    try:
        # Sørg for UPPERCASE kolonner for konsistens
        df_matches.columns = [c.upper() for c in df_matches.columns]
        if not df_stats.empty:
            df_stats.columns = [c.upper() for c in df_stats.columns]

        # --- DATO & TOGGLE ---
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE'] if c in df_matches.columns), None)
        visning = st.radio("Vis:", ["Spillede kampe", "Kommende kampe"], horizontal=True)

        if dato_col:
            df_matches[dato_col] = pd.to_datetime(df_matches[dato_col])
            nu = datetime.now()
            df_matches = df_matches[df_matches[dato_col] <= nu] if visning == "Spillede kampe" else df_matches[df_matches[dato_col] > nu]
            df_matches = df_matches.sort_values(by=dato_col, ascending=(visning == "Kommende kampe"))

        # --- HOVEDTABEL ---
        df_matches['KAMP'] = df_matches['CONTESTANTHOME_NAME'] + " - " + df_matches['CONTESTANTAWAY_NAME']
        df_matches['RESULTAT'] = df_matches.apply(lambda r: f"{int(r.get('TOTAL_HOME_SCORE', 0))} - {int(r.get('TOTAL_AWAY_SCORE', 0))}" if visning == "Spillede kampe" else "-", axis=1)
        df_matches['DATO_STR'] = df_matches[dato_col].dt.strftime('%d-%m-%Y')

        st.dataframe(df_matches[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)

        # --- DYB STATISTIK (PIVOTERING AF STAT_TYPE) ---
        if visning == "Spillede kampe" and not df_stats.empty:
            st.markdown("---")
            valgt_label = st.selectbox("Vælg kamp for detaljeret statistik:", df_matches['KAMP'].tolist())
            
            # Find kampens UUID
            match_row = df_matches[df_matches['KAMP'] == valgt_label].iloc[0]
            m_uuid = match_row.get('MATCH_OPTAUUID')
            
            # Filtrer stats for kampen
            m_stats = df_stats[df_stats['MATCH_OPTAUUID'] == m_uuid].copy()
            
            if not m_stats.empty:
                h_id = match_row.get('CONTESTANTHOME_OPTAUUID')
                a_id = match_row.get('CONTESTANTAWAY_OPTAUUID')
                h_navn = match_row.get('CONTESTANTHOME_NAME')
                a_navn = match_row.get('CONTESTANTAWAY_NAME')

                # Pivotering: Vi transformerer STAT_TYPE rækker til kolonner
                # Vi tager kun de vigtigste stats for at holde det overskueligt
                pivot_df = m_stats.pivot(index='STAT_TYPE', columns='CONTESTANT_OPTAUUID', values='STAT_TOTAL')
                
                # Omdøb kolonner fra UUID til holdnavne
                pivot_df = pivot_df.rename(columns={h_id: h_navn, a_id: a_navn})
                
                # Vælg kun de relevante rækker (stats) hvis de findes
                vigtige_stats = [
                    'possessionPercentage', 'totalScoringAtt', 'ontargetScoringAtt', 
                    'accuratePass', 'totalPass', 'wonCorners', 'totalTackle', 
                    'formationUsed', 'totalYellowCard'
                ]
                
                final_stats = pivot_df[pivot_df.index.isin(vigtige_stats)].copy()
                
                # Gør index (Stat-navnet) til en almindelig kolonne og omdøb den
                final_stats.index.name = 'STATISTIK'
                final_stats = final_stats.reset_index()

                st.write(f"### Statistik: {h_navn} vs {a_navn}")
                st.table(final_stats)
                
            else:
                st.info("Ingen dyb statistik fundet for denne kamp.")

    except Exception as e:
        st.error(f"Fejl i generering af kampoversigt: {e}")
