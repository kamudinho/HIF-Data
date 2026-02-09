import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_events, cols_slider, hold_map=None):
    HIF_ID = 38331
    BG_WHITE = '#ffffff'

    # --- SIKKERHEDS-CHECK AF DATA ---
    if df_events is None or df_events.empty:
        st.error("Ingen data modtaget i Heatmaps modulet.")
        return

    # Standardiser kolonnenavne til store bogstaver for at undgå fejl
    df_events.columns = [c.upper() for c in df_events.columns]

    # 1. Filtrering af afleveringer (passes)
    # Vi tjekker om kolonnen 'PRIMARYTYPE' findes
    if 'PRIMARYTYPE' not in df_events.columns:
        st.error(f"Kolonnen 'PRIMARYTYPE' mangler i data. Fundne kolonner: {list(df_events.columns)}")
        return

    mask = df_events['PRIMARYTYPE'].astype(str).str.contains('pass', case=False, na=False)
    df_p = df_events[mask].copy()

    # Hvis df_p er tom, giver vi besked om hvad der faktisk findes i data
    if df_p.empty:
        st.warning("Ingen afleveringsdata fundet med filteret 'pass'.")
        st.info("Her er de typer af hændelser, der findes i din fil:")
        st.write(df_events['PRIMARYTYPE'].unique())
        return

    # 2. Layout konfiguration
    # Sorterer så Hvidovre (38331) altid kommer først
    hold_ids = sorted(df_p['TEAM_WYID'].unique(), key=lambda x: x != HIF_ID)

    # Beregn rækker baseret på antal hold og slideren
    rows = int(np.ceil(len(hold_ids) / cols_slider))

    # Opret figuren med samme dimensioner som dine andre ark
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(15, rows * 4),
        facecolor=BG_WHITE
    )

    # Justering af afstand (matcher din ønskede stil)
    fig.subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.90, wspace=0.1, hspace=0.3)
    axes_flat = np.atleast_1d(axes).flatten()

    pitch = VerticalPitch(
        pitch_type='custom', pitch_length=100, pitch_width=100,
        line_color='#1a1a1a', line_zorder=2, linewidth=0.5
    )

    # 3. Tegne-loop
    for i, tid in enumerate(hold_ids):
        ax = axes_flat[i]
        
        # Filtrer data for det specifikke hold og fjern rækker uden koordinater
        hold_df = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        
        pitch.draw(ax=ax)

        # Hent holdnavn fra hold_map
        if hold_map and tid in hold_map:
            navn = str(hold_map[tid]).upper()
        else:
            navn = "HVIDOVRE IF" if tid == HIF_ID else f"HOLD ID: {tid}"

        # Titel (Navn + antal passes på ny linje)
        ax.set_title(f"{navn}\n({len(hold_df)} passes)",
                     fontsize=12, fontweight='bold', pad=10)

        # Tegn heatmappet (KDE)
        if len(hold_df) > 5:
            sns.kdeplot(
                x=hold_df['LOCATIONY'], y=hold_df['LOCATIONX'], ax=ax,
                fill=True, thresh=0.02, levels=40, 
                cmap='YlOrRd', alpha=0.8, zorder=1
            )

    # Skjul de tomme hvide felter til sidst
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    # Vis figuren i Streamlit
    st.pyplot(fig, use_container_width=True)
