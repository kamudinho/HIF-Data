import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# HIF Branding
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'

def vis_shotmap(df):
    if df is None or df.empty:
        st.warning("Ingen skud fundet for det valgte filter.")
        return None
    
    # Setup banen (Opta pitch bruger 0-100 skala)
    pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444', goal_type='box')
    fig, ax = pitch.draw(figsize=(10, 8))
    
    # Golden Zone (Farligste område)
    ax.add_patch(plt.Rectangle((37, 88.5), 26, 11.5, color='gold', alpha=0.1, zorder=1))

    for _, row in df.iterrows():
        # Rød for mål (Outcome 1), Blå for miss (Outcome 0)
        color = HIF_RED if str(row.get('EVENT_OUTCOME')) == '1' else HIF_BLUE
        
        # Marker: Trekant for hovedstød (Søg efter Qualifier 15 i din LISTAGG kolonne)
        is_header = '15' in str(row.get('QUALIFIERS', ''))
        marker = '^' if is_header else 'o'
        
        # Størrelse baseret på xG (XG_VAL som vi lavede i loaderen)
        size = (row.get('XG_VAL', 0.05) * 1200) + 100
        
        pitch.scatter(row['EVENT_X'], row['EVENT_Y'], 
                      s=size, c=color, marker=marker,
                      edgecolors='white', linewidths=1,
                      ax=ax, alpha=0.8, zorder=3)
    return fig

def vis_side(dp):
    st.title("🎯 Hvidovre IF - Opta Shotmap")
    
    # Hent data fra din data_load pakke
    df_events = dp.get('playerstats', pd.DataFrame())
    df_matches = dp.get('opta_matches', pd.DataFrame())

    if df_events.empty:
        st.error("Kunne ikke finde skud-data (playerstats er tom).")
        return

    # --- FILTRE ---
    col1, col2 = st.columns(2)
    with col1:
        if not df_matches.empty:
            # Vi bruger dine præcise kolonnenavne: DATE, HOMECONTESTANT_NAME, AWAYCONTESTANT_NAME
            df_matches['DESC'] = (
                df_matches['DATE'].astype(str) + " - " + 
                df_matches['HOMECONTESTANT_NAME'] + " v " + 
                df_matches['AWAYCONTESTANT_NAME']
            )
            
            match_list = df_matches.sort_values('DATE', ascending=False)
            valgt_kamp = st.selectbox("Vælg Kamp", ["Alle Kampe"] + match_list['DESC'].tolist())
        else:
            valgt_kamp = "Alle Kampe"

    # --- FILTRERINGS LOGIK ---
    if valgt_kamp != "Alle Kampe":
        # Find UUID for den valgte kamp
        m_id = df_matches[df_matches['DESC'] == valgt_kamp]['MATCH_OPTAUUID'].iloc[0]
        # Match mod EVENTS tabellens MATCH_OPTAUUID
        df_to_plot = df_events[df_events['MATCH_OPTAUUID'] == m_id]
    else:
        df_to_plot = df_events

    # --- VISUALISERING ---
    fig = vis_shotmap(df_to_plot)
    
    if fig:
        st.pyplot(fig)
        st.caption("Størrelse = xG | Trekant = Hovedstød | Rød = Mål")
        
        # Hurtig statistik under kortet
        mål = len(df_to_plot[df_to_plot['EVENT_OUTCOME'].astype(str) == '1'])
        xg_sum = df_to_plot['XG_VAL'].sum() if 'XG_VAL' in df_to_plot.columns else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Antal Skud", len(df_to_plot))
        c2.metric("Mål", mål)
        c3.metric("Total xG", f"{xg_sum:.2f}")

    # Valgfri: Vis tabel med skuddene
    if st.checkbox("Vis skud-detaljer"):
        cols_to_show = ['PLAYER_NAME', 'EVENT_TIMEMIN', 'EVENT_OUTCOME', 'XG_VAL']
        st.dataframe(df_to_plot[cols_to_show].sort_values('EVENT_TIMEMIN'))
