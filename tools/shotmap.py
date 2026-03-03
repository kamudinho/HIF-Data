import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt  # TILFØJET: Nødvendig for plt.Rectangle
from mplsoccer import VerticalPitch
from data.data_load import get_data_package

# Hvidovre IF Branding
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'

def extract_qualifier_value(qual_str, val_str, target_id):
    """Hjælper med at finde en specifik værdi i LISTAGG-strengene"""
    if not qual_str or pd.isna(qual_str): return None
    quals = str(qual_str).split(',')
    vals = str(val_str).split(',')
    if str(target_id) in quals:
        try:
            return vals[quals.index(str(target_id))]
        except IndexError:
            return None
    return None

def vis_shotmap(df):
    """Genererer shotmap baseret på Opta-data"""
    if df is None or df.empty:
        st.warning("Ingen skud-data tilgængelig for den valgte periode.")
        return None
    
    # Snowflake returnerer altid kolonnenavne i UPPERCASE
    df.columns = [c.upper() for c in df.columns]
    
    # 1. Filtrér kun skud (13=Miss, 14=Post, 15=Saved, 16=Goal)
    shot_ids = ['13', '14', '15', '16']
    df_shots = df[df['EVENT_TYPEID'].astype(str).isin(shot_ids)].copy()
    
    if df_shots.empty:
        st.info("Ingen afslutninger fundet i dette datasæt.")
        return None
    
    # 2. Berig data med Qualifiers (xG og Hovedstød)
    # Vi tjekker både Q321 og Q460 for xG
    df_shots['XG_VAL'] = df_shots.apply(
        lambda r: extract_qualifier_value(r.get('QUALIFIERS'), r.get('QUAL_VALUES'), '460') or 
                  extract_qualifier_value(r.get('QUALIFIERS'), r.get('QUAL_VALUES'), '321'), 
        axis=1
    )
    df_shots['XG_VAL'] = pd.to_numeric(df_shots['XG_VAL'], errors='coerce').fillna(0.07)
    df_shots['IS_HEADER'] = df_shots['QUALIFIERS'].apply(lambda x: '15' in str(x))

    # 3. Tegn banen
    pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444', goal_type='box')
    fig, ax = pitch.draw(figsize=(10, 8))
    
    # Visualisering af "The Golden Zone" (Høj xG område)
    ax.add_patch(plt.Rectangle((37, 88.5), 26, 11.5, color='gold', alpha=0.1, zorder=1))

    # 4. Plot hvert skud
    for _, row in df_shots.iterrows():
        # Farve baseret på Outcome (1 = Mål)
        color = HIF_RED if str(row['EVENT_OUTCOME']) == '1' else HIF_BLUE
        # Form baseret på kropsdel
        marker = '^' if row['IS_HEADER'] else 'o'
        # Størrelse baseret på xG
        size = (row['XG_VAL'] * 900) + 100
        
        pitch.scatter(row['EVENT_X'], row['EVENT_Y'], 
                      s=size, c=color, marker=marker,
                      edgecolors='white', linewidths=1,
                      ax=ax, alpha=0.8, zorder=3)
    
    return fig

# --- KALD I DIN APP ---
# dp = get_data_package()
# fig = vis_shotmap(dp['opta']['player_stats'])
# if fig:
#     st.pyplot(fig)
