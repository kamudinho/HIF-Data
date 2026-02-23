import streamlit as st
import pandas as pd
import os

def vis_side():
    # 1. CSS der får st.dataframe til at ligne din trupoversigt
    st.markdown("""
        <style>
            /* Fjerner standard Streamlit padding */
            .stDataFrame { border: 1px solid #eee; border-radius: 4px; }
            
            /* Branding af overskriften */
            h3 { color: #cc0000; text-transform: uppercase; font-size: 1.1rem; }
            
            /* Gør tabellen ren og hvid som i players.py */
            [data-testid="stMetric"] { background-color: #fafafa; border-radius: 4px; padding: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h3>Test: Spillerstatistik</h3>")
    
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df['Navn'] = df['FIRSTNAME'].fillna('') + ' ' + df['LASTNAME'].fillna('')
        
        # --- 2. FILTRE ---
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            hold = ["Alle"] + sorted(df['COMPETITIONNAME'].unique().tolist())
            valgt_hold = st.selectbox("Turnering", hold)
        with col2:
            roller = ["Alle"] + sorted(df['ROLECODE3'].unique().tolist())
            valgt_rolle = st.selectbox("Position", roller)
        with col3:
            visningstype = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)

        # Definition af stats grupper
        stats_groups = {
            "Generelt": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
            "Offensivt": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
            "Defensivt": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'SLIDINGTACKLES'],
            "Pasninger": ['PASSES', 'SUCCESSFULPASSES', 'CROSSES', 'PROGRESSIVEPASSES']
        }

        # --- 3. DATA PROCESSING ---
        df_filt = df.copy()
        if valgt_hold != "Alle":
            df_filt = df_filt[df_filt['COMPETITIONNAME'] == valgt_hold]
        if valgt_rolle != "Alle":
            df_filt = df_filt[df_filt['ROLECODE3'] == valgt_rolle]

        # --- 4. FANER ---
        tabs = st.tabs(list(stats_groups.keys()))

        for i, (group_name, cols) in enumerate(stats_groups.items()):
            with tabs[i]:
                # Basis kolonner
                display_cols = ['Navn', 'ROLECODE3', 'MINUTESONFIELD'] + cols
                df_tab = df_filt[display_cols].copy()

                # Beregn Pr. 90 hvis valgt
                if visningstype == "Pr. 90":
                    for c in cols:
                        df_tab[c] = (df_tab[c] / df_tab['MINUTESONFIELD'] * 90).round(2)
                        # Håndter division med nul
                        df_tab.loc[df_tab['MINUTESONFIELD'] == 0, c] = 0

                # --- 5. VISNING MED INDBYGGET SORTERING ---
                # Vi bruger st.dataframe fordi den har indbygget sortering på alle kolonneoverskrifter
                st.dataframe(
                    df_tab,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Navn": st.column_config.TextColumn("Spiller", width="medium"),
                        "ROLECODE3": st.column_config.TextColumn("Pos", width="small"),
                        "MINUTESONFIELD": st.column_config.NumberColumn("Min", format="%d"),
                        **{c: st.column_config.NumberColumn(c, format="%.2f" if visningstype == "Pr. 90" else "%d") for c in cols}
                    }
                )
    else:
        st.error(f"Filen mangler: {csv_path}")
