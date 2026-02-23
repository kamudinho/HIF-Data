import streamlit as st
import pandas as pd
import os

def vis_side():
    st.markdown("<h3 style='color: #cc0000;'>Test: Spillerstatistik</h3>", unsafe_allow_html=True)
    
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        
        # --- OPRET NAVN-KOLONNE ---
        # Samler fornavn og efternavn og fjerner de gamle kolonner
        df['Navn'] = df['FIRSTNAME'].fillna('') + ' ' + df['LASTNAME'].fillna('')
        df['Pos'] = df['ROLECODE3'].fillna('')

        
        # --- FILTRE ---
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            hold = ["Alle"] + sorted(df['COMPETITIONNAME'].unique().tolist())
            valgt_hold = st.selectbox("Turnering", hold)
        with col2:
            roller = ["Alle"] + sorted(df['ROLECODE3'].unique().tolist())
            valgt_rolle = st.selectbox("Position", roller)
        with col3:
            visningstype = st.radio("Datatype", ["Total", "Pr. 90"], horizontal=True)

        # Filtrering
        df_filt = df.copy()
        if valgt_hold != "Alle":
            df_filt = df_filt[df_filt['COMPETITIONNAME'] == valgt_hold]
        if valgt_rolle != "Alle":
            df_filt = df_filt[df_filt['ROLECODE3'] == valgt_rolle]

        # Definition af kolonne-grupper (Navn er nu med her)
        basis_cols = ['Navn', 'ROLECODE3', 'MATCHES', 'MINUTESONFIELD']
        
        stats = {
            "Generelt": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'REDCARDS'],
            "Offensivt": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES', 'SUCCESSFULDRIBBLES', 'TOUCHINBOX', 'PROGRESSIVERUN'],
            "Defensivt": ['DEFENSIVEDUELS', 'DEFENSIVEDUELSWON', 'INTERCEPTIONS', 'RECOVERIES', 'CLEARANCES', 'SLIDINGTACKLES'],
            "Pasninger": ['PASSES', 'SUCCESSFULPASSES', 'PASSESTOFINALTHIRD', 'CROSSES', 'PROGRESSIVEPASSES', 'THROUGHPASSES']
        }

        # Beregning af Pr. 90 hvis valgt
        if visningstype == "Pr. 90":
            df_display = df_filt[basis_cols].copy()
            all_stat_cols = [item for sublist in stats.values() for item in sublist]
            
            for col in all_stat_cols:
                if col in df_filt.columns:
                    # Formel: (Statistik / Minutter) * 90 - undgå division med 0
                    df_display[col] = df_filt.apply(
                        lambda row: round((row[col] / row['MINUTESONFIELD'] * 90), 2) if row['MINUTESONFIELD'] > 0 else 0, 
                        axis=1
                    )
        else:
            all_needed_cols = basis_cols + [item for sublist in stats.values() for item in sublist if item in df_filt.columns]
            df_display = df_filt[all_needed_cols]

        st.markdown("---")

        # --- TABS TIL KATEGORIER ---
        tab1, tab2, tab3, tab4 = st.tabs(["Generelt", "Offensivt", "Defensivt", "Pasninger"])

        with tab1:
            st.dataframe(df_display[basis_cols + [c for c in stats["Generelt"] if c in df_display.columns]], use_container_width=True, hide_index=True)
            
        with tab2:
            st.dataframe(df_display[basis_cols + [c for c in stats["Offensivt"] if c in df_display.columns]], use_container_width=True, hide_index=True)
            
        with tab3:
            st.dataframe(df_display[basis_cols + [c for c in stats["Defensivt"] if c in df_display.columns]], use_container_width=True, hide_index=True)
            
        with tab4:
            st.dataframe(df_display[basis_cols + [c for c in stats["Pasninger"] if c in df_display.columns]], use_container_width=True, hide_index=True)

    else:
        st.error(f"Kunne ikke finde filen: {csv_path}")
