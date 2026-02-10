import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

# --- CACHING AF SELVE FIGUREN ---
# Vi bruger hash_funcs eller konverterer hold_ids til en tuple for at sikre stabil caching
@st.cache_data(show_spinner="Genererer taktiske heatmaps...")
def generate_cached_heatmaps(df_p, cols_slider, hold_ids_tuple, hold_map):
    HIF_ID = 38331
    BG_WHITE = '#ffffff'

    # Layout konfiguration
    rows = int(np.ceil(len(hold_ids_tuple) / cols_slider))
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(15, rows * 5), # Lidt ekstra højde til titlerne
        facecolor=BG_WHITE
    )

    fig.subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.92, wspace=0.1, hspace=0.4)
    axes_flat = np.atleast_1d(axes).flatten()

    pitch = VerticalPitch(
        pitch_type='custom', pitch_length=100, pitch_width=100,
        line_color='#1a1a1a', line_zorder=2, linewidth=0.5
    )

    # Loop gennem holdene
    for i, tid in enumerate(hold_ids_tuple):
        ax = axes_flat[i]
        
        # 1. Hent alt data for holdet (til optælling)
        hold_df_full = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        total_passes = len(hold_df_full)
        
        # 2. SPEED BOOST: Sample data til selve tegningen (n=2000)
        # Dette påvirker ikke tælleren i titlen, kun hvor hurtigt farverne tegnes
        if total_passes > 2000:
            hold_df_draw = hold_df_full.sample(n=2000, random_state=42)
        else:
            hold_df_draw = hold_df_full

        # Tegn banen
        pitch.draw(ax=ax)

        # Hent holdnavn
        navn = str(hold_map.get(tid, f"HOLD ID: {tid}")).upper()

        # 3. TITEL: Her bruger vi det RIGTIGE totale antal (f.eks. 12.450)
        ax.set_title(f"{navn}\n({total_passes:,} PASSES)".replace(',', '.'), 
                     fontsize=12, fontweight='bold', pad=10)

        # 4. TEGN HEATMAP (KDE)
        if total_passes > 10:
            sns.kdeplot(
                x=hold_df_draw['LOCATIONY'], y=hold_df_draw['LOCATIONX'], ax=ax,
                fill=True, 
                thresh=0.05, # Fjerner de helt svage farver i yderkanten for renere look
                levels=20,   # 20 er rigeligt til 12 små baner
                cmap='YlOrRd', 
                alpha=0.8, 
                zorder=1
            )

    # Skjul resterende tomme plots
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    return fig

def vis_side(df_events, cols_slider, hold_map=None):
    HIF_ID = 38331

    if df_events is None or df_events.empty:
        st.error("Ingen data modtaget.")
        return

    # Standardiser kolonner
    df_events.columns = [c.upper() for c in df_events.columns]

    if 'PRIMARYTYPE' not in df_events.columns:
        st.error("Data mangler 'PRIMARYTYPE' kolonnen.")
        return

    # Filtrer afleveringer
    mask = df_events['PRIMARYTYPE'].astype(str).str.contains('pass', case=False, na=False)
    df_p = df_events[mask].copy()

    if df_p.empty:
        st.warning("Ingen afleveringsdata fundet.")
        return

    # Sorter hold-IDs (HIF først)
    hold_ids = sorted(df_p['TEAM_WYID'].unique(), key=lambda x: x != HIF_ID)

    # KALD DEN OPTIMEREDE BEREGNING
    # Vi sender hold_ids som en tuple, da lister ikke kan caches direkte
    fig = generate_cached_heatmaps(df_p, cols_slider, tuple(hold_ids), hold_map)
    
    # Vis i Streamlit
    st.pyplot(fig, use_container_width=True)
