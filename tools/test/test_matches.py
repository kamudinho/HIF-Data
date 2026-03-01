import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(data_package):
    st.subheader("KAMPOVERSIGT")
    
    df_matches = data_package.get("opta_matches")
    df_stats = data_package.get("opta_stats")
    
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata fundet i 'opta_matches'.")
        return

    try:
        # Tving alle navne til UPPERCASE for at undgå 'Match_Id' vs 'MATCH_ID' fejl
        df = df_matches.copy()
        df.columns = [c.upper() for c in df.columns]
        
        # --- FILTRE ---
        visning = st.radio("Vis:", ["Spillede kampe", "Kommende kampe"], horizontal=True)
        
        # Find dato kolonne
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE', 'DATO'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            df = df.sort_values(by=dato_col, ascending=False)

        # Hold vælger
        liga_hold = sorted(list(set(df['CONTESTANTHOME_NAME'].dropna()) | set(df['CONTESTANTAWAY_NAME'].dropna())))
        valgt_hold = st.selectbox("Vælg hold:", ["Alle hold"] + liga_hold)

        # Basis formatering
        df['KAMP'] = df['CONTESTANTHOME_NAME'].astype(str) + " - " + df['CONTESTANTAWAY_NAME'].astype(str)
        df['RESULTAT'] = df.apply(lambda r: f"{int(r.get('TOTAL_HOME_SCORE') or 0)} - {int(r.get('TOTAL_AWAY_SCORE') or 0)}" if visning == "Spillede kampe" else "-", axis=1)        
        df['DATO_STR'] = df[dato_col].dt.strftime('%d-%m-%Y') if dato_col else ""

        if valgt_hold == "Alle hold":
            st.dataframe(df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)
        else:
            f_df = df[(df['CONTESTANTHOME_NAME'] == valgt_hold) | (df['CONTESTANTAWAY_NAME'] == valgt_hold)].copy()
            
            # BYG DEN BREDE TABEL
            if df_stats is not None and not df_stats.empty:
                ds = df_stats.copy()
                ds.columns = [c.upper() for c in ds.columns]
                
                match_list = []
                for _, m in f_df.iterrows():
                    m_id = m.get('MATCH_OPTAUUID')
                    # Find holdets ID - vi tjekker begge muligheder
                    is_home = m['CONTESTANTHOME_NAME'] == valgt_hold
                    t_id = m.get('CONTESTANTHOME_OPTAUUID') if is_home else m.get('CONTESTANTAWAY_OPTAUUID')
                    
                    row = {"Dato": m['DATO_STR'], "Kamp": m['KAMP'], "Resultat": m['RESULTAT']}
                    
                    # Filtrér stats
                    m_s = ds[(ds['MATCH_OPTAUUID'] == m_id) & (ds['CONTESTANT_OPTAUUID'] == t_id)]
                    
                    for _, s_row in m_s.iterrows():
                        row[s_row['STAT_TYPE']] = s_row['STAT_TOTAL']
                    
                    match_list.append(row)

                final_df = pd.DataFrame(match_list)
                st.dataframe(final_df, use_container_width=True, hide_index=True)
            else:
                st.write("Viser kun basisdata (Ingen Opta stats fundet i pakken)")
                st.dataframe(f_df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Fejl i visning: {e}")
