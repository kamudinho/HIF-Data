import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

# --- CACHING AF SELVE FIGUREN ---
@st.cache_data(show_spinner="Heatmaps præsenteres...")
def generate_cached_heatmaps(df_p, cols_slider, hold_ids_tuple, hold_map):
    HIF_ID = 38331
    BG_WHITE = '#ffffff'

    rows = int(np.ceil(len(hold_ids_tuple) / cols_slider))
    
    # Optimeret figsize for at mindske afstand
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(15, rows * 3.8), 
        facecolor=BG_WHITE
    )

    # Tæt layout konfiguration
    fig.subplots_adjust(
        left=0.05, 
        right=0.95, 
        bottom=0.02, 
        top=0.92, 
        wspace=0.05, 
        hspace=0.22
    )
    
    axes_flat = np.atleast_1d(axes).flatten()

    pitch = VerticalPitch(
        pitch_type='custom', pitch_length=100, pitch_width=100,
        line_color='#1a1a1a', line_zorder=2, linewidth=0.5
    )

    for i, tid in enumerate(hold_ids_tuple):
        ax = axes_flat[i]
        
        # Filtrer data
        hold_df_full = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        total_passes = len(hold_df_full)
        
        # SPEED BOOST: Sample data (n=2000)
        if total_passes > 2000:
            hold_df_draw = hold_df_full.sample(n=2000, random_state=42)
        else:
            hold_df_draw = hold_df_full

        pitch.draw(ax=ax)

        # Navn og Titel
        navn = str(hold_map.get(tid, f"HOLD ID: {tid}")).upper()
        ax.set_title(f"{navn}\n({total_passes:,} PASSES)".replace(',', '.'), 
                     fontsize=11, fontweight='bold', pad=8)

        # Tegn Heatmap
        if total_passes > 10:
            sns.kdeplot(
                x=hold_df_draw['LOCATIONY'], y=hold_df_draw['LOCATIONX'], ax=ax,
                fill=True, thresh=0.05, levels=20, 
                cmap='YlOrRd', alpha=0.8, zorder=1
            )

    # Skjul tomme felter
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    return fig

def vis_side(df_events, cols_slider, hold_map=None):
    HIF_ID = 38331

    if df_events is None or df_events.empty:
        st.error("Ingen data modtaget.")
        return

    df_events.columns = [c.upper() for c in df_events.columns]

    if 'PRIMARYTYPE' not in df_events.columns:
        st.error("Data mangler 'PRIMARYTYPE' kolonnen.")
        return

    mask = df_events['PRIMARYTYPE'].astype(str).str.contains('pass', case=False, na=False)
    df_p = df_events[mask].copy()

    if df_p.empty:
        st.warning("Ingen afleveringsdata fundet.")
        return

    hold_ids = sorted(df_p['TEAM_WYID'].unique(), key=lambda x: x != HIF_ID)

    # Kald cachen
    fig = generate_cached_heatmaps(df_p, cols_slider, tuple(hold_ids), hold_map)
    
    st.pyplot(fig, use_container_width=True)
