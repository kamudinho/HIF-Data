# tools/ligaen/gamestates.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from data.data_load import _get_snowflake_conn
from data.sql.teams import hent_hold_gamestate_tid

def vis_side():
    """
    Hovedfunktion der kaldes af appen. Viser gamestate-oversigten som et 
    statisk Matplotlib-billede med legenden indbygget i en top-bar.
    """
    st.markdown("#### Holdenes Gamestates (Førende / Uafgjort / Bagud)")
    st.caption("Oversigt over andelen af spilletiden holdene tilbringer i henholdsvis Winning, Drawing og Losing.")

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake.")
        return

    calendar_uuid = "2mb332vncy4450vu14paj8844"

    with st.spinner("Henter gamestate-data fra Snowflake..."):
        try:
            df = hent_hold_gamestate_tid(conn, calendar_uuid)
        except Exception as e:
            if "390111" in str(e) or "Session no longer exists" in str(e):
                st.warning("Sessionen udløbet. Genopretter forbindelse...")
                st.cache_data.clear()
                new_conn = _get_snowflake_conn()
                df = hent_hold_gamestate_tid(new_conn, calendar_uuid)
            else:
                st.error(f"Fejl ved hentning af data: {e}")
                return

    if df.empty:
        st.info("Ingen gamestate-data fundet for denne kalender.")
        return

    # Sorter efter mest tid i føring
    df = df.sort_values(by='WINNING_PCT', ascending=True).reset_index(drop=True)

    teams = list(df['TEAM_NAME'])
    winning = df['WINNING_PCT']
    drawing = df['DRAWING_PCT']
    losing = df['LOSING_PCT']

    # Tilføj en "fake" række øverst til legende-bar (fordelt 33.3% til hver)
    teams_with_legend = ['LEGEND_BAR'] + teams
    winning_data = [33.33] + list(winning)
    drawing_data = [33.33] + list(drawing)
    losing_data = [33.33] + list(losing)

    # Opsæt Matplotlib figur (lidt højere for at give plads til legende-baren)
    fig, ax = plt.subplots(figsize=(10, max(8.5, (len(df) + 1) * 0.45)))

    c_winning = '#2e7d32'
    c_drawing = '#78909c'
    c_losing = '#c62828'

    # Stablede søjler for hele molevitten
    bars_w = ax.barh(teams_with_legend, winning_data, color=c_winning)
    bars_d = ax.barh(teams_with_legend, drawing_data, left=winning_data, color=c_drawing)
    bars_l = ax.barh(teams_with_legend, losing_data, left=[w + d for w, d in zip(winning_data, drawing_data)], color=c_losing)

    # Tilføj procenter for holdene, og tekst for legende-baren øverst
    for i, team_name in enumerate(teams_with_legend):
        bw = bars_w[i]
        bd = bars_d[i]
        bl = bars_l[i]

        if team_name == 'LEGEND_BAR':
            # Skriv legende-tekst ind i de 3 sektioner af top-baren
            ax.text(16.66, bw.get_y() + bw.get_height()/2, "Winning",
                    ha='center', va='center', color='white', fontweight='bold', fontsize=10)
            ax.text(50.0, bd.get_y() + bd.get_height()/2, "Drawing",
                    ha='center', va='center', color='white', fontweight='bold', fontsize=10)
            ax.text(83.33, bl.get_y() + bl.get_height()/2, "Losing",
                    ha='center', va='center', color='white', fontweight='bold', fontsize=10)
        else:
            # Almindelige hold-procenter
            w_val = winning.iloc[i-1]
            d_val = drawing.iloc[i-1]
            l_val = losing.iloc[i-1]

            if w_val > 5:
                ax.text(w_val / 2, bw.get_y() + bw.get_height()/2, f"{int(round(w_val))}%",
                        ha='center', va='center', color='white', fontweight='bold', fontsize=9)

            if d_val > 5:
                ax.text(w_val + (d_val / 2), bd.get_y() + bd.get_height()/2, f"{int(round(d_val))}%",
                        ha='center', va='center', color='white', fontweight='bold', fontsize=9)

            if l_val > 5:
                ax.text(w_val + d_val + (l_val / 2), bl.get_y() + bl.get_height()/2, f"{int(round(l_val))}%",
                        ha='center', va='center', color='white', fontweight='bold', fontsize=9)

    # Titel boks i top-venstre stil
    ax.text(0, 1.05, "  GAME STATES: SPILLETID FORDELT (%)  ", transform=ax.transAxes,
            fontsize=12, fontweight='bold', color='white',
            bbox=dict(facecolor='#1b4332', alpha=0.9, edgecolor='none', pad=6),
            ha='left', va='bottom')

    ax.set_xlim(0, 100)
    ax.set_ylim(-0.8, len(teams_with_legend) - 0.2)

    ax.set_xlabel('Procent af spilletid (%)', fontsize=10, fontweight='bold', color='#333333')
    ax.xaxis.grid(True, linestyle='--', alpha=0.5, color='#cccccc')
    ax.set_axisbelow(True)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#888888')
    ax.spines['bottom'].set_color('#888888')

    plt.tight_layout()

    # Gem figuren til bytes
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    plt.close(fig)
    img_bytes = buf.getvalue()

    # Vis billedet i Streamlit
    st.image(img_bytes, use_container_width=True)

    # Download-knap med de lagrede bytes
    st.download_button(
        label="📸 Download gamestate-oversigt som billede",
        data=img_bytes,
        file_name="hvidovre_gamestates.png",
        mime="image/png"
    )

if __name__ == "__main__":
    vis_side()
