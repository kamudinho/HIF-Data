import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# Hvidovre IF Branding
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'

def vis_shotmap(df):
    if df is None or df.empty:
        st.warning("Ingen skud fundet for det valgte filter.")
        return None
    
    df.columns = [c.upper() for c in df.columns]
    
    # Setup af banen (Opta 0-100 skala)
    pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444', goal_type='box')
    fig, ax = pitch.draw(figsize=(10, 8))
    
    # Golden Zone
    ax.add_patch(plt.Rectangle((37, 88.5), 26, 11.5, color='gold', alpha=0.1, zorder=1))

    for _, row in df.iterrows():
        # Farve: Rød = Mål, Blå = Miss
        color = HIF_RED if str(row['EVENT_OUTCOME']) == '1' else HIF_BLUE
        # Marker: Trekant = Hovedstød (Qualifier 15)
        marker = '^' if '15' in str(row.get('QUALIFIERS', '')) else 'o'
        # Størrelse baseret på xG
        size = (row.get('XG_VAL', 0.05) * 1000) + 100
        
        pitch.scatter(row['EVENT_X'], row['EVENT_Y'], 
                      s=size, c=color, marker=marker,
                      edgecolors='white', linewidths=1,
                      ax=ax, alpha=0.8, zorder=3)
    return fig

def vis_side(dp):
    st.title("🎯 Hvidovre IF - Opta Shotmap")
    
    # Hent data fra pakken
    df_events = dp.get('playerstats', pd.DataFrame())
    df_matches = dp.get('opta_matches', pd.DataFrame())

    if df_events.empty:
        st.error("Ingen skud fundet i systemet.")
        return

    # --- FILTRE ---
    col1, col2 = st.columns(2)
    with col1:
        if not df_matches.empty:
            df_matches['DESC'] = (df_matches['MATCH_DATE_FULL'].astype(str).str[:10] + " - " + 
                                 df_matches['CONTESTANTHOME_NAME'] + " v " + 
                                 df_matches['CONTESTANTAWAY_NAME'])
            
            match_list = df_matches.sort_values('MATCH_DATE_FULL', ascending=False)
            valgt_kamp = st.selectbox("Vælg Kamp", ["Alle Kampe"] + match_list['DESC'].tolist())
        else:
            valgt_kamp = "Alle Kampe"

    if valgt_kamp != "Alle Kampe":
        m_id = df_matches[df_matches['DESC'] == valgt_kamp]['MATCH_OPTAUUID'].iloc[0]
        df_to_plot = df_events[df_events['MATCH_OPTAUUID'] == m_id]
    else:
        df_to_plot = df_events

    # --- VISUALISERING ---
    fig = vis_shotmap(df_to_plot)
    
    if fig:
        st.pyplot(fig)
        st.caption("Størrelse = xG | Trekant = Hovedstød | Rød = Mål")
        
        mål = len(df_to_plot[df_to_plot['EVENT_OUTCOME'].astype(str) == '1'])
        st.metric("Total xG", f"{df_to_plot['XG_VAL'].sum():.2f}", delta=f"{mål} mål")
