import streamlit as st
import pandas as pd
from data.data_load import load_snowflake_query

# --- 1. NAVNE-VASKER (Håndterer Ísak Snær og andre specialtegn) ---
def super_clean(text):
    if not isinstance(text, str) or text == 'None' or text == 'nan':
        return ""
    rep = {
        "√ç": "Í", "√û": "Þ", "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å", "Ã¦": "æ", "Ã¸": "ø", "Ã¥": "å",
        "Ã†": "Æ", "Ã˜": "Ø", "Ã…": "Å", "√Å": "Á", "√©": "é", "Ã©": "é"
    }
    for wrong, right in rep.items():
        text = text.replace(wrong, right)
    return text.strip()

def vis_side():
    # --- 1. SESSION DATA ---
    if "data_package" in st.session_state:
        dp = st.session_state["data_package"]
    else:
        st.error("Kunne ikke indlæse systemdata. Prøv at genindlæse siden.")
        return
        
    # --- 2. CSS STYLING ---
    st.markdown("""
        <style>
            [data-testid="stHeaderTableCell"] { text-align: center !important; }
            .custom-header {
                background-color: #cc0000; padding: 15px; border-radius: 8px; 
                margin-bottom: 20px; text-align: center; color: white;
            }
            .custom-header h3 { margin: 0 !important; text-transform: uppercase; letter-spacing: 1px; }
            button[data-baseweb="tab"][aria-selected="true"] { color: #cc0000 !important; border-bottom-color: #cc0000 !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="custom-header"><h3>SPILLERSTATISTIK</h3></div>', unsafe_allow_html=True)
    
    # --- 3. DATA LOADING ---
    with st.spinner("Henter data fra Snowflake..."):
        df_raw = load_snowflake_query("playerstats", dp["comp_filter"], dp["season_filter"])

    if df_raw is None or df_raw.empty:
        st.warning("Ingen spillerdata fundet for denne sæson.")
        return

    df = df_raw.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]

    # --- 4. NAVNE-LOGIK (FIRSTNAME + LASTNAME = NAVN) ---
    # Vi tjekker alle varianter af kolonnenavne for at undgå 'Ukendt Spiller'
    if 'FIRSTNAME' in df.columns and 'LASTNAME' in df.columns:
        df['NAVN'] = (
            df['FIRSTNAME'].apply(super_clean) + " " + df['LASTNAME'].apply(super_clean)
        ).str.strip()
    elif 'PLAYERNAME' in df.columns:
        df['NAVN'] = df['PLAYERNAME'].apply(super_clean)
    elif 'SHORTNAME' in df.columns:
        df['NAVN'] = df['SHORTNAME'].apply(super_clean)
    else:
        df['NAVN'] = "Navn ikke fundet"

    # Sikre at vi har billedkolonne (bruger dit alias fra queries.py)
    if 'IMAGEURLDATA' not in df.columns:
        # Hvis den hedder noget andet i Snowflake endnu
        if 'IMAGEDATAURL' in df.columns:
            df.rename(columns={'IMAGEDATAURL': 'IMAGEURLDATA'}, inplace=True)
        else:
            df['IMAGEURLDATA'] = None

    # --- 5. INTERFACE (FILTER & TABS) ---
    nav_col1, nav_col2 = st.columns([4, 2])
    pos_labels = ["ALLE", "GKP", "DEF", "MID", "FWD"]
    
    with nav_col1:
        tabs_pos = st.tabs(pos_labels)
    with nav_col2:
        visningstype = st.radio("VISNING", ["TOTAL", "PR. 90"], horizontal=True, label_visibility="collapsed")

    # Kolonne-grupper baseret på din Snowflake tabel
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
            
            # Position filter (ROLECODE3 er Wyscout standard)
            if valgt_pos != "ALLE" and 'ROLECODE3' in df_filt.columns:
                df_filt = df_filt[df_filt['ROLECODE3'] == valgt_pos]

            stat_tabs = st.tabs(list(stats_groups.keys()))
            
            for s_idx, (group_name, cols) in enumerate(stats_groups.items()):
                with stat_tabs[s_idx]:
                    # Find de kolonner der faktisk findes i dit SQL-træk
                    available_stats = [c for c in cols if c in df_filt.columns]
                    
                    # Definer hvad der skal vises i tabellen
                    display_cols = ['IMAGEURLDATA', 'NAVN', 'MINUTESONFIELD'] + available_stats
                    # Fjern kolonner der ikke findes i datasættet for at undgå 'Not in Index' fejl
                    final_cols = [c for c in display_cols if c in df_filt.columns]
                    
                    df_tab = df_filt[final_cols].copy()

                    # Beregn pr. 90 hvis valgt
                    if visningstype == "PR. 90" and 'MINUTESONFIELD' in df_tab.columns:
                        for c in available_stats:
                            df_tab[c] = pd.to_numeric(df_tab[c], errors='coerce').fillna(0)
                            df_tab['MINUTESONFIELD'] = pd.to_numeric(df_tab['MINUTESONFIELD'], errors='coerce').fillna(0)
                            mask = df_tab['MINUTESONFIELD'] > 0
                            df_tab.loc[mask, c] = (df_tab.loc[mask, c] / df_tab.loc[mask, 'MINUTESONFIELD'] * 90)
                            df_tab[c] = df_tab[c].round(2)

                    # --- TABEL VISNING ---
                    # Beregn højde dynamisk så vi slipper for scrollbars
                    df_height = (len(df_tab) + 1) * 35 + 45
                    
                    st.dataframe(
                        df_tab.sort_values(by=available_stats[0] if available_stats else 'NAVN', ascending=False),
                        use_container_width=True,
                        hide_index=True,
                        height=min(df_height, 800),
                        column_config={
                            "IMAGEURLDATA": st.column_config.ImageColumn("", width="small"),
                            "NAVN": st.column_config.TextColumn("SPILLER", width="medium"),
                            "MINUTESONFIELD": st.column_config.NumberColumn("MIN", format="%d"),
                            **{c: st.column_config.NumberColumn(c, format="%.2f" if visningstype == "PR. 90" else "%d") for c in available_stats}
                        }
                    )
