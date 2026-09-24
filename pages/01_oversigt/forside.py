# pages/01_oversigt/forside.py
# pages/01_oversigt/forside.py
import streamlit as st
import pandas as pd
import data.hif_load as hif_load
from data.utils.team_mapping import TEAMS, SEASONS, COMPETITIONS, TEAM_COLORS, TOURNAMENTCALENDAR_NAME, COMPETITION_NAME
from data.sql.teams import hent_hurtig_stilling, hent_hold_formkurve

def vis_side():
    # 1. Hent dynamiske data for Hvidovre fra team_mapping
    team_name = "Hvidovre"
    hif_data = TEAMS.get(team_name, {})
    team_wyid = hif_data.get("team_wyid", 7490)
    team_optauuid = hif_data.get("opta_uuid", "")
    logo_url = hif_data.get("logo", "")
    colors = TEAM_COLORS.get(team_name, {"primary": "#df003b", "secondary": "#1a1a1a"})
    primary_color = colors.get("primary", "#df003b")

    # Aktuelle indstillinger fra mapping
    current_season = TOURNAMENTCALENDAR_NAME  # f.eks. "2026/2027" eller "2025/2026"
    current_comp = COMPETITION_NAME           # f.eks. "1. Division"
    
    # Hent den korrekte Opta UUID for sæsonen/turneringen
    calendar_uuid = SEASONS.get(current_season, {}).get(current_comp, "")

    # Top header med logo og titel
    cols = st.columns([1, 8])
    with cols[0]:
        if logo_url:
            st.image(logo_url, width=70)
    with cols[1]:
        st.markdown(f"""
            <div style="font-size: 26px; font-weight: 700; color: #1a1a1a; line-height: 1.2;">
                {team_name} IF – Hovedoversigt
            </div>
            <div style="font-size: 14px; color: #666; margin-top: 4px;">
                Sæson: <b>{current_season}</b> | Turnering: <b>{current_comp}</b> (Wyscout ID: {team_wyid})
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 2. Hent live data fra Snowflake via dine SQL-funktioner
    stilling_df = hent_hurtig_stilling(calendar_uuid) if calendar_uuid else pd.DataFrame()
    form_df = hent_hold_formkurve(calendar_uuid, team_optauuid, limit=5) if calendar_uuid and team_optauuid else pd.DataFrame()

    # Find Hvidovres aktuelle placering i stillingen hvis muligt
    hif_placering = "-"
    hif_point = "-"
    if not stilling_df.empty and 'TEAM_ID' in stilling_df.columns:
        hif_row = stilling_df[stilling_df['TEAM_ID'] == team_optauuid]
        if not hif_row.empty:
            hif_placering = str(hif_row.iloc[0].get('POSITION', '-'))
            hif_point = str(hif_row.iloc[0].get('P', '-'))

    # 3. Metrikker baseret på rigtige data fra databasen
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Ligaplacering", value=hif_placering)
    with col2:
        st.metric(label="Point", value=hif_point)
    with col3:
        st.metric(label="Aktiv Sæson", value=current_season)
    with col4:
        st.metric(label="Turnering", value=current_comp)

    st.divider()

    # 4. Hovedsektion med stilling og formkurve
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader(f"🏆 Aktuel Stilling – {current_comp}")
        if not stilling_df.empty:
            # Vis de vigtigste kolonner i tabellen
            vis_cols = [c for c in ['POSITION', 'HOLD', 'K', 'V', 'U', 'T', 'MF', 'P'] if c in stilling_df.columns]
            st.dataframe(stilling_df[vis_cols], use_container_width=True, hide_index=True)
        else:
            st.info("Ingen stillingsdata tilgængelig for den valgte sæson/turnering.")

    with col_right:
        st.subheader("📈 Seneste Form (5 kampe)")
        if not form_df.empty:
            for _, row in form_df.iterrows():
                res = row.get('RESULTAT', '-')
                modstander = row.get('CONTESTANTAWAY_NAME', '') if row.get('CONTESTANTHOME_OPTAUUID') == team_optauuid else row.get('CONTESTANTHOME_NAME', '')
                dato = str(row.get('MATCH_DATE_FULL', ''))[:10]
                
                # Farvekode for resultat
                f_farve = "#28a745" if res == "V" else ("#ffc107" if res == "U" else "#dc3545")
                st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; margin-bottom: 6px; background: #f8f9fa; border-radius: 4px; border-left: 4px solid {f_farve};">
                        <span><b>{res}</b> mod {modstander}</span>
                        <span style="font-size: 12px; color: #666;">{dato}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Ingen formkurve-data fundet.")

        st.markdown(f"""
            <div style="background-color: #f4f4f4; padding: 12px; border-radius: 6px; border-left: 4px solid {primary_color}; margin-top: 15px; font-size: 13px;">
                <b>Opta UUID Aktiv:</b><br>
                <code>{team_optauuid or 'Ikke sat'}</code>
            </div>
        """, unsafe_allow_html=True)
