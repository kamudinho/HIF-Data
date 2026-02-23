import streamlit as st
import pandas as pd
import os

def super_clean(text):
    if not isinstance(text, str): return text
    rep = {
        "ƒç": "č", "ƒá": "ć", "≈°": "š", "≈æ": "ž", "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å", "√Å": "Á", "√©": "é", "√∂": "ö", "√º": "ü"
    }
    for wrong, right in rep.items(): text = text.replace(wrong, right)
    return text

def vis_side():
    st.markdown("<style>.stDataFrame {border: none;} button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}</style>", unsafe_allow_html=True)

    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">TEST: HOLDSTATISTIK</h3>
    </div>""", unsafe_allow_html=True)
    
    csv_path = "data/testdata/teams.csv"
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except:
            df = pd.read_csv(csv_path, encoding='latin-1')

        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(super_clean)

        # Filtre
        ligaer = ["Alle"] + sorted([str(x) for x in df['SEASONNAME'].unique() if pd.notna(x)])
        valgt_liga = st.selectbox("Sæson / Liga", ligaer)
        
        df_filt = df.copy()
        if valgt_liga != "Alle": df_filt = df_filt[df_filt['SEASONNAME'] == valgt_liga]

        # Gruppering af de mange kolonner
        team_stats = {
            "Overblik": ['TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALGOALSFOR', 'TOTALGOALSAGAINST', 'TOTALPOINTS'],
            "Angreb": ['TEAMNAME', 'GOALS', 'XGSHOT', 'SHOTS', 'PROGRESSIVERUN', 'TOUCHINBOX', 'CROSSES'],
            "Forsvar": ['TEAMNAME', 'CONCEDEDGOALS', 'DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'XGSHOTAGAINST', 'PPDA'],
            "Pasninger": ['TEAMNAME', 'PASSES', 'SUCCESSFULPASSES', 'LONGPASSES', 'THROUGHPASSES', 'PASSESTOFINALTHIRD']
        }

        tabs = st.tabs(list(team_stats.keys()))

        for i, (group_name, cols) in enumerate(team_stats.items()):
            with tabs[i]:
                # Vi sikrer os at kolonnerne findes i CSV'en
                available_cols = [c for c in cols if c in df_filt.columns]
                df_display = df_filt[available_cols]

                calc_height = (len(df_display) + 1) * 35 + 45
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    height=calc_height,
                    column_config={
                        "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                        "TOTALPOINTS": st.column_config.NumberColumn("Point"),
                        "TOTALGOALSFOR": st.column_config.NumberColumn("Mål For"),
                        "XGSHOT": st.column_config.NumberColumn("xG", format="%.2f"),
                        "PPDA": st.column_config.NumberColumn("PPDA", format="%.2f")
                    }
                )
    else:
        st.error(f"Filen mangler: {csv_path}")
