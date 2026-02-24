import streamlit as st
import pandas as pd
import os
from data.data_load import load_snowflake_query, get_data_package, fmt_val

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
    # 2. CSS FOR LAYOUT & CENTRERING
    st.markdown("""
        <style>
            .stDataFrame { border: none; }
            [data-testid="stHeaderTableCell"] {
                text-align: center !important;
                display: flex;
                justify-content: center;
            }
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
    
    # --- 3. DATA LOADING FRA SQL ---
    if "data_package" not in st.session_state:
        st.session_state["data_package"] = get_data_package()
    
    dp = st.session_state["data_package"]
    # Vi henter 'player_stats_full' (eller hvad din query hedder i queries.py)
    df_raw = load_snowflake_query("player_stats_full", "(328)", dp.get("season_filter", "='2025/2026'"))

    if df_raw is None or df_raw.empty:
        st.error("❌ Ingen spillerdata fundet i Snowflake.")
        return

    # Tving alle kolonner til UPPERCASE med det samme for at undgå index-fejl
    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df = df.fillna(0)

    # Rens navne og tekst
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).apply(super_clean)

    # Saml Navn og tjek for Billed-kolonne
    df['NAVN'] = (df['FIRSTNAME'].replace('0', '') + ' ' + df['LASTNAME'].replace('0', '')).str.strip()
    if 'IMAGEURLDATA' not in df.columns:
        df['IMAGEURLDATA'] = None

    # --- 4. NAVIGATION ---
    nav_col1, nav_col2 = st.columns([4, 2])
    pos_labels = ["ALLE", "GKP", "DEF", "MID", "FWD"]
    with nav_col1:
        tabs_pos = st.tabs(pos_labels)
    with nav_col2:
        visningstype = st.radio("VISNING", ["TOTAL", "PR. 90"], horizontal=True, label_visibility="collapsed")

    stats_groups = {
        "GENERELT": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
        "OFFENSIVT": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
        "DEFENSIVT": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'SLIDINGTACKLES'],
        "PASNINGER": ['PASSES', 'SUCCESSFULPASSES', 'CROSSES', 'PROGRESSIVEPASSES']
    }

    # --- 5. TABS LOGIK ---
    for idx, p_tab in enumerate(tabs_pos):
        with p_tab:
            valgt_pos = pos_labels[idx]
            df_filt = df.copy()
            if valgt_pos != "ALLE":
                # Vi antager kolonnen hedder ROLECODE3 (husk den er upper nu)
                df_filt = df_filt[df_filt['ROLECODE3'] == valgt_pos]

            stat_tabs = st.tabs(list(stats_groups.keys()))
            
            for s_idx, (group_name, cols) in enumerate(stats_groups.items()):
                with stat_tabs[s_idx]:
                    # Vælg de kolonner der faktisk findes i SQL-trækket
                    available_cols = [c for c in cols if c in df_filt.columns]
                    display_cols = ['IMAGEURLDATA', 'NAVN', 'ROLECODE3', 'MINUTESONFIELD'] + available_cols
                    df_tab = df_filt[display_cols].copy()

                    # Beregning af Pr. 90
                    if visningstype == "PR. 90":
                        for c in available_cols:
                            mask = df_tab['MINUTESONFIELD'] > 0
                            df_tab.loc[mask, c] = (pd.to_numeric(df_tab.loc[mask, c]) / pd.to_numeric(df_tab.loc[mask, 'MINUTESONFIELD']) * 90)
                            df_tab[c] = df_tab[c].round(2)

                    # Tabel højde og visning
                    df_height = (len(df_tab) + 1) * 35 + 50
                    if df_height < 150: df_height = 150

                    st.dataframe(
                        df_tab.sort_values(by=available_cols[0] if available_cols else 'NAVN', ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        height=df_height,
                        column_config={
                            "IMAGEURLDATA": st.column_config.ImageColumn("", width="small"),
                            "NAVN": st.column_config.TextColumn("SPILLER"),
                            "ROLECODE3": st.column_config.TextColumn("POS"),
                            "MINUTESONFIELD": st.column_config.NumberColumn("MIN", format="%d"),
                            **{c: st.column_config.NumberColumn(c, format="%.2f" if visningstype == "PR. 90" else "%d") for c in available_cols}
                        }
                    )

if __name__ == "__main__":
    vis_side()
