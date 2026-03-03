import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
from data.data_load import get_data_package

# Vi bruger dine egne farver og mappings
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'

def extract_qualifier_value(qual_str, val_str, target_id):
    """Hjælper med at finde en specifik værdi i LISTAGG-strengene"""
    if not qual_str or pd.isna(qual_str): return None
    quals = str(qual_str).split(',')
    vals = str(val_str).split(',')
    if str(target_id) in quals:
        return vals[quals.index(str(target_id))]
    return None

def vis_shotmap_opta(df_events):
    # 1. Filtrér kun skud (13, 14, 15, 16)
    shot_ids = ['13', '14', '15', '16']
    df_shots = df_events[df_events['EVENT_TYPEID'].astype(str).isin(shot_ids)].copy()
    
    # 2. Berig data med dine Qualifiers
    # xG findes typisk i QID 321 eller 460 (Expected Goal 2.0)
    df_shots['xG'] = df_shots.apply(lambda r: extract_qualifier_value(r['QUALIFIERS'], r['QUAL_VALUES'], '460'), axis=1)
    df_shots['xG'] = pd.to_numeric(df_shots['xG'], errors='coerce').fillna(0.05)
    
    # Tjek for Hovedstød (Qualifier 15)
    df_shots['is_head'] = df_shots['QUALIFIERS'].apply(lambda x: '15' in str(x))

    # 3. Tegn banen
    pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444', goal_type='box')
    fig, ax = pitch.draw(figsize=(10, 8))
    
    # Danger Zone visualisering
    ax.add_patch(plt.Rectangle((37, 88.5), 26, 11.5, color='orange', alpha=0.1, zorder=1))

    for _, row in df_shots.iterrows():
        # Mål = Rød, Resten = Blå (Hvidovre farver)
        color = HIF_RED if str(row['EVENT_OUTCOME']) == '1' else HIF_BLUE
        marker = '^' if row['is_head'] else 'o'
        size = (row['xG'] * 800) + 100
        
        pitch.scatter(row['EVENT_X'], row['EVENT_Y'], 
                      s=size, c=color, marker=marker,
                      edgecolors='white', ax=ax, alpha=0.7)
    
    return fig

# I din hoved-app:
dp = get_data_package()
st.pyplot(vis_shotmap_opta(dp['opta']['player_stats']))
