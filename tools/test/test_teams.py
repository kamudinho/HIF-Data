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

def color_diff(val):
    """Farver rød hvis minus, grøn hvis plus"""
    try:
        if val > 0: return 'color: #28a745; font-weight: bold;'
        elif val < 0: return 'color: #dc3545; font-weight: bold;'
    except: pass
    return ''

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

        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(super_clean)

        # --- BEREGNINGER ---
        df['GOALS'] = pd.to_numeric(df['GOALS'], errors='coerce').fillna(0)
        df['XGSHOT'] = pd.to_numeric(df['XGSHOT'], errors='coerce').fillna(0)
        df['CONCEDEDGOALS'] = pd.to_numeric(df['CONCEDEDGOALS'], errors='coerce').fillna(0)
        df['XGSHOTAGAINST'] = pd.to_numeric(df['XGSHOTAGAINST'], errors='coerce').fillna(0)

        # Beregn Diff som rene tal til farvning
        df['xG (Diff)'] = (df['GOALS'] - df['XGSHOT']).round(2)
        # For mål imod: Positiv diff er godt (man har lukket færre ind end xG)
        df['xG Imod (Diff)'] = (df['XGSHOTAGAINST'] - df['CONCEDEDGOALS']).round(2)

        # Filtre
        ligaer = ["Alle"] + sorted([str(x) for x in df['SEASONNAME'].unique() if pd.notna(x)])
        valgt_liga = st.selectbox("Sæson / Liga", ligaer)
        
        df_filt = df.copy()
        if valgt_liga != "Alle": df_filt = df_filt[df_filt['SEASONNAME'] == valgt_liga]

        team_stats = {
            "Overblik": ['TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALGOALSFOR', 'TOTALPOINTS'],
            "Angreb & xG": ['TEAMNAME', 'GOALS', 'XGSHOT', 'xG (Diff)', 'SHOTS', 'TOUCHINBOX'],
            "Forsvar": ['TEAMNAME', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'xG Imod (Diff)', 'DEFENSIVEDUELS', 'PPDA'],
            "Pasninger": ['TEAMNAME', 'PASSES', 'SUCCESSFULPASSES', 'PASSESTOFINALTHIRD']
        }

        tabs = st.tabs(list(team_stats.keys()))

        for i, (group_name, cols) in enumerate(team_stats.items()):
            with tabs[i]:
                available_cols = [c for c in cols if c in df_filt.columns or c in ['xG (Diff)', 'xG Imod (Diff)']]
                df_display = df_filt[available_cols].copy()

                # Styling af tabellen
                styled_df = df_display.style.applymap(
                    color_diff, subset=[c for c in ['xG (Diff)', 'xG Imod (Diff)'] if c in df_display.columns]
                ).format({
                    'XGSHOT': "{:.2f}",
                    'XGSHOTAGAINST': "{:.2f}",
                    'xG (Diff)': "{:+.2f}",
                    'xG Imod (Diff)': "{:+.2f}",
                    'PPDA': "{:.2f}"
                })

                calc_height = (len(df_display) + 1) * 35 + 45
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    height=calc_height,
                    column_config={
                        "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                        "xG (Diff)": st.column_config.TextColumn("xG (Diff)", help="Positiv = Overpræstation"),
                        "xG Imod (Diff)": st.column_config.TextColumn("xG Imod (Diff)", help="Positiv = Forsvaret/GK har reddet mål")
                    }
                )
    else:
        st.error(f"Filen mangler: {csv_path}")
