import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATAGRUNDLAG ---
    # Henter data fra din loader (sikrer vi bruger de rigtige nøgler fra din get_opta_queries)
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_raw_stats = dp.get("opta_team_stats", pd.DataFrame()).copy()
    # Din query hedder "wyscout_match_history" i SQL-filen, men loades ofte som "match_history" i dp
    df_wy = dp.get("match_history", pd.DataFrame()).copy() 
    
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    if df_matches.empty:
        st.warning("Ingen kampdata fundet i Snowflake.")
        return

    # --- 2. FORBERED DATA (INGEN DATE_ONLY REFERENCER) ---
    df_matches['MATCH_STATUS_CLEAN'] = df_matches['MATCH_STATUS'].astype(str).str.strip().str.capitalize()
    
    # Konvertér datoer til datetime objekter med det samme
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'])
    if not df_wy.empty:
        df_wy['DATE'] = pd.to_datetime(df_wy['DATE'])

    # --- 3. LOOKUP & MAPPING ---
    opta_to_wyid = {v['opta_uuid']: v['team_wyid'] for k, v in TEAMS.items() if v.get('opta_uuid')}
    opta_to_name = {v['opta_uuid']: k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    # --- 4. OPTA TEAM STATS PIVOT ---
    if not df_raw_stats.empty:
        try:
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', values='STAT_TOTAL', aggfunc='first'
            ).reset_index()
            
            df_h = df_pivot.add_suffix('_HOME')
            df_a = df_pivot.add_suffix('_AWAY')

            df_matches = pd.merge(df_matches, df_h, left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], 
                                 right_on=['MATCH_OPTAUUID_HOME', 'CONTESTANT_OPTAUUID_HOME'], how='left')
            df_matches = pd.merge(df_matches, df_a, left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], 
                                 right_on=['MATCH_OPTAUUID_AWAY', 'CONTESTANT_OPTAUUID_AWAY'], how='left')
        except Exception:
            pass

    # --- 5. UI & FILTRERING ---
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())
    
    valgt_navn = st.selectbox("Vælg hold", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
    valgt_uuid = liga_hold_options[valgt_navn]

    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()
    played = team_matches[team_matches['MATCH_STATUS_CLEAN'] == 'Played']

    # --- 6. TEGN KAMPE FUNKTION (RETTET TIL GAMEWEEK + DATE) ---
    def tegn_kampe(df_list, is_played):
        if df_list.empty:
            st.info("Ingen kampe fundet.")
            return

        for _, row in df_list.iterrows():
            # Hent ID'er og Gameweek
            h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
            h_wyid, a_wyid = opta_to_wyid.get(h_uuid), opta_to_wyid.get(a_uuid)
            aktuel_runde = row.get('GAMEWEEK')
            
            # --- KOBLING TIL WYSCOUT VIA GAMEWEEK ---
            wy_match = pd.DataFrame()
            if not df_wy.empty and aktuel_runde:
                # Vi matcher på GAMEWEEK da det er unikt pr. runde i din query
                wy_match = df_wy[df_wy['GAMEWEEK'] == aktuel_runde]
            
            # Udpakning af værdier
            xg_display = ""
            if not wy_match.empty and is_played:
                val_xg = wy_match.iloc[0].get('XG', 0)
                xg_display = f"xG {val_xg:.2f}" if val_xg else ""

            # Dato formatering (Bruger MATCH_DATE_FULL direkte)
            dato_str = row['MATCH_DATE_FULL'].strftime('%d. %B %Y').upper()
            st.markdown(f"**{dato_str}** — Runde {aktuel_runde}")
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.5, 1, 0.5, 2])
                h_name = opta_to_name.get(h_uuid, row['CONTESTANTHOME_NAME'])
                a_name = opta_to_name.get(a_uuid, row['CONTESTANTAWAY_NAME'])

                c1.write(f"**{h_name}**")
                c2.image(TEAMS.get(h_name, {}).get('logo', ''), width=30)
                
                if is_played:
                    score = f"{int(row.get('TOTAL_HOME_SCORE', 0))} - {int(row.get('TOTAL_AWAY_SCORE', 0))}"
                    c3.markdown(f"<div style='text-align:center'><b>{score}</b><br><small>{xg_display}</small></div>", unsafe_allow_html=True)
                else:
                    tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                    c3.write(f"Kl. {tid}")
                
                c4.image(TEAMS.get(a_name, {}).get('logo', ''), width=30)
                c5.write(f"**{a_name}**")

    # --- 7. TABS ---
    tab1, tab2 = st.tabs(["Resultater", "Program"])
    with tab1:
        tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab2:
        future = team_matches[team_matches['MATCH_STATUS_CLEAN'] != 'Played']
        tegn_kampe(future.sort_values('MATCH_DATE_FULL'), False)
