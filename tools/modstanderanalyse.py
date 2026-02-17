import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

# Vi beholder din caching-logik, men gør den specifik for det valgte hold
@st.cache_data(show_spinner="Genererer taktisk heatmap...")
def get_team_heatmap(df_p, team_id, team_name):
    BG_WHITE = '#ffffff'
    fig, ax = plt.subplots(figsize=(8, 10), facecolor=BG_WHITE)
    
    pitch = VerticalPitch(
        pitch_type='wyscout', 
        line_color='#1a1a1a', 
        line_zorder=2, 
        linewidth=1.2
    )
    pitch.draw(ax=ax)

    # Filtrer data
    hold_df = df_p[df_p['TEAM_WYID'] == team_id].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
    
    if len(hold_df) > 5:
        # Tegn heatmap (din stil)
        sns.kdeplot(
            x=hold_df['LOCATIONY'], 
            y=hold_df['LOCATIONX'], 
            ax=ax,
            fill=True, 
            thresh=0.05, 
            levels=15, 
            cmap='YlOrRd', 
            alpha=0.6, 
            zorder=1,
            clip=((0, 100), (0, 100))
        )
        ax.set_title(f"AFLEVERINGSMØNSTER: {team_name.upper()}", 
                    fontsize=14, fontweight='bold', pad=20)
    
    return fig

# --- I din modstanderanalyse.py ---
def vis_side(df_team_matches, hold_map, df_events):
    # ... (valg af modstander som før) ...

    st.markdown("### Taktisk Analyse")
    
    tab1, tab2 = st.tabs(["📊 Statistik & Form", "🔥 Positionelt Heatmap"])
    
    with tab1:
        # Her placerer vi de Plotly grafer/metrics vi lavede før
        st.write("Visning af xG trend og metrics...")

    with tab2:
        # Her bruger vi din heatmap-formatering
        if df_events is not None:
            # Forbered data (kun pass events)
            df_p = df_events[df_events['PRIMARYTYPE'].str.lower().str.contains('pass', na=False)].copy()
            
            # Generer heatmap for KUN den valgte modstander
            fig_map = get_team_heatmap(df_p, valgt_id, valgt_navn)
            st.pyplot(fig_map, use_container_width=True)
            
            st.caption("Heatmappet viser hvor på banen holdet foretager deres afleveringer. "
                       "Jo mørkere rød, jo højere intensitet i opspillet.")
