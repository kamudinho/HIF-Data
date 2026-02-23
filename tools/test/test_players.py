import streamlit as st
import pandas as pd
import os

def clean_text(text):
    """Fikser fejlbehæftet encoding som J√∏rgensen -> Jørgensen"""
    if not isinstance(text, str):
        return text
    try:
        # Denne proces "vasker" teksten ved at tvinge den gennem de rigtige formater
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text

def vis_side():
    # 1. CSS (Matcher trupoversigtens layout og fjerner ikoner)
    st.markdown("""
        <style>
            [data-testid="column"] {
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            }
            .stDataFrame { border: none; }
            /* Styling af faner så de matcher det røde tema */
            button[data-baseweb="tab"] { font-size: 14px; }
            button[data-baseweb="tab"][aria-selected="true"] { color: #cc0000; border-bottom-color: #cc0000; }
        </style>
    """, unsafe_allow_html=True)

    # 2. BRANDING BOKS (Matcher players.py)
    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">TEST: SPILLERSTATISTIK</h3>
    </div>""", unsafe_allow_html=True)
    
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        # Indlæser data - vi prøver flere encodings for at være sikre
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except:
            df = pd.read_csv(csv_path, encoding='cp1252')
        
        # Rens alle tekst-kolonner for encoding-fejl (J√∏rgensen fix)
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(clean_text)
            
        # Samler Navn efter rensning
        df['Navn'] = df['FIRSTNAME'].fillna('') + ' ' + df['LASTNAME'].fillna('')
        
        # --- 3. FILTRE ---
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            hold = ["Alle"] + sorted([str(x) for x in df['COMPETITIONNAME'].unique() if pd.notna(x)])
            valgt_hold = st.selectbox("Turnering", hold)
        with col2:
            roller = ["Alle"] + sorted([str(x) for x in df['ROLECODE3'].unique() if pd.notna(x)])
            valgt_rolle = st.selectbox("Position", roller)
        with col3:
            visningstype = st.radio("Datatype", ["Total", "Pr. 90"], horizontal=True)

        # Filtrering af rådata
        df_filt = df.copy()
        if valgt_hold != "Alle":
            df_filt = df_filt[df_filt['COMPETITIONNAME'] == valgt_hold]
        if valgt_rolle != "Alle":
            df_filt = df_filt[df_filt['ROLECODE3'] == valgt_rolle]

        # Statistik grupper
        stats_groups = {
            "Generelt": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
            "Offensivt": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
            "Defensivt": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'SLIDINGTACKLES'],
            "Pasninger": ['PASSES', 'SUCCESSFULPASSES', 'PASSESTOFINALTHIRD', 'CROSSES', 'PROGRESSIVEPASSES']
        }

        # --- 4. FANER ---
        tabs = st.tabs(list(stats_groups.keys()))

        for i, (group_name, cols) in enumerate(stats_groups.items()):
            with tabs[i]:
                # Vi viser Navn, Position og Minutter som basis
                display_cols = ['Navn', 'ROLECODE3', 'MINUTESONFIELD'] + [c for c in cols if c in df_filt.columns]
                df_tab = df_filt[display_cols].copy()

                # Pr. 90 beregning
                if visningstype == "Pr. 90":
                    for c in cols:
                        if c in df_tab.columns:
                            df_tab[c] = (df_tab[c] / df_tab['MINUTESONFIELD'] * 90).round(2)
                            df_tab.loc[df_tab['MINUTESONFIELD'] == 0, c] = 0

                # Dynamisk højde til fuld længde (ca. 35px pr række + 40px til header)
                calc_height = (len(df_tab) + 1) * 35 + 40
                
                # --- 5. TABEL VISNING ---
                st.dataframe(
                    df_tab,
                    use_container_width=True,
                    hide_index=True,
                    height=calc_height,
                    column_config={
                        "Navn": st.column_config.TextColumn("Spiller", width="medium"),
                        "ROLECODE3": st.column_config.TextColumn("Pos", width="small"),
                        "MINUTESONFIELD": st.column_config.NumberColumn("Min", format="%d"),
                        **{c: st.column_config.NumberColumn(c, format="%.2f" if visningstype == "Pr. 90" else "%d") for c in cols}
                    }
                )
    else:
        st.error(f"Kunne ikke finde filen: {csv_path}")
