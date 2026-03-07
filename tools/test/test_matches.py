import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    # 1. HENT DATA
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_raw_stats = dp.get("opta_team_stats", pd.DataFrame()).copy()
    
    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # Rens status
    df_matches['MATCH_STATUS_CLEAN'] = df_matches['MATCH_STATUS'].astype(str).str.strip().str.capitalize()

    # --- AVANCERET DATA MERGE ---
    if not df_raw_stats.empty:
        try:
            # Pivotering af alle stat-typer (inkl. de nye du bad om)
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

    # --- STYLING ---
    st.markdown("""
        <style>
        .metric-card { background: #f8f9fb; padding: 15px; border-radius: 10px; border: 1px solid #e0e4e8; text-align: center; }
        .metric-label { font-size: 0.7rem; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
        .metric-value { font-size: 1.4rem; font-weight: 800; color: #111; }
        .date-header { background: #f0f2f6; padding: 5px 15px; border-radius: 5px; font-size: 0.8rem; font-weight: bold; margin-top: 15px; color: #333; }
        .score-pill { background: #262730; color: white; border-radius: 4px; padding: 2px 12px; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    # --- FILTRE & LOGO LOGIK ---
    config = dp.get("config", {})
    valgt_hold_navn = config.get("hold_navn", "Hvidovre")
    valgt_uuid = next((i.get("opta_uuid") for n, i in TEAMS.items() if n == valgt_hold_navn), None)
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}

    def hent_logo(uuid):
        for n, i in TEAMS.items():
            if str(i.get("opta_uuid")) == str(uuid):
                return i.get('logo') or f"https://cdn5.wyscout.com/photos/team/public/{i.get('wyid')}_120x120.png"
        return ""

    # --- DYNAMISK BEREGNING AF KPI (Hold-gennemsnit) ---
    played = df_matches[df_matches['MATCH_STATUS_CLEAN'] == 'Played'].copy()
    
    def get_avg(stat_key):
        h_vals = played[played['CONTESTANTHOME_OPTAUUID'] == valgt_uuid][f"{stat_key}_HOME"]
        a_vals = played[played['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid][f"{stat_key}_AWAY"]
        combined = pd.concat([h_vals, a_vals]).dropna()
        return combined.mean() if not combined.empty else 0

    # Beregn værdier dynamisk fra payload
    avg_xg = get_avg('expectedGoals')
    avg_ppda = get_avg('ppda')
    avg_touches_box = get_avg('touchesInBox')
    avg_passes_final = get_avg('passesToFinalThird')

    # --- DASHBOARD TOP ---
    st.title(f"📊 {valgt_hold_navn} Analytics")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"<div class='metric-card'><div class='metric-label'>xG pr. kamp</div><div class='metric-value'>{avg_xg:.2f}</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='metric-card'><div class='metric-label'>PPDA (Pres)</div><div class='metric-value'>{avg_ppda:.1f}</div></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='metric-card'><div class='metric-label'>Felt-berøringer</div><div class='metric-value'>{avg_touches_box:.1f}</div></div>", unsafe_allow_html=True)
    m4.markdown(f"<div class='metric-card'><div class='metric-label'>Final 1/3 Ent.</div><div class='metric-value'>{avg_passes_final:.1f}</div></div>", unsafe_allow_html=True)

    # --- TABS ---
    t_matches, t_style = st.tabs(["Kampprogram", "Spillestil & KPI"])

    with t_matches:
        mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
        team_df = df_matches[mask].copy().sort_values('MATCH_DATE_FULL', ascending=False)

        for _, row in team_df.iterrows():
            is_played = row['MATCH_STATUS_CLEAN'] == 'Played'
            dt = pd.to_datetime(row['MATCH_DATE_FULL'])
            
            st.markdown(f"<div class='date-header'>{dt.strftime('%d. %b %Y').upper()}</div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.5, 1, 0.5, 2])
                
                # Home
                c1.markdown(f"<div style='text-align:right;'><b>{id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'])}</b></div>", unsafe_allow_html=True)
                c2.image(hent_logo(row['CONTESTANTHOME_OPTAUUID']), width=30)
                
                # Score/Time
                if is_played:
                    score = f"{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}"
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{score}</span></div>", unsafe_allow_html=True)
                else:
                    tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                    c3.markdown(f"<div style='text-align:center; font-weight:bold; color:#cc0000;'>Kl. {tid}</div>", unsafe_allow_html=True)
                
                # Away
                c4.image(hent_logo(row['CONTESTANTAWAY_OPTAUUID']), width=30)
                c5.markdown(f"<div><b>{id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'])}</b></div>", unsafe_allow_html=True)

    with t_style:
        col_off, col_def = st.columns(2)
        
        with col_off:
            st.subheader("🚀 Offensiv Profil")
            st.write(f"**Deep Completions:** {get_avg('deepCompletions'):.1f}")
            st.write(f"**Through Passes:** {get_avg('throughPasses'):.1f}")
            st.write(f"**Indlæg (Accuracy):** {get_avg('crossesAcc'):.1f}%")
            
        with col_def:
            st.subheader("🛡️ Defensiv Profil")
            st.write(f"**Skud imod fra DZ:** {get_avg('shotsAgainstDZ'):.1f}")
            st.write(f"**Touches in Box imod:** {get_avg('touchesInBoxAgainst'):.1f}")
            st.write(f"**PPDA:** {avg_ppda:.1f}")

    st.divider()
    st.caption("Data leveret af Opta/Wyscout Hybrid Engine")
