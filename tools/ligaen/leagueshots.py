
import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATA CHECK & KONFIGURATION ---
    df_matches = dp.get("opta", {}).get("team_stats", pd.DataFrame()).copy()
    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "NordicBet Liga") # Fra din COMP_MAP
    
    # Mapping af Opta UUID til Navne
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    # Hent alle hold i den valgte liga
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())
    
    # --- 2. HOLDVALG & FARVESTYRING ---
    # Vi placerer holdvalg øverst
    col_top = st.columns([1, 1, 1])
    with col_top[0]:
        valgt_navn = st.selectbox("Vælg Hold", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # Hent farve med "Hvid-tjek"
    team_cols = TEAM_COLORS.get(valgt_navn, {"primary": "#cc0000", "secondary": "#222222"})
    primary_color = team_cols.get("primary", "#cc0000")
    
    # Hvis primary er hvid (eller meget tæt på), brug secondary
    if primary_color.lower() in ["#ffffff", "#white", "#fff"]:
        primary_color = team_cols.get("secondary", "#222222")

    # --- 3. CSS STYLING (Dynamisk farve indsat) ---
    st.markdown(f"""
        <style>
        .stat-box {{ 
            text-align: center; 
            background: #f8f9fa; 
            border-radius: 6px; 
            padding: 8px 4px; 
            border-bottom: 2px solid {primary_color};
            height: 52px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .stat-label {{ font-size: 10px; color: #666; text-transform: uppercase; font-weight: 600; line-height: 1.1; }}
        .stat-val {{ font-weight: 800; font-size: 16px; color: #111; line-height: 1.1; }}
        
        .date-header {{ background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 15px; border-left: 5px solid {primary_color}; color: #333; }}
        .score-pill {{ background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 80px; text-align: center; }}
        .time-pill {{ text-align: center; font-weight: bold; color: {primary_color}; border: 1px solid {primary_color}; border-radius: 4px; padding: 2px 8px; font-size: 14px; display: inline-block; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 4. DATA FILTRERING ---
    df_matches.columns = [c.upper() for c in df_matches.columns]
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    # Filtrer kampe for det valgte hold
    team_matches = df_matches[
        (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | 
        (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    ].copy()

    # --- 5. STATS RÆKKER (LAYOUT) ---
    col_layout = [2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6]
    
    # Række 1: Sæson + K-S-U-N
    row1 = st.columns(col_layout)
    with row1[0]:
        # Sæson/Periode vælger under holdvalg
        valgt_periode = st.selectbox("Periode", ["Sæson 25/26", "Efterår 25", "Forår 26"], label_visibility="collapsed")

    # Anvend tidsfilter
    if valgt_periode == "Efterår 25":
        p_matches = team_matches[(team_matches['MATCH_DATE_FULL'] >= '2025-07-01') & (team_matches['MATCH_DATE_FULL'] <= '2025-12-31')]
    elif valgt_periode == "Forår 26":
        p_matches = team_matches[(team_matches['MATCH_DATE_FULL'] >= '2026-01-01') & (team_matches['MATCH_DATE_FULL'] <= '2026-06-30')]
    else:
        p_matches = team_matches

    played_p = p_matches[p_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # Beregn K-S-U-N for det valgte hold
    s = {"K": len(played_p), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in played_p.iterrows():
        is_h = str(m['CONTESTANTHOME_OPTAUUID']).upper() == valgt_uuid
        h_s, a_s = int(m.get('TOTAL_HOME_SCORE', 0)), int(m.get('TOTAL_AWAY_SCORE', 0))
        s["M+"] += h_s if is_h else a_s
        s["M-"] += a_s if is_h else h_s
        if h_s == a_s: s["U"] += 1
        elif (is_h and h_s > a_s) or (not is_h and a_s > h_s): s["S"] += 1
        else: s["N"] += 1

    stats_disp = [("K", s["K"]), ("S", s["S"]), ("U", s["U"]), ("N", s["N"]), ("M+", s["M+"]), ("M-", s["M-"]), ("+/-", s["M+"]-s["M-"])]
    for i, (l, v) in enumerate(stats_disp):
        row1[i+1].markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # Række 2: Snit
    row2 = st.columns(col_layout)
    row2[1].markdown(f"<div class='stat-box' style='background:#eee; border-bottom-color:#666;'><div class='stat-label'>SNIT</div><div class='stat-val' style='font-size:9px;'>I PERIODEN</div></div>", unsafe_allow_html=True)
    
    avg_map = [("POSS", "POSS", 1, "%"), ("TOUCHES", "FELT", 0, ""), ("SHOTS", "SKUD", 0, ""), ("XG", "xG", 2, ""), ("PASSES", "PASS", 0, ""), ("FORWARD_PASSES", "FREM", 0, "")]
    for i, (key, label, dec, suffix) in enumerate(avg_map):
        vals = [pd.to_numeric(m.get(f"{'HOME_' if str(m['CONTESTANTHOME_OPTAUUID']).upper() == valgt_uuid else 'AWAY_'}{key}"), errors='coerce') for _, m in played_p.iterrows()]
        avg_val = np.nanmean(vals) if vals else 0
        fmt = f"{avg_val:.{dec}f}{suffix}" if dec > 0 else f"{int(round(avg_val))}{suffix}"
        row2[i+2].markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>{fmt}</div></div>", unsafe_allow_html=True)

    # --- 6. TABS (RESULTATER / TRUP) ---
    st.write("---")
    tab1, tab2, tab3 = st.tabs(["RESULTATER", "KOMMENDE", "SPILLERE"])
    
    with tab1:
        # Genbrug din tegn_kamp_række funktion her, den vil nu automatisk 
        # bruge primary_color og de grå modstander-bars pga. CSS'en ovenfor.
        st.info(f"Viser resultater for {valgt_navn}...")
        # (Indsæt tegn_kamp_række loop her)

    with tab3:
        # Placeholder til dit næste step: Spillervalg
        st.subheader(f"Profilér spillere fra {valgt_navn}")
        # spillere = dp.get("players", df_players) -> filter by team
        st.selectbox("Vælg spiller", ["Vælg spiller...", "Spiller 1", "Spiller 2"], label_visibility="collapsed")
