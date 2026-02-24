import streamlit as st
import pandas as pd
import os

# --- HJÆLPEFUNKTIONER ---
def super_clean(text):
    """Vaskemaskine til europæiske tegn (Delač, Ásgeir, Yatéké, Björk, Jørgensen)"""
    if not isinstance(text, str):
        return text
    
    rep = {
        # Østeuropæiske
        "ƒç": "č", "ƒá": "ć", "≈°": "š", "≈æ": "ž",
        # Danske tegn
        "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å",
        "Ã¦": "æ", "Ã¸": "ø", "Ã¥": "å",
        "Ã†": "Æ", "Ã˜": "Ø", "Ã…": "Å",
        # Islandske / Specialtegn
        "√Å": "Á", "√©": "é", "√∂": "ö", 
        "√º": "ü", "√ñ": "Ö",
        "Ã©": "é", "Ã¡": "Á", "Ã¶": "ö",
        "√≠": "í", "√≥": "ó", "√∫": "ú", "√Ω": "ý"
    }
    for wrong, right in rep.items():
        text = text.replace(wrong, right)
    return text

def vis_side():
    # 1. CSS FOR LAYOUT & STYLING
    st.markdown("""
        <style>
            .stDataFrame { border: none; }
            /* Gør fanerne mindre og røde når valgt */
            button[data-baseweb="tab"] { font-size: 14px; padding-left: 10px; padding-right: 10px; }
            button[data-baseweb="tab"][aria-selected="true"] { color: #cc0000; border-bottom-color: #cc0000; }
            
            /* Fjern overflødig padding i radio-knapper */
            div[data-testid="stRadio"] > div { gap: 15px; padding-top: 5px; }
            
            /* Header styling */
            .custom-header {
                background-color: #cc0000; padding: 12px; border-radius: 4px; 
                margin-bottom: 20px; text-align: center; color: white;
                font-family: sans-serif; font-weight: bold; text-transform: uppercase;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="custom-header">TEST: SPILLERSTATISTIK</div>', unsafe_allow_html=True)
    
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except:
            df = pd.read_csv(csv_path, encoding='latin-1')
        
        # Rens tekst-data
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).apply(super_clean)
        
        # Opret Navn-kolonne
        df['NAVN'] = (df['FIRSTNAME'].replace('nan', '') + ' ' + df['LASTNAME'].replace('nan', '')).str.strip()
        
        # --- NAVIGATION: POSITIONS-TABS OG DATATYPE PÅ SAMME LINJE ---
        nav_col1, nav_col2 = st.columns([4, 2])
        
        pos_labels = ["ALLE", "GKP", "DEF", "MID", "FWD"]
        
        with nav_col1:
            # Hovedtabs for positioner
            tabs_pos = st.tabs(pos_labels)
            
        with nav_col2:
            # Datatype-vælger placeret til højre for tabs
            visningstype = st.radio("VISNING", ["TOTAL", "PR. 90"], horizontal=True, label_visibility="collapsed")

        # Gruppering af statistikker
        stats_groups = {
            "GENERELT": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
            "OFFENSIVT": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
            "DEFENSIVT": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'SLIDINGTACKLES'],
            "PASNINGER": ['PASSES', 'SUCCESSFULPASSES', 'CROSSES', 'PROGRESSIVEPASSES']
        }

        # Loop gennem hver positions-tab
        for idx, p_tab in enumerate(tabs_pos):
            with p_tab:
                valgt_pos = pos_labels[idx]
                
                # Filtrer på position
                df_filt = df.copy()
                if valgt_pos != "ALLE":
                    df_filt = df_filt[df_filt['ROLECODE3'] == valgt_pos]

                # Indlejrede tabs for de forskellige stat-grupper
                stat_tabs = st.tabs(list(stats_groups.keys()))
                
                for s_idx, (group_name, cols) in enumerate(stats_groups.items()):
                    with stat_tabs[s_idx]:
                        # Udvælg og rens data til visning
                        display_cols = ['NAVN', 'ROLECODE3', 'MINUTESONFIELD'] + [c for c in cols if c in df_filt.columns]
                        df_tab = df_filt[display_cols].copy()

                        # Konverter til tal
                        df_tab['MINUTESONFIELD'] = pd.to_numeric(df_tab['MINUTESONFIELD'], errors='coerce').fillna(0)
                        for c in cols:
                            if c in df_tab.columns:
                                df_tab[c] = pd.to_numeric(df_tab[c], errors='coerce').fillna(0)

                        # Beregn PR. 90 hvis valgt
                        if visningstype == "PR. 90":
                            for c in cols:
                                if c in df_tab.columns:
                                    mask = df_tab['MINUTESONFIELD'] > 0
                                    df_tab.loc[mask, c] = (df_tab.loc[mask, c] / df_tab.loc[mask, 'MINUTESONFIELD'] * 90)
                                    df_tab.loc[~mask, c] = 0
                                    df_tab[c] = df_tab[c].round(2)

                        # --- KLARGØRING TIL TABEL ---
                        # 1. Alle kolonner til store bogstaver
                        df_tab.columns = [str(c).upper() for c in df_tab.columns]
                        upper_cols = [c.upper() for c in cols]

                        # 2. Beregn højde for at fjerne scroll (35px pr række + 40px til header)
                        df_height = (len(df_tab) + 1) * 35 + 40
                        # Sæt en fornuftig minimumshøjde
                        if df_height < 150: df_height = 150

                        # 3. Vis tabellen
                        st.dataframe(
                            df_tab.sort_values(by=upper_cols[0] if upper_cols else 'NAVN', ascending=False),
                            use_container_width=True,
                            hide_index=True,
                            height=df_height,
                            column_config={
                                "NAVN": st.column_config.TextColumn("SPILLER"),
                                "ROLECODE3": st.column_config.TextColumn("POS"),
                                "MINUTESONFIELD": st.column_config.NumberColumn("MIN", format="%d"),
                                **{c: st.column_config.NumberColumn(c, format="%.2f" if visningstype == "PR. 90" else "%d") for c in upper_cols}
                            }
                        )
    else:
        st.error(f"❌ Filen blev ikke fundet: {csv_path}")

if __name__ == "__main__":
    vis_side()
