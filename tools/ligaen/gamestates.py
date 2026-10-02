# tools/ligaen/gamestates.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
from data.data_load import _get_snowflake_conn
from data.sql.teams import hent_hold_gamestate_tid

def vis_side():
    """
    Hovedfunktion der kaldes af appen. Viser gamestate-oversigten opdelt 
    i tre kolonner (Losing, Drawing, Winning) i Opta Analyst-stil.
    """
    st.markdown("#### Holdenes Gamestates (Førende / Uafgjort / Bagud)")
    st.caption("Oversigt over andelen af spilletiden holdene tilbringer i henholdsvis Losing, Drawing og Winning.")

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

    # Konverter procenter til rene floats
    for col in ['WINNING_PCT', 'DRAWING_PCT', 'LOSING_PCT']:
        if col in df.columns:
            df[col] = df[col].astype(float)

    # Sorter efter WINNING_PCT faldende, så holdet med flest procent i føring er øverst
    df = df.sort_values(by='WINNING_PCT', ascending=False).reset_index(drop=True)

    teams = list(df['TEAM_NAME'])
    winning = df['WINNING_PCT']
    drawing = df['DRAWING_PCT']
    losing = df['LOSING_PCT']

    # Opsæt figur med 3 subplots ved siden af hinanden
    fig, (ax_losing, ax_drawing, ax_winning) = plt.subplots(
        1, 3, 
        figsize=(14, max(8, len(df) * 0.4)), 
        sharey=True
    )

    # Opta-inspirerede farver (eller dine foretrukne)
    c_losing = '#e57373'
    c_drawing = '#90a4ae'
    c_winning = '#81c784'

    # 1. LOSING barer (vises fra højre mod venstre eller standard venstre mod højre - her standard med værdi)
    bars_l = ax_losing.barh(teams, losing, color=c_losing)
    ax_losing.set_title("LOSING", fontsize=12, fontweight='bold', color='#555555', pad=10)
    ax_losing.invert_yaxis() # Sørg for at topholdet er øverst
    ax_losing.set_xlim(0, 100)
    ax_losing.xaxis.grid(True, linestyle='--', alpha=0.3, color='#cccccc')
    ax_losing.set_axisbelow(True)

    # 2. DRAWING barer
    bars_d = ax_drawing.barh(teams, drawing, color=c_drawing)
    ax_drawing.set_title("DRAWING", fontsize=12, fontweight='bold', color='#555555', pad=10)
    ax_drawing.set_xlim(0, 100)
    ax_drawing.xaxis.grid(True, linestyle='--', alpha=0.3, color='#cccccc')
    ax_drawing.set_axisbelow(True)

    # 3. WINNING barer
    bars_w = ax_winning.barh(teams, winning, color=c_winning)
    ax_winning.set_title("WINNING", fontsize=12, fontweight='bold', color='#555555', pad=10)
    ax_winning.set_xlim(0, 100)
    ax_winning.xaxis.grid(True, linestyle='--', alpha=0.3, color='#cccccc')
    ax_winning.set_axisbelow(True)

    # Tilføj procenter på højre side af hver søjle
    for i in range(len(teams)):
        l_val = losing.iloc[i]
        d_val = drawing.iloc[i]
        w_val = winning.iloc[i]

        if l_val > 2:
            ax_losing.text(l_val + 1, i, f"{int(round(l_val))}%", va='center', fontsize=9, color='#333333', fontweight='bold')
        if d_val > 2:
            ax_drawing.text(d_val + 1, i, f"{int(round(d_val))}%", va='center', fontsize=9, color='#333333', fontweight='bold')
        if w_val > 2:
            ax_winning.text(w_val + 1, i, f"{int(round(w_val))}%", va='center', fontsize=9, color='#333333', fontweight='bold')

    # Fjern overflødige kanter (spines) for et rent Opta-look
    for ax in [ax_losing, ax_drawing, ax_winning]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#cccccc')
        ax.spines['bottom'].set_color('#cccccc')

    # Fælles x-akse label under graferne
    fig.text(0.5, 0.02, '% of time in each game state', ha='center', fontsize=11, fontweight='bold', color='#222222')

    plt.tight_layout(rect=[0, 0.03, 1, 1])

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
        file_name="hvidovre_gamestates_opta.png",
        mime="image/png"
    )

if __name__ == "__main__":
    vis_side()
