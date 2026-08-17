import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from data.utils.spiller_qualifiers import ACTION_CATEGORIES, POSITION_ACTIONS
from utils.helpers import get_ordinal

# ---------------------------------------------------------------------------
# Konstanter specifikke for Spillerprofil-visningen
# (bevidst duplikeret fra player_stats.py, så denne fil er selvstændig og
# ikke skaber en cirkulær afhængighed mellem filerne)
# ---------------------------------------------------------------------------
POSITION_DA = {
    "Goalkeeper": "Målmand",
    "Defender": "Forsvar",
    "Midfielder": "Midtbane",
    "Attacker": "Angriber",
}
POSITION_DA_FLERTAL = {
    "Goalkeeper": "målmænd",
    "Defender": "forsvarsspillere",
    "Midfielder": "midtbanespillere",
    "Attacker": "angribere",
}
POSITION_TO_SPQ = {
    "Goalkeeper": "GK",
    "Defender": "DEF",
    "Midfielder": "MID",
    "Attacker": "FWD",
}


def byg_kategori_visning(spq_position: str) -> dict:
    """
    Returnerer {"offensiv": [(LABEL, kategori_nøgle), ...], "defensiv": [...]}
    for en given spiller_qualifiers-position (GK/DEF/MID/FWD) - direkte
    afspejling af POSITION_ACTIONS, uden at klippe kategorier af.
    """
    return {
        side: [(ACTION_CATEGORIES[k]["navn"].upper(), k) for k in POSITION_ACTIONS[spq_position][side]]
        for side in ("offensiv", "defensiv")
    }


# Statistik-kategorier vist i "hjul"-grafikkerne, opdelt offensivt/defensivt,
# bygget dynamisk ud fra spiller_qualifiers.POSITION_ACTIONS.
KATEGORI_PER_POSITION = {
    eng_pos: byg_kategori_visning(spq_pos)
    for eng_pos, spq_pos in POSITION_TO_SPQ.items()
}
# "Fremadrettede pasninger" er koordinat-baseret (beregnet i player_stats.py's
# databehandling, ikke en del af ACTION_CATEGORIES), så den tilføjes manuelt
# til de udspillende positioner.
for _eng_pos in ("Defender", "Midfielder", "Attacker"):
    KATEGORI_PER_POSITION[_eng_pos]["offensiv"].append(("FREMADRETTEDE PASNINGER", "fremadrettede_pasninger"))

DEFAULT_KAT_LISTE = byg_kategori_visning("MID")
DEFAULT_KAT_LISTE["offensiv"].append(("FREMADRETTEDE PASNINGER", "fremadrettede_pasninger"))


def create_relative_donut(player_val, max_val, label, rank_text, color="#df003b"):
    base_max = max(max_val, player_val, 1)
    reminder = base_max - player_val
    fig = go.Figure(go.Pie(
        values=[player_val, reminder],
        hole=0.7,
        marker_colors=[color, "#eeeeee"],
        textinfo='none',
        hoverinfo='none',
        rotation=0,
        direction='clockwise',
        sort=False
    ))
    fig.update_layout(
        showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=110, width=130,
        annotations=[dict(
            text=f"<b>{player_val}</b><br><span style='font-size:12px; color:{color}; font-weight:bold;'>{rank_text}</span>",
            x=0.5, y=0.5, font_size=16, showarrow=False, font_family="Arial"
        )]
    )
    return fig


def render_spillerprofil(truppen_stats: pd.DataFrame, truppen_stats_liga: pd.DataFrame,
                          valgt_player_uuid: str, valgt_spiller: str, spiller_position: str,
                          hold_logo, primær_farve: str):
    """
    Renderer Spillerprofil-fanen: kampdata-boks + offensive/defensive
    statistik-hjul. truppen_stats/truppen_stats_liga skal allerede indeholde
    'Position'-kolonnen og alle kategori-kolonner fra player_stats.py's
    databehandling (byg_spiller_og_holdstats).
    """
    if truppen_stats.empty or valgt_player_uuid not in truppen_stats.index:
        st.info("Ingen spillerdata tilgængelig.")
        return

    if spiller_position != 'Ukendt':
        sammenligningsgruppe = truppen_stats_liga[truppen_stats_liga['Position'] == spiller_position]
        if sammenligningsgruppe.empty:
            sammenligningsgruppe = truppen_stats_liga
    else:
        sammenligningsgruppe = truppen_stats_liga

    numeric_cols = sammenligningsgruppe.drop(columns=['visningsnavn', 'Pasningsprocent_Str', 'Position'], errors='ignore')
    ranks = (-numeric_cols).rank(ascending=True, method='min').astype(int)

    try:
        spiller_ranks = ranks.loc[valgt_player_uuid]
        if isinstance(spiller_ranks, pd.DataFrame):
            spiller_ranks = spiller_ranks.iloc[0]
        s_data = truppen_stats.loc[valgt_player_uuid]
        if isinstance(s_data, pd.DataFrame):
            s_data = s_data.iloc[0]
    except KeyError:
        st.error(f"Kunne ikke finde stats for spiller: {valgt_spiller}")
        return

    main_col_left, main_col_right = st.columns([1.3, 4])

    with main_col_left:
        logo_html = ""
        if hold_logo is not None:
            import io
            import base64
            buffered = io.BytesIO()
            hold_logo.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            logo_html = f'<img src="data:image/png;base64,{img_str}" style="height: 35px; margin-right: 12px;">'

        position_label = POSITION_DA.get(spiller_position, spiller_position)
        st.markdown(f'''<div style="display: flex; align-items: center; margin-bottom: 10px;">{logo_html}<div>
                <div style="font-size: 18px; font-weight: bold; line-height: 1.2;">{valgt_spiller}</div>
                <div style="font-size: 12px; color: #888;">{position_label}</div>
            </div></div>''', unsafe_allow_html=True)
        st.markdown("<hr style='margin: 10px 0; opacity: 0.5;'>", unsafe_allow_html=True)

        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; border: 1px solid #e9ecef;">
                <h4 style="margin: 0 0 10px 0; font-size: 14px; text-transform: uppercase; font-weight: bold;">Kampdata</h4>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Kampe:</b></span><span>{int(s_data['Kampe'])}</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Minutter:</b></span><span>{int(s_data['Minutter'])}'</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Mål (xG):</b></span><span>{int(s_data['Mål'])} ({round(s_data['xG'], 2)})</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Assists (xA):</b></span><span>{int(s_data['Assists'])} ({round(s_data['xA'], 2)})</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Gule kort:</b></span><span>{int(s_data['Gule_kort'])}</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Røde kort:</b></span><span>{int(s_data['Roede_kort'])}</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 13px;"><span><b>Indskiftet:</b></span><span>{int(s_data['Indskiftet'])}</span></div>
                <div style="display: flex; justify-content: space-between; font-size: 13px;"><span><b>Udskiftet:</b></span><span>{int(s_data['Udskiftet'])}</span></div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
        gruppe_navn = POSITION_DA_FLERTAL.get(spiller_position, "spillere")
        st.caption(f"Sammenlignet med alle {gruppe_navn} i ligaen.")

    with main_col_right:
        kat_dict = KATEGORI_PER_POSITION.get(spiller_position, DEFAULT_KAT_LISTE)

        for side_label, side_key in (("Offensivt", "offensiv"), ("Defensivt", "defensiv")):
            kat_liste = [(label, k_id) for label, k_id in kat_dict[side_key] if k_id in truppen_stats.columns]
            if not kat_liste:
                continue

            st.markdown(
                f"<p style='font-weight:bold; font-size:12px; color:#888; "
                f"text-transform:uppercase; letter-spacing:0.5px; margin:12px 0 6px 0;'>{side_label}</p>",
                unsafe_allow_html=True
            )

            for i in range(0, len(kat_liste), 4):
                cols = st.columns(4)
                for j, (label, k_id) in enumerate(kat_liste[i:i + 4]):
                    with cols[j]:
                        st.markdown(f"<p style='text-align:center; font-weight:bold; font-size:12px; margin-bottom:0px;'>{label}</p>", unsafe_allow_html=True)
                        player_val = truppen_stats.loc[valgt_player_uuid, k_id]
                        if isinstance(player_val, pd.Series):
                            player_val = player_val.iloc[0]
                        max_val = sammenligningsgruppe[k_id].max() if k_id in sammenligningsgruppe.columns else 1
                        rank_val = spiller_ranks[k_id] if k_id in spiller_ranks.index else 1
                        fig = create_relative_donut(player_val, max_val, label, get_ordinal(rank_val), color=primær_farve)
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"p_{side_key}_{k_id}_{i}_{j}")
