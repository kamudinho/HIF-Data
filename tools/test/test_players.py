import streamlit as st
import pandas as pd
import os

def super_clean(text):
    """Den ultimative vaskemaskine til alle europæiske tegn"""
    if not isinstance(text, str):
        return text
    rep = {
        "ƒç": "č", "ƒá": "ć", "≈°": "š", "≈æ": "ž",
        "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å",
        "Ã¦": "æ", "Ã¸": "ø", "Ã¥": "å",
        "Ã†": "Æ", "Ã˜": "Ø", "Ã…": "Å",
        "√Å": "Á", "√©": "é", "√∂": "ö", 
        "√º": "ü", "√ñ": "Ö",
        "Ã©": "é", "Ã¡": "Á", "Ã¶": "ö",
        "√≠": "í", "√≥": "ó", "√∫": "ú", "√Ω": "ý"
    }
    for wrong, right in rep.items():
        text = text.replace(wrong, right)
    return text

def vis_side():
    # 1. CSS (Forbedret til at centrere radio og tabs)
    st.markdown("""
        <style>
            .stDataFrame { border: none; }
            button[data-baseweb="tab"] { font-size: 14px; }
            button[data-baseweb="tab"][aria-selected="true"] { color: #cc0000; border-bottom-color: #cc0000; }
            /* Gør radio buttons mere kompakte så de passer på linjen */
            div[data-testid="stRadio"] > div { gap: 10px; }
        </style>
    """, unsafe_allow_html=True)

    # 2. BRANDING BOKS
    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">SPILLERSTATISTIK</h3>
    </div>""", unsafe_allow_html=True)
    
    csv_path = "data/testdata/players.csv"
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except:
            df = pd.read_csv(csv_path, encoding='latin-1')
        
        # Rens alle tekst-kolonner
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).apply(super_clean)
        
        # Saml Navn
        df['Navn'] = df['FIRSTNAME'].replace('nan', '') + ' ' + df['LASTNAME'].replace('nan', '')
        df['Navn'] = df['Navn'].str.strip()

        # --- NAVIGATION LINJE (Positions-tabs + Datatype) ---
        # Vi definerer de ønskede positioner
        pos_tabs_labels = ["Alle", "GKP", "DEF", "MID", "FWD"]
        
        # Vi laver to kolonner: En bred til tabs og en smal til radio buttons
        nav_col1, nav_col2 = st.columns([4, 2])
        
        with nav_col1:
            pos_tabs = st.tabs(pos_tabs_labels)
            
        with nav_col2:
            # Flyttet herop så den står på linje med tabs
            visningstype = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True, label_visibility="collapsed")

        # Stats grupper
        stats_groups = {
            "Generelt": ['GOALS', 'ASSISTS', 'YELLOWCARDS', 'MATCHES'],
            "Offensivt": ['SHOTS', 'SHOTSONTARGET', 'XGSHOT', 'DRIBBLES'],
            "Defensivt": ['DEFENSIVEDUELS', 'INTERCEPTIONS', 'RECOVERIES', 'SLIDINGTACKLES'],
            "Pasninger": ['PASSES', 'SUCCESSFULPASSES', 'CROSSES', 'PROGRESSIVEPASSES']
        }

        # Loop gennem hver positions-tab
        for idx, p_tab in enumerate(pos_tabs):
            with p_tab:
                valgt_pos = pos_tabs_labels[idx]
                
                # Filtrer efter position
                df_pos = df.copy()
                if valgt_pos != "Alle":
                    df_pos = df_pos[df_pos['ROLECODE3'] == valgt_pos]

                # Indlejrede faner til statistikker (Generelt, Offensivt, osv.)
                stat_tabs = st.tabs(list(stats_groups.keys()))
                
                for s_idx, (group_name, cols) in enumerate(stats_groups.items()):
                    with stat_tabs[s_idx]:
                        display_cols = ['Navn', 'ROLECODE3', 'MINUTESONFIELD'] + [c for c in cols if c in df_pos.columns]
                        df_tab = df_pos[display_cols].copy()

                        # Konvertering
                        df_tab['MINUTESONFIELD'] = pd.to_numeric(df_tab['MINUTESONFIELD'], errors='coerce').fillna(0)
                        for c in cols:
                            if c in df_tab.columns:
                                df_tab[c] = pd.to_numeric(df_tab[c], errors='coerce').fillna(0)

                        # Beregning af Pr. 90
                        if visningstype == "Pr. 90":
                            for c in cols:
                                if c in df_tab.columns:
                                    # Undgå division med nul
                                    mask = df_tab['MINUTESONFIELD'] > 0
                                    df_tab.loc[mask, c] = (df_tab.loc[mask, c] / df_tab.loc[mask, 'MINUTESONFIELD'] * 90)
                                    df_tab.loc[~mask, c] = 0
                                    df_tab[c] = df_tab[c].round(2)

                        # Tabel visning
                        st.dataframe(
                            df_tab.sort_values(by=cols[0] if cols else 'Navn', ascending=False),
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Navn": st.column_config.TextColumn("Spiller"),
                                "ROLECODE3": st.column_config.TextColumn("Pos"),
                                "MINUTESONFIELD": st.column_config.NumberColumn("Min", format="%d"),
                                **{c: st.column_config.NumberColumn(c, format="%.2f" if visningstype == "Pr. 90" else "%d") for c in cols}
                            }
                        )
    else:
        st.error(f"Filen mangler: {csv_path}")

# Husk at kalde funktionen hvis du kører filen direkte
if __name__ == "__main__":
    vis_side()
