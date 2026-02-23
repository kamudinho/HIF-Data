import streamlit as st
import pandas as pd
import os

def super_clean(text):
    if not isinstance(text, str): return text
    rep = {
        "ƒç": "č", "ƒá": "ć", "≈°": "š", "≈æ": "ž", "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å", "√Å": "Á", "√©": "é", "√∂": "ö", "√º": "ü", "Yat√©k√©": "Yatéké"
    }
    for wrong, right in rep.items(): text = text.replace(wrong, right)
    return text

def vis_side():
    st.markdown("<style>[data-testid='column'] {display: flex; flex-direction: column;} .stDataFrame {border: none;}</style>", unsafe_allow_html=True)

    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">TEST: KAMPSTATISTIK</h3>
    </div>""", unsafe_allow_html=True)
    
    csv_path = "data/testdata/matches.csv"
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except:
            df = pd.read_csv(csv_path, encoding='latin-1')

        # Rens tekst
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(super_clean)

        # Filtre
        col1, col2 = st.columns(2)
        with col1:
            turnering = ["Alle"] + sorted([str(x) for x in df['COMPETITION_NAME'].unique() if pd.notna(x)])
            valgt_turnering = st.selectbox("Turnering", turnering)
        with col2:
            hold = ["Alle"] + sorted([str(x) for x in df['TEAMNAME'].unique() if pd.notna(x)])
            valgt_hold = st.selectbox("Hold", hold)

        df_filt = df.copy()
        if valgt_turnering != "Alle": df_filt = df_filt[df_filt['COMPETITION_NAME'] == valgt_turnering]
        if valgt_hold != "Alle": df_filt = df_filt[df_filt['TEAMNAME'] == valgt_hold]

        # Udvalgte kolonner til visning
        vis_cols = ['DATE', 'MATCHLABEL', 'GOALS', 'XG', 'SHOTS', 'SHOTSONTARGET', 'CORNERS', 'YELLOWCARDS']
        df_display = df_filt[[c for c in vis_cols if c in df_filt.columns]]

        calc_height = (len(df_display) + 1) * 35 + 45
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=calc_height,
            column_config={
                "DATE": st.column_config.TextColumn("Dato"),
                "MATCHLABEL": st.column_config.TextColumn("Kamp & Resultat", width="large"),
                "GOALS": st.column_config.NumberColumn("Mål"),
                "XG": st.column_config.NumberColumn("xG", format="%.2f"),
                "SHOTS": st.column_config.NumberColumn("Skud"),
                "SHOTSONTARGET": st.column_config.NumberColumn("På mål")
            }
        )
    else:
        st.error(f"Filen mangler: {csv_path}")
