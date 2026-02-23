import streamlit as st
import pandas as pd
import os

def super_clean(text):
    """Den ultimative vaskemaskine til danske tegn i CSV-eksport"""
    if not isinstance(text, str):
        return text
    
    # Liste over de præcise symboler der opstår ved fejl-encoding
    rep = {
        "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å",
        "√º": "ü", "√ñ": "Ö",
        "Ã¦": "æ", "Ã¸": "ø", "Ã¥": "å",
        "Ã†": "Æ", "Ã˜": "Ø", "Ã…": "Å",
        "Ã¼": "ü"
    }
    for wrong, right in rep.items():
        text = text.replace(wrong, right)
    return text

def vis_side():
    st.markdown("""
        <style>
            [data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-start; }
            .stDataFrame { border: none; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">TEST: SPILLERSTATISTIK</h3>
    </div>""", unsafe_allow_html=True)
    
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        # Vi tvinger indlæsningen til at være mere fleksibel
        try:
            # Vi prøver 'utf-8-sig' først (håndterer Excel UTF-8)
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except:
            # Hvis det fejler, bruger vi 'latin-1' som er meget almindelig for danske Excel-filer
            df = pd.read_csv(csv_path, encoding='latin-1')
        
        # Vi kører ALLE tekstkolonner igennem vaskemaskinen
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).apply(super_clean)
            
        # Saml Navn
        df['Navn'] = df['FIRSTNAME'].replace('nan', '') + ' ' + df['LASTNAME'].replace('nan', '')
        
        # --- FILTRE ---
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            hold = ["Alle"] + sorted([x for x in df['COMPETITIONNAME'].unique() if x != 'nan'])
            valgt_hold = st.selectbox("Turnering", hold)
        with col2:
            roller = ["Alle"] + sorted([x for x in df['ROLECODE3'].unique() if x != 'nan'])
            valgt_rolle = st.selectbox("Position", roller)
        with col3:
            visningstype = st.radio("Datatype", ["Total", "Pr. 90"], horizontal=True)

        df_filt = df.copy()
        if valgt_hold != "Alle":
            df_filt = df_filt[df_filt['COMPETITIONNAME'] == valgt_hold]
        if valgt_rolle != "Alle":
            df_filt = df_filt[df_filt['ROLECODE3'] == valgt_rolle]

        stats_groups = {
            "Generelt": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
            "Offensivt": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
            "Defensivt": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'SLIDINGTACKLES'],
            "Pasninger": ['PASSES', 'SUCCESSFULPASSES', 'CROSSES', 'PROGRESSIVEPASSES']
        }

        tabs = st.tabs(list(stats_groups.keys()))

        for i, (group_name, cols) in enumerate(stats_groups.items()):
            with tabs[i]:
                display_cols = ['Navn', 'ROLECODE3', 'MINUTESONFIELD'] + [c for c in cols if c in df_filt.columns]
                df_tab = df_filt[display_cols].copy()

                # Konverter tal-kolonner for at undgå fejl ved beregning
                df_tab['MINUTESONFIELD'] = pd.to_numeric(df_tab['MINUTESONFIELD'], errors='coerce').fillna(0)
                for c in cols:
                    if c in df_tab.columns:
                        df_tab[c] = pd.to_numeric(df_tab[c], errors='coerce').fillna(0)

                if visningstype == "Pr. 90":
                    for c in cols:
                        if c in df_tab.columns:
                            df_tab[c] = (df_tab[c] / df_tab['MINUTESONFIELD'] * 90).replace([float('inf'), -float('inf')], 0).round(2).fillna(0)

                calc_height = (len(df_tab) + 1) * 35 + 45
                
                st.dataframe(
                    df_tab,
                    use_container_width=True,
                    hide_index=True,
                    height=calc_height,
                    column_config={
                        "Navn": st.column_config.TextColumn("Spiller"),
                        "ROLECODE3": st.column_config.TextColumn("Pos"),
                        "MINUTESONFIELD": st.column_config.NumberColumn("Min", format="%d"),
                        **{c: st.column_config.NumberColumn(c, format="%.2f" if visningstype == "Pr. 90" else "%d") for c in cols}
                    }
                )
    else:
        st.error(f"Filen mangler: {csv_path}")
