import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# Hvidovre IF Branding
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'

def extract_qualifier_value(qual_str, val_str, target_id):
    if not qual_str or pd.isna(qual_str): return None
    quals = str(qual_str).split(',')
    vals = str(val_str).split(',')
    if str(target_id) in quals:
        try:
            return vals[quals.index(str(target_id))]
        except:
            return None
    return None

def vis_shotmap(df):
    """Selve logikken til at tegne kortet"""
    if df is None or df.empty:
        st.warning("Ingen skud fundet for denne kamp.")
        return None
    
    df.columns = [c.upper() for c in df.columns]
    shot_ids = ['13', '14', '15', '16']
    df_shots = df[df['EVENT_TYPEID'].astype(str).isin(shot_ids)].copy()
    
    if df_shots.empty:
        return None
    
    df_shots['XG_VAL'] = df_shots.apply(
        lambda r: extract_qualifier_value(r.get('QUALIFIERS'), r.get('QUAL_VALUES'), '460') or 
                  extract_qualifier_value(r.get('QUALIFIERS'), r.get('QUAL_VALUES'), '321'), 
        axis=1
    )
    df_shots['XG_VAL'] = pd.to_numeric(df_shots['XG_VAL'], errors='coerce').fillna(0.07)
    df_shots['IS_HEADER'] = df_shots['QUALIFIERS'].apply(lambda x: '15' in str(x))

    pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444', goal_type='box')
    fig, ax = pitch.draw(figsize=(10, 8))
    
    # Golden Zone
    ax.add_patch(plt.Rectangle((37, 88.5), 26, 11.5, color='gold', alpha=0.1, zorder=1))

    for _, row in df_shots.iterrows():
        color = HIF_RED if str(row['EVENT_OUTCOME']) == '1' else HIF_BLUE
        marker = '^' if row['IS_HEADER'] else 'o'
        size = (row['XG_VAL'] * 900) + 100
        
        pitch.scatter(row['EVENT_X'], row['EVENT_Y'], 
                      s=size, c=color, marker=marker,
                      edgecolors='white', linewidths=1,
                      ax=ax, alpha=0.8, zorder=3)
    return fig

def vis_side(dp):
    """Denne funktion kaldes fra HIF-dash.py"""
    st.title("🎯 Hvidovre IF - Opta Shotmap")
    
    # Hent data fra pakken
    df_events = dp.get('opta', {}).get('player_stats', pd.DataFrame())
    df_matches = dp.get('opta', {}).get('matches', pd.DataFrame())

    if df_events.empty or df_matches.empty:
        st.error("Kunne ikke finde Opta-data i systemet.")
        return

    # --- FILTRE I TOPPEN ---
    col1, col2 = st.columns(2)
    with col1:
        # Lav en liste over kampe: "Dato - Modstander"
        match_list = df_matches.sort_values('DATE', ascending=False)
        match_options = match_list['MATCH_DESCRIPTION'].unique().tolist()
        valgt_kamp_navn = st.selectbox("Vælg Kamp", ["Alle Kampe"] + match_options)

    # Filtrér data
    if valgt_kamp_navn != "Alle Kampe":
        match_id = match_list[match_list['MATCH_DESCRIPTION'] == valgt_kamp_navn]['MATCH_OPTAUUID'].iloc[0]
        df_to_plot = df_events[df_events['MATCH_OPTAUUID'] == match_id]
    else:
        df_to_plot = df_events

    # --- VISUALISERING ---
    fig = vis_shotmap(df_to_plot)
    
    if fig:
        st.pyplot(fig)
        st.caption("Størrelsen på prikken indikerer xG. Trekant er hovedstød. Rød er mål.")
    else:
        st.info("Ingen afslutninger registreret for det valgte filter.")
