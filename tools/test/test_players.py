import streamlit as st
import pandas as pd
import os

def vis_side():
    # 1. CSS (Matcher trupoversigtens layout)
    st.markdown("""
        <style>
            [data-testid="column"] {
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            }
            .stDataFrame { border: none; }
        </style>
    """, unsafe_allow_html=True)

    # 2. BRANDING BOKS
    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">TEST: SPILLERSTATISTIK</h3>
    </div>""", unsafe_allow_html=True)
    
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        # Vi indlæser med utf-8-sig for at håndtere danske tegn korrekt
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        
        # Samler Navn og sikrer rene strenge
        df['Navn'] = df['FIRSTNAME'].fillna('') + ' ' + df['LASTNAME'].fillna('')
        
        # --- 3. FILTRE ---
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

        # Definition af stats grupper
        stats_groups = {
            "Generelt": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
            "Offensivt": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
            "Defensivt": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'SLIDINGTACKLES'],
            "Pasninger": ['PASSES', 'SUCCESSFULPASSES', 'CROSSES', 'PROGRESSIVEPASSES']
        }

        # --- 4. FANER ---
        tabs = st.tabs(list(stats_groups.keys()))

        for i, (group_name, cols) in enumerate(stats_groups.items()):
            with tabs[i]:
                display_cols = ['Navn', 'ROLECODE3', 'MINUTESONFIELD'] + cols
                df_tab = df_filt[display_cols].copy()

                if visningstype == "Pr. 90":
                    for c in cols:
                        df_tab[c] = (df_tab[c] / df_tab['MINUTESONFIELD'] * 90).round(2)
                        df_tab.loc[df_tab['MINUTESONFIELD'] == 0, c] = 0

                # Dynamisk højde til fuld længde
                calc_height = (len(df_tab) + 1) * 35 + 2
                
                st.dataframe(
                    df_tab,
                    use_container_width=True,
                    hide_index=True,
                    height=calc_height,
                    column_config={
                        "Navn": st.column_config.TextColumn("Spiller"),
                        "ROLECODE3": st.column_config.TextColumn("Pos"),
                        "MINUTESONFIELD": st.column_config.NumberColumn("Min"),
                        **{c: st.column_config.NumberColumn(c, format="%.2f" if visningstype == "Pr. 90" else "%d") for c in cols}
                    }
                )
    else:
        st.error(f"Filen mangler: {csv_path}")
