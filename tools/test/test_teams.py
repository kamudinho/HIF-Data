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

        # Rens data
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(super_clean)

        # Konvertering
        df['GOALS'] = pd.to_numeric(df['GOALS'], errors='coerce').fillna(0)
        df['XGSHOT'] = pd.to_numeric(df['XGSHOT'], errors='coerce').fillna(0)
        df['CONCEDEDGOALS'] = pd.to_numeric(df['CONCEDEDGOALS'], errors='coerce').fillna(0)
        df['XGSHOTAGAINST'] = pd.to_numeric(df['XGSHOTAGAINST'], errors='coerce').fillna(0)

        # SAMLER xG og Diff i én kolonne (Tekst-format)
        df['xG (Diff)'] = df.apply(lambda r: f"{r['XGSHOT']:.2f} ({'+' if (r['GOALS']-r['XGSHOT']) > 0 else ''}{(r['GOALS']-r['XGSHOT']):.2f})", axis=1)
        df['xG Imod (Diff)'] = df.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({'+' if (r['XGSHOTAGAINST']-r['CONCEDEDGOALS']) > 0 else ''}{(r['XGSHOTAGAINST']-r['CONCEDEDGOALS']):.2f})", axis=1)

        # Filtre
        ligaer = ["Alle"] + sorted([str(x) for x in df['SEASONNAME'].unique() if pd.notna(x)])
        valgt_liga = st.selectbox("Sæson / Liga", ligaer)
        df_filt = df.copy()
        if valgt_liga != "Alle": df_filt = df_filt[df_filt['SEASONNAME'] == valgt_liga]

        tabs = st.tabs(["Angreb & xG", "Forsvar", "Overblik"])

        with tabs[0]:
            calc_height = (len(df_filt) + 1) * 35 + 45
            # Vi inkluderer den skjulte XGSHOT til sortering hvis man klikker på overskriften
            st.dataframe(
                df_filt[['TEAMNAME', 'GOALS', 'xG (Diff)', 'SHOTS']],
                use_container_width=True,
                hide_index=True,
                height=calc_height,
                column_config={
                    "TEAMNAME": "Hold",
                    "GOALS": st.column_config.NumberColumn("Mål"),
                    "xG (Diff)": st.column_config.TextColumn("xG (Diff)", width="medium")
                }
            )

        with tabs[1]:
            st.dataframe(
                df_filt[['TEAMNAME', 'CONCEDEDGOALS', 'xG Imod (Diff)', 'PPDA']],
                use_container_width=True,
                hide_index=True,
                height=calc_height,
                column_config={
                    "TEAMNAME": "Hold",
                    "CONCEDEDGOALS": "Mål Imod",
                    "xG Imod (Diff)": st.column_config.TextColumn("xG Imod (Diff)", width="medium")
                }
            )

        with tabs[2]:
            st.dataframe(df_filt[['TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']], use_container_width=True, hide_index=True)
    else:
        st.error("Filen mangler.")
