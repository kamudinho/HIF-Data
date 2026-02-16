import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

# --- CACHING AF SELVE FIGUREN ---
# Vi bruger tuple for hold_ids, da lister ikke kan caches direkte
@st.cache_data(show_spinner="Heatmaps genereres...")
def generate_cached_heatmaps(df_p, cols_slider, hold_ids_tuple, hold_map):
    BG_WHITE = '#ffffff'
    # Beregn rækker baseret på antal hold og valgte kolonner
    num_hold = len(hold_ids_tuple)
    rows = int(np.ceil(num_hold / cols_slider))
    
    # Opret figuren
    fig, axes = plt.subplots(
        rows, cols_slider,
        figsize=(15, rows * 5), 
        facecolor=BG_WHITE
    )

    # Juster afstand mellem banerne
    fig.subplots_adjust(left=0.05, right=0.95, bottom=0.02, top=0.95, wspace=0.1, hspace=0.3)
    
    # Gør axes flad (array), så vi kan iterere over dem, selv hvis der kun er 1 række
    axes_flat = np.atleast_1d(axes).flatten()

    # Opsæt banen (Wyscout bruger ofte 100x100)
    pitch = VerticalPitch(
        pitch_type='wyscout', 
        line_color='#1a1a1a', 
        line_zorder=2, 
        linewidth=0.8
    )

    for i, tid in enumerate(hold_ids_tuple):
        ax = axes_flat[i]
        
        # Filtrer data for det specifikke hold
        hold_df_full = df_p[df_p['TEAM_WYID'] == tid].copy().dropna(subset=['LOCATIONX', 'LOCATIONY'])
        total_passes = len(hold_df_full)
        
        # SPEED BOOST: Sample data hvis der er ekstremt mange rækker
        if total_passes > 3000:
            hold_df_draw = hold_df_full.sample(n=3000, random_state=42)
        else:
            hold_df_draw = hold_df_full

        pitch.draw(ax=ax)

        # Hent navn fra map eller brug ID
        navn = str(hold_map.get(str(tid), f"HOLD: {tid}")).upper()
        ax.set_title(f"{navn}\n({total_passes:,} AFLEVERINGER)".replace(',', '.'), 
                     fontsize=11, fontweight='bold', pad=10)

        # Tegn Heatmap hvis der er data nok
        if total_passes > 5:
            sns.kdeplot(
                x=hold_df_draw['LOCATIONY'], 
                y=hold_df_draw['LOCATIONX'], 
                ax=ax,
                fill=True, 
                thresh=0.05, 
                levels=15, 
                cmap='YlOrRd', 
                alpha=0.7, 
                zorder=1,
                clip=((0, 100), (0, 100)) # Holder det inden for banen
            )

    # Skjul resterende tomme plots
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis('off')

    return fig

# --- HOVEDFUNKTION ---
def vis_side(df_events, hold_map=None):
    st.subheader("HEATMAPS: AFLEVERINGSMØNSTRE")
    
    if df_events is None or df_events.empty:
        st.error("Ingen data fundet i Snowflake.")
        return

    # 1. SIDEBAR KONTROL
    st.sidebar.markdown("---")
    st.sidebar.subheader("Indstillinger for Heatmaps")
    cols_slider = st.sidebar.slider("Antal kolonner", 1, 4, 2)
    
    # 2. DATAPRÆPARERING
    # Sørg for kolonnenavne er rigtige
    df_events.columns = [c.upper() for c in df_events.columns]
    
    # Filtrer kun pasninger (PRIMARYTYPE skal indeholde 'pass')
    df_p = df_events[df_events['PRIMARYTYPE'].str.lower().str.contains('pass', na=False)].copy()

    if df_p.empty:
        st.warning("Der blev ikke fundet nogen 'pass' events i de indlæste data.")
        return

    # Sorter hold efter navn
    # Vi mapper ID til navn først for at kunne sortere alfabetisk
    temp_hold_list = []
    unique_ids = df_p['TEAM_WYID'].unique()
    for tid in unique_ids:
        t_name = hold_map.get(str(tid), f"ID: {tid}")
        temp_hold_list.append({'ID': tid, 'NAME': t_name})
    
    sorted_hold = sorted(temp_hold_list, key=lambda x: x['NAME'])
    hold_ids = [h['ID'] for h in sorted_hold]

    # 3. GENERER OG VIS
    # Vi sender hold_ids som en tuple til cachen
    fig = generate_cached_heatmaps(df_p, cols_slider, tuple(hold_ids), hold_map)
    
    st.pyplot(fig, use_container_width=True)
    
    st.info("💡 Heatmappet viser koncentrationen af afleveringer. Røde områder indikerer høj aktivitet.")
