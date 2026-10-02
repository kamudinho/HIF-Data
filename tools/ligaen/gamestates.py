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
    statisk Matplotlib-billede i stil med dine øvrige visualiseringer.
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

    # Sorter efter mest tid i føring (stigende, så det øverste hold kommer øverst på y-aksen)
    df = df.sort_values(by='WINNING_PCT', ascending=True).reset_index(drop=True)

    teams = df['TEAM_NAME']
    winning = df['WINNING_PCT']
    drawing = df['DRAWING_PCT']
    losing = df['LOSING_PCT']

    # Opsæt Matplotlib figur
    fig, ax = plt.subplots(figsize=(10, max(8, len(df) * 0.4)))

    # Farver (Grøn for Winning, Grå for Drawing, Rød for Losing)
    c_winning = '#2e7d32'
    c_drawing = '#90a4ae'
    c_losing = '#c62828'

    # Stablede vandrette søjler i rækkefølgen: Winning (venstre), Drawing (midt), Losing (højre)
    bars_w = ax.barh(teams, winning, color=c_winning, label='Winning')
    bars_d = ax.barh(teams, drawing, left=winning, color=c_drawing, label='Drawing')
    bars_l = ax.barh(teams, losing, left=winning + drawing, color=c_losing, label='Losing')

    # Tilføj procenter med hvid, fed skrift inde i søjlerne (hvis pladsen tillader det)
    for bw, bd, bl, team in zip(bars_w, bars_d, bars_l, df.itertuples()):
        w_val = team.WINNING_PCT
        d_val = team.DRAWING_PCT
        l_val = team.LOSING_PCT

        # Winning tekst (hvis > 5%)
        if w_val > 5:
            ax.text(w_val / 2, bw.get_y() + bw.get_height()/2, f"{int(round(w_val))}%",
                    ha='center', va='center', color='white', fontweight='bold', fontsize=9)

        # Drawing tekst (hvis > 5%)
        if d_val > 5:
            ax.text(w_val + (d_val / 2), bd.get_y() + bd.get_height()/2, f"{int(round(d_val))}%",
                    ha='center', va='center', color='white', fontweight='bold', fontsize=9)

        # Losing tekst (hvis > 5%)
        if l_val > 5:
            ax.text(w_val + d_val + (l_val / 2), bl.get_y() + bl.get_height()/2, f"{int(round(l_val))}%",
                    ha='center', va='center', color='white', fontweight='bold', fontsize=9)

    # Titel boks i top-venstre stil (ligesom eksemplet)
    ax.text(0, 1.02, "  GAME STATES: SPILLETID FORDELT (%)  ", transform=ax.transAxes,
            fontsize=12, fontweight='bold', color='white',
            bbox=dict(facecolor='#1b4332', alpha=0.9, edgecolor='none', pad=6),
            ha='left', va='bottom')

    # Styling af akser og baggrund
    ax.set_xlim(0, 100)
    ax.set_xlabel('Procent af spilletid (%)', fontsize=10, fontweight='bold', color='#333333')
    ax.xaxis.grid(True, linestyle='--', alpha=0.5, color='#cccccc')
    ax.set_axisbelow(True)

    # Fjern unødvendige kanter (spines)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#888888')
    ax.spines['bottom'].set_color('#888888')

    # Legende øverst til højre
    ax.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='none')

    plt.tight_layout()

    # Gem som billede i hukommelsen og vis i Streamlit
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)

    st.image(buf, use_container_width=True)

    # Download knap til billedet
    st.download_button(
        label="📸 Download gamestate-oversigt som billede",
        data=buf,
        file_name="hvidovre_gamestates.png",
        mime="image/png"
    )

if __name__ == "__main__":
    vis_side()
