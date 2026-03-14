import streamlit as st
import pandas as pd
from mplsoccer import Pitch

# Konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

# --- 1. DATABEHANDLING (Robust version) ---
def process_sequences(df):
    if df is None or df.empty:
        return pd.DataFrame()

    # Tjek om kolonnerne findes. Hvis de hedder noget andet i din SQL, omdøber vi dem her.
    # Nogle Opta-tabeller bruger 'X' og 'Y' i stedet for 'EVENT_X'
    rename_dict = {}
    if 'X' in df.columns and 'EVENT_X' not in df.columns: rename_dict['X'] = 'EVENT_X'
    if 'Y' in df.columns and 'EVENT_Y' not in df.columns: rename_dict['Y'] = 'EVENT_Y'
    if rename_dict:
        df = df.rename(columns=rename_dict)

    # Hvis 'EVENT_X' stadig mangler efter omdøbning, må vi stoppe for at undgå KeyError
    if 'EVENT_X' not in df.columns:
        st.error("Kolonnen 'EVENT_X' blev ikke fundet i data. Tjek din SQL query.")
        return pd.DataFrame()

    # Konvertering til tal
    df['EVENT_X'] = pd.to_numeric(df['EVENT_X'], errors='coerce')
    df['EVENT_Y'] = pd.to_numeric(df['EVENT_Y'], errors='coerce')

    # Fjern rækker uden koordinater (vigtigt for index-logik)
    df = df.dropna(subset=['EVENT_X', 'EVENT_Y'])

    # Sortering
    df = df.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)

    if 'PLAYER_NAME' in df.columns:
        df['PLAYER_NAME'] = df['PLAYER_NAME'].fillna('Ukendt').str.strip()

    return df

# --- 2. SELVE SIDEN ---
def vis_side(dp):
    st.markdown(f"<style>.match-header {{ font-size: 1.4rem; font-weight: 800; color: {HIF_RED}; text-align: center; margin-bottom: 20px; text-transform: uppercase; }}</style>", unsafe_allow_html=True)

    # Hent rådata fra din dictionary
    raw_df = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
    
    # Kør processering
    df_seq = process_sequences(raw_df)
    
    if df_seq.empty:
        st.warning("Ingen sekvensdata tilgængelig.")
        return

    # Find mål
    goal_ids = df_seq[df_seq['EVENT_TYPEID'] == 16]['SEQUENCEID'].unique()
    
    if len(goal_ids) == 0:
        st.info("Ingen mål fundet.")
        return

    col_viz, col_ctrl = st.columns([2.5, 1])

    with col_ctrl:
        selected_id = st.selectbox("Vælg scoring", options=goal_ids)
        active_seq = df_seq[df_seq['SEQUENCEID'] == selected_id].copy().reset_index(drop=True)
        
        goal_res = active_seq[active_seq['EVENT_TYPEID'] == 16]
        if goal_res.empty: return
        
        goal_idx = goal_res.index[-1]
        
        # Sikker adgang til rækker via index-tjek
        goal_row = active_seq.loc[goal_idx]
        shot_row = active_seq.loc[goal_idx - 1] if (goal_idx - 1) in active_seq.index else None
        assist_row = active_seq.loc[goal_idx - 2] if (goal_idx - 2) in active_seq.index else None

        flip = True if goal_row['EVENT_X'] < 50 else False
        def fx(x): return 100 - x if flip else x
        def fy(y): return 100 - y if flip else y

    with col_viz:
        st.markdown(f'<div class="match-header">{goal_row["PLAYER_NAME"]} vs. Modstander</div>', unsafe_allow_html=True)
        pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(12, 8))

        # Tegn assist
        if assist_row is not None and shot_row is not None:
            pitch.arrows(fx(assist_row['EVENT_X']), fy(assist_row['EVENT_Y']), 
                         fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                         color=HIF_GOLD, width=4, headwidth=4, ax=ax, zorder=2)
            
            a_name = str(assist_row['PLAYER_NAME']).split(' ')[-1]
            ax.text(fx(assist_row['EVENT_X']), fy(assist_row['EVENT_Y']) + 3, a_name, 
                    fontsize=9, color='#666666', ha='center', zorder=3)

        # Tegn skud
        if shot_row is not None:
            pitch.arrows(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                         100, 50, color=HIF_RED, width=6, headwidth=5, ax=ax, zorder=4)
            
            pitch.scatter(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']), 
                          s=250, color=HIF_RED, edgecolors='black', linewidth=2, ax=ax, zorder=5)
            
            s_name = str(goal_row['PLAYER_NAME']).split(' ')[-1]
            ax.text(fx(shot_row['EVENT_X']), fy(shot_row['EVENT_Y']) - 5, s_name, 
                    fontsize=12, fontweight='bold', ha='center', zorder=6)

        pitch.scatter(100, 50, s=100, color=HIF_RED, alpha=0.4, ax=ax, zorder=1)
        st.pyplot(fig, use_container_width=True)
