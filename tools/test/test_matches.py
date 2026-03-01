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

        # Dato filtrering
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            nu = datetime.now()
            df = df[df[dato_col] <= nu] if visning == "Spillede kampe" else df[df[dato_col] > nu]
            df = df.sort_values(by=dato_col, ascending=(visning == "Spillede kampe"))

        # Hold vælger
        liga_hold = sorted(list(set(df['CONTESTANTHOME_NAME'].dropna()) | set(df['CONTESTANTAWAY_NAME'].dropna())))
        with col_nav2:
            hvi_index = next((i + 1 for i, h in enumerate(liga_hold) if "Hvidovre" in str(h)), 0)
            valgt_hold = st.selectbox("Filtrér på hold:", ["Alle hold"] + liga_hold, index=hvi_index)

        # Klargør labels
        df['KAMP'] = df['CONTESTANTHOME_NAME'] + " - " + df['CONTESTANTAWAY_NAME']
        df['RESULTAT'] = df.apply(lambda r: f"{int(r.get('TOTAL_HOME_SCORE', 0))} - {int(r.get('TOTAL_AWAY_SCORE', 0))}" if visning == "Spillede kampe" else "-", axis=1)
        df['DATO'] = df[dato_col].dt.strftime('%d-%m-%Y')

        # --- 2. VISNINGS-LOGIK ---

        if valgt_hold == "Alle hold":
            # SCENARIE A: Oversigt over alle hold (Simpel tabel)
            st.write("### Alle Kampe")
            st.dataframe(df[['DATO', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)
        
        else:
            # SCENARIE B: Enkelt hold (Data-tung tabel)
            st.write(f"### Statistik for {valgt_hold}")
            f_df = df[(df['CONTESTANTHOME_NAME'] == valgt_hold) | (df['CONTESTANTAWAY_NAME'] == valgt_hold)].copy()
            
            if f_df.empty:
                st.info(f"Ingen kampe fundet for {valgt_hold}")
                return

            # Her bygger vi rækkerne med stats inddraget
            match_list = []
            for _, row in f_df.iterrows():
                m_uuid = row.get('MATCH_OPTAUUID')
                # Find uuid for det valgte hold i denne kamp (kan være hjemme eller ude)
                is_home = row['CONTESTANTHOME_NAME'] == valgt_hold
                t_uuid = row['CONTESTANTHOME_OPTAUUID'] if is_home else row['CONTESTANTAWAY_OPTAUUID']
                
                # Hent alle stats for dette hold i denne kamp
                m_stats = df_stats[(df_stats['MATCH_OPTAUUID'] == m_uuid) & (df_stats['CONTESTANT_OPTAUUID'] == t_uuid)]
                
                # Vi bygger en ordbog for rækken
                match_data = {
                    "Dato": row['DATO'],
                    "Kamp": row['KAMP'],
                    "Resultat": row['RESULTAT']
                }
                
                # Tilføj alle STAT_TYPE som kolonner dynamisk
                for _, s_row in m_stats.iterrows():
                    match_data[s_row['STAT_TYPE']] = s_row['STAT_TOTAL']
                
                match_list.append(match_data)

            # Lav den store tabel
            full_stats_df = pd.DataFrame(match_list)
            
            # Flyt de vigtigste kolonner forrest
            cols = ["Dato", "Kamp", "Resultat"]
            rest_cols = [c for c in full_stats_df.columns if c not in cols]
            
            st.dataframe(full_stats_df[cols + rest_cols], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Fejl: {e}")
