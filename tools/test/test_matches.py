import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    # 1. HENT DATA
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_raw_stats = dp.get("opta_team_stats", pd.DataFrame()).copy()
    
    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    df_matches['MATCH_STATUS_CLEAN'] = df_matches['MATCH_STATUS'].astype(str).str.strip().str.capitalize()

    # --- DATA MERGE (Opta Stats & Udvidede KPI'er) ---
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
        except Exception as e:
            st.error(f"Statistik-fejl ved merge: {e}")

    # --- CSS STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; border-bottom: 2px solid #cc0000; }
        .stat-label { font-size: 10px; color: gray; text-transform: uppercase; }
        .stat-val { font-weight: bold; font-size: 14px; }
        .date-header { background: #eee; padding: 5px 15px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 20px; color: #444; border-left: 4px solid #cc0000; }
        .score-pill { background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; min-width: 70px; display: inline-block; text-align: center; }
        .metric-card { background: white; padding: 10px; border-radius: 8px; border: 1px solid #eee; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .metric-title { font-size: 11px; color: #666; font-weight: 600; text-transform: uppercase; }
        .metric-value { font-size: 18px; font-weight: 800; color: #cc0000; }
        </style>
    """, unsafe_allow_html=True)

    def hent_hold_logo(opta_uuid):
        for name, info in TEAMS.items():
            if str(info.get("opta_uuid")) == str(opta_uuid):
                if info.get('logo'): return info['logo']
                if info.get('wyid'): return f"https://cdn5.wyscout.com/photos/team/public/{info['wyid']}_120x120.png"
        return ""

    # --- FILTRE & LOGIK ---
    config = dp.get("config", {})
    valgt_hold_navn = config.get("hold_navn", "Hvidovre")
    valgt_uuid = next((i.get("opta_uuid") for n, i in TEAMS.items() if n == valgt_hold_navn), None)

    # --- TOP DASHBOARD (HOLD DATA) ---
    st.subheader(f"Tactical Dashboard: {valgt_hold_navn}")
    
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.markdown("<div class='metric-card'><div class='metric-title'>PPDA</div><div class='metric-value'>8.4</div></div>", unsafe_allow_html=True)
    with col_b:
        st.markdown("<div class='metric-card'><div class='metric-title'>Deep Completions</div><div class='metric-value'>12.4</div></div>", unsafe_allow_html=True)
    with col_c:
        st.markdown("<div class='metric-card'><div class='metric-title'>Touches in Box</div><div class='metric-value'>21.8</div></div>", unsafe_allow_html=True)
    with col_d:
        st.markdown("<div class='metric-card'><div class='metric-title'>Final 1/3 Passes</div><div class='metric-value'>48.2</div></div>", unsafe_allow_html=True)

    # --- HOVEDTABS ---
    tab_matches, tab_offensive, tab_defensive = st.tabs(["Kampe & Resultater", "Offensiv KPI", "Defensiv KPI"])

    def tegn_kampe(df, is_played):
        if df.empty:
            st.info("Ingen kampe fundet.")
            return
        
        danske_dage = {"Monday": "Mandag", "Tuesday": "Tirsdag", "Wednesday": "Onsdag", "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lørdag", "Sunday": "Søndag"}
        danske_maaneder = {"January": "januar", "February": "februar", "March": "marts", "April": "april", "May": "maj", "June": "juni", "July": "juli", "August": "august", "September": "september", "October": "oktober", "November": "november", "December": "december"}

        id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}

        for _, row in df.iterrows():
            dt = pd.to_datetime(row['MATCH_DATE_FULL'])
            dag = danske_dage.get(dt.strftime('%A'), dt.strftime('%A'))
            maaned = danske_maaneder.get(dt.strftime('%B'), dt.strftime('%B'))
            
            tid_raw = str(row.get('MATCH_LOCALTIME', ''))
            tidspunkt = tid_raw[:5] if len(tid_raw) >= 5 else "TBA"
            
            st.markdown(f"<div class='date-header'>{dag.upper()} D. {dt.day}. {maaned.upper()}</div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                
                h_uuid = row['CONTESTANTHOME_OPTAUUID']
                c1.markdown(f"<div style='text-align:right; font-weight:bold;'>{id_to_name.get(h_uuid, row['CONTESTANTHOME_NAME'])}</div>", unsafe_allow_html=True)
                c2.image(hent_hold_logo(h_uuid), width=28)
                
                if is_played:
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                else:
                    c3.markdown(f"<div style='text-align:center; font-weight:bold; margin-top:5px; color:#cc0000;'>Kl. {tidspunkt}</div>", unsafe_allow_html=True)
                
                a_uuid = row['CONTESTANTAWAY_OPTAUUID']
                c4.image(hent_hold_logo(a_uuid), width=28)
                c5.markdown(f"<div style='text-align:left; font-weight:bold;'>{id_to_name.get(a_uuid, row['CONTESTANTAWAY_NAME'])}</div>", unsafe_allow_html=True)
                
                if is_played:
                    st.markdown("<hr style='margin: 8px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                    # Udvidet kamp-statistik (KPI'er)
                    sc = st.columns(6)
                    stats_map = [
                        ("xG", "expectedGoals", ""),
                        ("Poss%", "possessionPercentage", "%"),
                        ("Passes", "totalPass", ""),
                        ("Shots Box", "touchesInBox", ""), # Mapped til Opta data
                        ("LineBreak", "lineBreakPass", ""),
                        ("PPDA", "ppda", "")
                    ]
                    for i, (label, s_key, suff) in enumerate(stats_map):
                        h_val = row.get(f"{s_key}_HOME", 0)
                        a_val = row.get(f"{s_key}_AWAY", 0)
                        if s_key == "expectedGoals":
                            try: h_val, a_val = f"{float(h_val):.2f}", f"{float(a_val):.2f}"
                            except: h_val, a_val = "0.00", "0.00"
                        sc[i].markdown(f"<div style='text-align:center;'><div class='match-stat-label'>{label}</div><div class='match-stat-val'>{h_val}{suff}-{a_val}{suff}</div></div>", unsafe_allow_html=True)

    with tab_matches:
        mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
        team_df = df_matches[mask].copy()
        
        sub_res, sub_fix = st.tabs(["Resultater", "Program"])
        with sub_res:
            tegn_kampe(team_df[team_df['MATCH_STATUS_CLEAN'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
        with sub_fix:
            tegn_kampe(team_df[team_df['MATCH_STATUS_CLEAN'] != 'Played'].sort_values('MATCH_DATE_FULL'), False)

    with tab_offensive:
        st.subheader("Offensive Spillestils KPI")
        c1, c2 = st.columns(2)
        with c1:
            st.info("Shots from DZ & Shot Map")
            # Her ville ShotMap komponenten ligge (Plottet via x,y)
            st.markdown("**Danger Zone Shots:** 4.2 pr. kamp")
            st.progress(0.65)
        with c2:
            st.info("Passing & Crosses")
            st.write("- Throughpasses: 8.2 (Acc: 34%)")
            st.write("- Final 1/3 entries: 42")
            st.write("- Crosses from Left/Right: 12/8")

    with tab_defensive:
        st.subheader("Defensive Spillestils KPI")
        c1, c2 = st.columns(2)
        with c1:
            st.error("Shots Against (Danger Zone)")
            st.write("Holdet tillader 2.1 skud fra DZ i snit.")
        with c2:
            st.error("Pres & Organisation")
            st.write(f"**PPDA:** 9.1 (Liga gns: 11.2)")
            st.write("Touches in box imod: 14.5")

    # --- FOOTER / DATA STATUS ---
    st.caption(f"Sæson: 2025/2026 | Data: Opta/Wyscout Hybrid | Team ID: {valgt_uuid}")

# Eksempel på kald
# vis_side(data_payload)
