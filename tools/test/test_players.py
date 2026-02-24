import streamlit as st
import pandas as pd
from data.data_load import load_snowflake_query

# --- 1. DEN ULTIMATIVE VASKEMASKINE ---
def super_clean(text):
    if not isinstance(text, str):
        return text
    rep = {
        "√ç": "Í", "√û": "Þ", "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å", "ƒç": "č", "ƒá": "ć", 
        "≈°": "š", "≈æ": "ž", "Ã¦": "æ", "Ã¸": "ø", "Ã¥": "å",
        "Ã†": "Æ", "Ã˜": "Ø", "Ã…": "Å", "√Å": "Á", "√©": "é", 
        "√∂": "ö", "√º": "ü", "√ñ": "Ö", "Ã©": "é", "Ã¡": "Á", 
        "Ã¶": "ö", "√≠": "í", "√≥": "ó", "√∫": "ú", "√Ω": "ý"
    }
    for wrong, right in rep.items():
        text = text.replace(wrong, right)
    return text

def vis_side():
    # 2. CSS FOR DESIGN & CENTRERING
    st.markdown("""
        <style>
            .stDataFrame { border: none; }
            [data-testid="stHeaderTableCell"] { text-align: center !important; display: flex; justify-content: center; }
            button[data-baseweb="tab"] { font-size: 14px; }
            button[data-baseweb="tab"][aria-selected="true"] { color: #cc0000; border-bottom-color: #cc0000; }
            div[data-testid="stRadio"] > div { gap: 15px; padding-top: 5px; }
            .custom-header {
                background-color: #cc0000; padding: 15px; border-radius: 4px; 
                margin-bottom: 20px; text-align: center; color: white;
            }
            .custom-header h3 { margin: 0 !important; color: white !important; text-transform: uppercase; font-size: 1.2rem; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="custom-header"><h3>SPILLERSTATISTIK</h3></div>', unsafe_allow_html=True)
    
    # --- 3. DATA LOADING FRA SNOWFLAKE ---
    if "data_package" not in st.session_state:
        st.error("Data package ikke fundet. Genindlæs siden.")
        return
    
    dp = st.session_state["data_package"]
    
    # Vi bruger query 'playerstats' som er defineret i din queries.py
    with st.spinner("Henter spillerdata..."):
        df_raw = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])

    if df_raw is None or df_raw.empty:
        st.warning("⚠️ Ingen data fundet i Snowflake for de valgte filtre.")
        return

    # Klargøring af DataFrame
    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Vask tekst og navne
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).apply(super_clean)

    # Navn og Billede check
    # Hvis 'IMAGEURLDATA' ikke findes i SQL, opretter vi den som tom for at undgå fejl
    if 'IMAGEURLDATA' not in df.columns:
        df['IMAGEURLDATA'] = ""
    
    # Sammensæt navn hvis FIRSTNAME/LASTNAME findes
    if 'FIRSTNAME' in df.columns and 'LASTNAME' in df.columns:
        df['NAVN'] = (df['FIRSTNAME'].replace('nan', '') + ' ' + df['LASTNAME'].replace('nan', '')).str.strip()
    elif 'PLAYERNAME' in df.columns:
        df['NAVN'] = df['PLAYERNAME']
    else:
        df['NAVN'] = "Ukendt Spiller"

    # --- 4. FILTRE & TABS ---
    nav_col1, nav_col2 = st.columns([4, 2])
    pos_labels = ["ALLE", "GKP", "DEF", "MID", "FWD"]
    
    with nav_col1:
        tabs_pos = st.tabs(pos_labels)
    with nav_col2:
        visningstype = st.radio("VISNING", ["TOTAL", "PR. 90"], horizontal=True, label_visibility="collapsed")

    # Statistik grupper (Matcher kolonnenavne fra din Snowflake tabel)
    stats_groups = {
        "GENERELT": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
        "OFFENSIVT": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
        "DEFENSIVT": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'SLIDINGTACKLES'],
        "PASNINGER": ['PASSES', 'SUCCESSFULPASSES', 'CROSSES', 'PROGRESSIVEPASSES']
    }

    for idx, p_tab in enumerate(tabs_pos):
        with p_tab:
            valgt_pos = pos_labels[idx]
            df_filt = df.copy()
            
            if valgt_pos != "ALLE":
                # Tjekker om ROLECODE3 eller POSITION findes
                pos_col = 'ROLECODE3' if 'ROLECODE3' in df.columns else 'POSITION'
                if pos_col in df_filt.columns:
                    df_filt = df_filt[df_filt[pos_col] == valgt_pos]

            stat_tabs = st.tabs(list(stats_groups.keys()))
            
            for s_idx, (group_name, cols) in enumerate(stats_groups.items()):
                with stat_tabs[s_idx]:
                    # Find de kolonner der rent faktisk er med i queryen
                    available_stats = [c for c in cols if c in df_filt.columns]
                    display_cols = ['IMAGEURLDATA', 'NAVN', 'MINUTESONFIELD'] + available_stats
                    
                    df_tab = df_filt[display_cols].copy()

                    # Konvertering til tal
                    df_tab['MINUTESONFIELD'] = pd.to_numeric(df_tab['MINUTESONFIELD'], errors='coerce').fillna(0)
                    for c in available_stats:
                        df_tab[c] = pd.to_numeric(df_tab[c], errors='coerce').fillna(0)

                    # Beregning af Pr. 90
                    if visningstype == "PR. 90":
                        for c in available_stats:
                            mask = df_tab['MINUTESONFIELD'] > 0
                            df_tab.loc[mask, c] = (df_tab.loc[mask, c] / df_tab.loc[mask, 'MINUTESONFIELD'] * 90)
                            df_tab[c] = df_tab[c].round(2)

                    # --- TABEL VISNING ---
                    df_height = (len(df_tab) + 1) * 35 + 50
                    if df_height < 150: df_height = 150
                    if df_height > 800: df_height = 800 # Valgfri: Sæt en max højde hvis listen er enorm

                    st.dataframe(
                        df_tab.sort_values(by=available_stats[0] if available_stats else 'NAVN', ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        height=df_height,
                        column_config={
                            "IMAGEURLDATA": st.column_config.ImageColumn("", width="small"),
                            "NAVN": st.column_config.TextColumn("SPILLER"),
                            "MINUTESONFIELD": st.column_config.NumberColumn("MIN", format="%d"),
                            **{c: st.column_config.NumberColumn(c, format="%.2f" if visningstype == "PR. 90" else "%d") for c in available_stats}
                        }
                    )
