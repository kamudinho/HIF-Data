import streamlit as st
import pandas as pd
import os

def super_clean(text):
    """Den ultimative vaskemaskine til nordiske og europæiske tegn (Björk, Ásgeir, Yatéké, Jørgensen)"""
    if not isinstance(text, str):
        return text
    
    # Udvidet ordbog over præcise symbol-fejl fra Excel/CSV eksport
    rep = {
        # Danske tegn
        "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å",
        "Ã¦": "æ", "Ã¸": "ø", "Ã¥": "å",
        "Ã†": "Æ", "Ã˜": "Ø", "Ã…": "Å",
        
        # Islandske / Specialtegn (Ásgeir, Yatéké, Björk)
        "√Å": "Á", "√©": "é", "√∂": "ö", 
        "√º": "ü", "√ñ": "Ö", "Yat√©k√©": "Yatéké",
        "Ã©": "é", "Ã¡": "Á", "Ã¶": "ö",
        "√≠": "í", "√≥": "ó", "√∫": "ú", "√Ω": "ý"
    }
    for wrong, right in rep.items():
        text = text.replace(wrong, right)
    return text

def vis_side():
    # 1. CSS (Matcher trupoversigtens layout)
    st.markdown("""
        <style>
            [data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-start; }
            .stDataFrame { border: none; }
            button[data-baseweb="tab"] { font-size: 14px; }
            button[data-baseweb="tab"][aria-selected="true"] { color: #cc0000; border-bottom-color: #cc0000; }
        </style>
    """, unsafe_allow_html=True)

    # 2. BRANDING BOKS
    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">TEST: SPILLERSTATISTIK</h3>
    </div>""", unsafe_allow_html=True)
    
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except:
            df = pd.read_csv(csv_path, encoding='latin-1')
        
        # Rens alle tekst-kolonner (vasker navne som Ásgeir, Yatéké og Björk)
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).apply(super_clean)
            
        # Saml Navn (fjerner 'nan' strenge hvis de findes)
        df['Navn'] = df['FIRSTNAME'].replace('nan', '') + ' ' + df['LASTNAME'].replace('nan', '')
        df['Navn'] = df['Navn'].str.strip()
        
        # --- 3. FILTRE ---
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            hold = ["Alle"] + sorted([str(x) for x in df['COMPETITIONNAME'].unique() if x != 'nan'])
            valgt_hold = st.selectbox("Turnering", hold)
        with col2:
            roller = ["Alle"] + sorted([str(x) for x in df['ROLECODE3'].unique() if x != 'nan'])
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

        # --- 4. FANER ---
        tabs = st.tabs(list(stats_groups.keys()))

        for i, (group_name, cols) in enumerate(stats_groups.items()):
            with tabs[i]:
                display_cols = ['Navn', 'ROLECODE3', 'MINUTESONFIELD'] + [c for c in cols if c in df_filt.columns]
                df_tab = df_filt[display_cols].copy()

                # Konverter tal-kolonner
                df_tab['MINUTESONFIELD'] = pd.to_numeric(df_tab['MINUTESONFIELD'], errors='coerce').fillna(0)
                for c in cols:
                    if c in df_tab.columns:
                        df_tab[c] = pd.to_numeric(df_tab[c], errors='coerce').fillna(0)

                # Pr. 90 beregning
                if visningstype == "Pr. 90":
                    for c in cols:
                        if c in df_tab.columns:
                            df_tab[c] = (df_tab[c] / df_tab['MINUTESONFIELD'] * 90).replace([float('inf'), -float('inf')], 0).round(2).fillna(0)

                # Dynamisk højde til fuld længde
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
