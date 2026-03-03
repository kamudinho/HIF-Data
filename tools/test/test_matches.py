import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    # 1. HENT DATA
    df_matches = dp.get("opta_matches", pd.DataFrame())
    
    if df_matches.empty:
        st.error("❌ Data-pakken 'opta_matches' er tom.")
        return

    # --- RENS KOLONNENAVNE (Vigtigt!) ---
    # Fjerner eventuelle kommaer eller mellemrum fra CSV-importen
    df_matches.columns = [c.replace(',', '').strip().upper() for c in df_matches.columns]

    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    # --- DANSKE DATOER ---
    danske_dage = {"Monday": "Mandag", "Tuesday": "Tirsdag", "Wednesday": "Onsdag", "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lørdag", "Sunday": "Søndag"}
    danske_maaneder = {"January": "januar", "February": "februar", "March": "marts", "April": "april", "May": "maj", "June": "juni", "July": "juli", "August": "august", "September": "september", "October": "oktober", "November": "november", "December": "december"}

    def hent_hold_logo(opta_uuid):
        logo_map = dp.get("logo_map", {})
        target_uuid = str(opta_uuid).lower().strip()
        for name, info in TEAMS.items():
            if str(info.get("opta_uuid", "")).lower().strip() == target_uuid:
                wy_id = info.get("team_wyid") or info.get("TEAM_WYID")
                if wy_id and int(wy_id) in logo_map: return logo_map[int(wy_id)]
                if info.get("logo") and info.get("logo") != "-": return info.get("logo")
        return "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"

    # FILTRE
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    
    if not liga_hold_options:
        st.warning(f"Ingen hold fundet for {valgt_liga_global}")
        return

    valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()))
    valgt_uuid = str(liga_hold_options[valgt_navn]).strip()

    # --- FILTRERING ---
    # Vi tvinger UUID'erne til at være strings for at sikre match
    df_matches['CONTESTANTHOME_OPTAUUID'] = df_matches['CONTESTANTHOME_OPTAUUID'].astype(str).str.strip()
    df_matches['CONTESTANTAWAY_OPTAUUID'] = df_matches['CONTESTANTAWAY_OPTAUUID'].astype(str).str.strip()

    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()

    # --- DIAGNOSE (Hvis den stadig er blank) ---
    if team_matches.empty:
        st.write("### 🔍 Diagnose-info")
        st.write(f"Leder efter UUID: `{valgt_uuid}` ({valgt_navn})")
        st.write("UUIDs fundet i data (første 3 hjemmehold):", df_matches['CONTESTANTHOME_OPTAUUID'].unique()[:3].tolist())
        return

    # --- TEGN KAMPE ---
    def tegn_kampe(df, played):
        for _, row in df.iterrows():
            try:
                dt_raw = row.get('MATCH_LOCALDATE')
                if pd.isna(dt_raw) or str(dt_raw) == "NaT": continue
                
                dt = pd.to_datetime(dt_raw)
                dag = danske_dage.get(dt.strftime('%A'), dt.strftime('%A'))
                maaned = danske_maaneder.get(dt.strftime('%B'), dt.strftime('%B'))
                
                st.markdown(f"**{dag.upper()} D. {dt.day}. {maaned.upper()}**")

                t_raw = str(row.get('MATCH_LOCALTIME', ''))
                t_disp = t_raw[:5] if ":" in t_raw else "TBA"

                h_n = id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'])
                a_n = id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'])

                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                    c1.markdown(f"<div style='text-align:right; font-weight:bold;'>{h_n}</div>", unsafe_allow_html=True)
                    c2.image(hent_logo(row['CONTESTANTHOME_OPTAUUID']), width=25)
                    with c3:
                        if played:
                            st.markdown(f"<div style='text-align:center;'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='text-align:center;'>{t_disp}</div>", unsafe_allow_html=True)
                    c4.image(hent_logo(row['CONTESTANTAWAY_OPTAUUID']), width=25)
                    c5.markdown(f"<div style='text-align:left; font-weight:bold;'>{a_n}</div>", unsafe_allow_html=True)
            except: continue

    tab1, tab2 = st.tabs(["Resultater", "Kommende"])
    with tab1:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Played'], True)
    with tab2:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] != 'Played'], False)
