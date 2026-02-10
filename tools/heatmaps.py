import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

# --- CACHING FUNKTION ---
# Vi gemmer hele figuren baseret på dataens unikke "fingeraftryk"
@st.cache_data(show_spinner="Beregner 12 heatmaps...")
def generate_cached_heatmaps(df_p, cols_slider, hold_ids, hold_map):
    HIF_ID = 38331
    BG_WHITE = '#ffffff'
    
    rows = int(np.ceil(len(hold_ids) / cols_slider))
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(15, rows * 4),
        facecolor=BG_WHITE
    )
    
    fig.subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.90, wspace=0.1, hspace=0.3)
    axes_flat = np.atleast_1d(axes).flatten()

    pitch = VerticalPitch(
        pitch_type='custom', pitch_length=100, pitch_width=100,
        line_color='#1a1a1a', line_zorder=2, linewidth=0.5
    )

    for i, tid in enumerate(hold_ids):
        ax = axes_flat[i]
        
        # 1. Hent ALL data for holdet
        hold_df_full = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        
        # 2. Gem det rigtige antal til titlen
        rigtigt_antal = len(hold_df_full)
        
        # 3. Lav et lille udpluk (n=2000) KUN til at tegne selve farverne
        if rigtigt_antal > 2000:
            hold_df_sample = hold_df_full.sample(n=2000, random_state=42)
        else:
            hold_df_sample = hold_df_full

        pitch.draw(ax=ax)

        # 4. Skriv det RIGTIGE antal i titlen (f.eks. 14.500 passes)
        navn = str(hold_map.get(tid, f"HOLD ID: {tid}")).upper()
        ax.set_title(f"{navn}\n({rigtigt_antal} passes)", fontsize=12, fontweight='bold', pad=10)

        # 5. Tegn heatmappet baseret på de 2.000 punkter (lynhurtigt)
        if rigtigt_antal > 5:
            sns.kdeplot(
                x=hold_df_sample['LOCATIONY'], y=hold_df_sample['LOCATIONX'], ax=ax,
                fill=True, thresh=0.05, levels=20, 
                cmap='YlOrRd', alpha=0.8, zorder=1
            )

    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')
        
    return fig

def vis_side(df_events, cols_slider, hold_map=None):
    HIF_ID = 38331

    if df_events is None or df_events.empty:
        st.error("Ingen data modtaget.")
        return

    # Sørg for store bogstaver
    df_events.columns = [c.upper() for c in df_events.columns]

    if 'PRIMARYTYPE' not in df_events.columns:
        st.error("Kolonnen 'PRIMARYTYPE' mangler.")
        return

    # Filtrering
    mask = df_events['PRIMARYTYPE'].astype(str).str.contains('pass', case=False, na=False)
    df_p = df_events[mask].copy()

    if df_p.empty:
        st.warning("Ingen afleveringsdata fundet.")
        return

    hold_ids = sorted(df_p['TEAM_WYID'].unique(), key=lambda x: x != HIF_ID)

    # --- KALD DEN CACHEDE FIGUR ---
    # Vi sender hold_ids med som en liste, så cachen ved hvornår den skal opdatere
    fig = generate_cached_heatmaps(df_p, cols_slider, tuple(hold_ids), hold_map)
    
    st.pyplot(fig, use_container_width=True)
