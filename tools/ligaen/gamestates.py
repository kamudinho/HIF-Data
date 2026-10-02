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
    i tre kolonner (Losing, Drawing, Winning) hvor procenterne summer til 100%.
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
        figsize=(13, max(8, len(df) * 0.4)), 
        sharey=True
    )

    # Farver i Opta-stil
    c_losing = '#e57373'
    c_drawing = '#90a4ae'
    c_winning = '#81c784'

    # 1. LOSING barer
    ax_losing.barh(teams, losing, color=c_losing)
    ax_losing.set_title("BAGUD", fontsize=11, fontweight='bold', color='#666666', pad=15)
    ax_losing.invert_yaxis() # Sørg for at topholdet er øverst
    ax_losing.set_xlim(0, 100)

    # 2. DRAWING barer
    ax_drawing.barh(teams, drawing, color=c_drawing)
    ax_drawing.set_title("UAFGJORT", fontsize=11, fontweight='bold', color='#666666', pad=15)
    ax_drawing.set_xlim(0, 100)

    # 3. WINNING barer
    ax_winning.barh(teams, winning, color=c_winning)
    ax_winning.set_title("FØRING", fontsize=11, fontweight='bold', color='#666666', pad=15)
    ax_winning.set_xlim(0, 100)

    # Tilføj afrundede procenter, hvor vi sikrer at summen for visning altid er 100%
    for i in range(len(teams)):
        l_round = int(round(losing.iloc[i]))
        d_round = int(round(drawing.iloc[i]))
        # Lad winning opsluge resten, så det altid går op med 100
        w_round = 100 - (l_round + d_round)

        if l_round > 1:
            ax_losing.text(losing.iloc[i] + 1.5, i, f"{l_round}%", va='center', fontsize=9, color='#333333', fontweight='bold')
        if d_round > 1:
            ax_drawing.text(drawing.iloc[i] + 1.5, i, f"{d_round}%", va='center', fontsize=9, color='#333333', fontweight='bold')
        if w_round > 1:
            ax_winning.text(winning.iloc[i] + 1.5, i, f"{w_round}%", va='center', fontsize=9, color='#333333', fontweight='bold')

    # Fjern alle rammer, gridlines og x-akser helt (Opta minimalistisk stil)
    for ax in [ax_losing, ax_drawing, ax_winning]:
        ax.set_xticks([])
        ax.set_xticklabels([])
        ax.xaxis.grid(False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)

    # Tilføj hovedtitel og undertekst (lige som Opta Analyst eksemplet)
    fig.suptitle("Kampperformance - Hvor længe holdet har været i hver periode ", fontsize=15, fontweight='bold', x=0.08, y=0.98, ha='left', color='#111111')
    fig.text(0.08, 0.93, "Betinia Ligaen 2026-2027", fontsize=11, fontweight='bold', color='#555555', ha='left')

    plt.tight_layout(rect=[0, 0, 1, 0.90])

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
        file_name="betinia_ligaen_gamestates.png",
        mime="image/png"
    )

if __name__ == "__main__":
    vis_side()
