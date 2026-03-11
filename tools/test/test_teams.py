import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
# Her importerer vi din database-funktion
from data.db_connection import run_query 

def vis_side(df_raw=None):
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet.")
        return
        
    dp = st.session_state["dp"]
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    logo_map = dp.get("logo_map", {})
    df_opta = dp.get("opta", {}).get("matches", pd.DataFrame())
    
    # --- 1. DEFINER OG KØR WYSCOUT QUERY ---
    # Her henter vi de avancerede stats direkte fra dine Wyscout tabeller
    query_adv = """
    SELECT 
        tm.TEAM_WYID, 
        AVG(adv.SHOTS) as SHOTS,
        AVG(adv.XG) as XG,
        AVG(def.PPDA) as PPDA,
        AVG(pas.FORWARDPASSES) as FORWARDPASSES,
        AVG(adv.TOUCHESINBOX) as TOUCHESINBOX
    FROM WYSCOUT_TEAMMATCHES tm
    LEFT JOIN WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
        ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
    LEFT JOIN WYSCOUT_MATCHADVANCEDSTATS_DEFENCE def
        ON tm.MATCH_WYID = def.MATCH_WYID AND tm.TEAM_WYID = def.TEAM_WYID
    LEFT JOIN WYSCOUT_MATCHADVANCEDSTATS_PASSES pas
        ON tm.MATCH_WYID = pas.MATCH_WYID AND tm.TEAM_WYID = pas.TEAM_WYID
    JOIN WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
    JOIN WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
    WHERE tm.COMPETITION_WYID = 328
    AND s.SEASONNAME LIKE '2025%2026'
    GROUP BY tm.TEAM_WYID
    """
    
    # Vi kører queryen og gemmer resultatet i df_adv
    try:
        df_adv = run_query(query_adv)
    except Exception as e:
        st.error(f"Fejl ved hentning af Wyscout data: {e}")
        df_adv = pd.DataFrame()

    if df_opta.empty:
        st.warning("Ingen Opta kampdata fundet.")
        return

    # --- 2. HJÆLPEFUNKTIONER (DIN ORIGINALE LOGIK) ---
    opta_to_wyid = {info['opta_uuid']: info['team_wyid'] for name, info in TEAMS.items() if 'opta_uuid' in info}

    def get_logo_html(uuid):
        wy_id = opta_to_wyid.get(uuid)
        url = logo_map.get(wy_id, "")
        return f'<img src="{url}" width="20">' if url else ""

    def update_form(current_form, result):
        return "".join((list(current_form) + [result])[-5:])

    def style_form(f):
        res = ""
        for char in f:
            color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
            res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
        return res

    # --- 3. BEREGN OPTA TABEL ---
    stats = {}
    for _, row in df_opta.iterrows():
        if row['MATCH_STATUS'] != 'Played': continue
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        h_g, a_g = int(row.get('TOTAL_HOME_SCORE', 0)), int(row.get('TOTAL_AWAY_SCORE', 0))
        winner = str(row.get('WINNER', '')).lower()

        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid}

        s_h, s_a = stats[h_uuid], stats[a_uuid]
        s_h['K'] += 1; s_a['K'] += 1
        s_h['M+'] += h_g; s_h['M-'] += a_g
        s_a['M+'] += a_g; s_a['M-'] += h_g
        if winner == 'home':
            s_h['V'] += 1; s_h['P'] += 3; s_h['FORM'] = update_form(s_h['FORM'], 'V')
            s_a['T'] += 1; s_a['FORM'] = update_form(s_a['FORM'], 'T')
        elif winner == 'away':
            s_a['V'] += 1; s_a['P'] += 3; s_a['FORM'] = update_form(s_a['FORM'], 'V')
            s_h['T'] += 1; s_h['FORM'] = update_form(s_h['FORM'], 'T')
        else:
            s_h['U'] += 1; s_h['P'] += 1; s_h['FORM'] = update_form(s_h['FORM'], 'U')
            s_a['U'] += 1; s_a['P'] += 1; s_a['FORM'] = update_form(s_a['FORM'], 'U')

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    
    # --- 4. MERGE DATA ---
    df_liga['TEAM_WYID'] = df_liga['UUID'].map(opta_to_wyid)
    if not df_adv.empty:
        df_adv.columns = df_adv.columns.str.upper() # Sikrer SHOTS, PPDA osv.
        df_liga = df_liga.merge(df_adv, on='TEAM_WYID', how='left')

    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- 5. VISNING ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', df_disp['UUID'].apply(get_logo_html))
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        
        # Omdøb Wyscout kolonner
        rename_map = {'SHOTS': 'Skud/K', 'PPDA': 'PPDA'}
        df_disp = df_disp.rename(columns={k: v for k, v in rename_map.items() if k in df_disp.columns})
        
        # Dynamisk liste over kolonner (hvis Wyscout data findes)
        vis_cols = ['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P']
        for c in ['Skud/K', 'PPDA']:
            if c in df_disp.columns: vis_cols.append(c)
        vis_cols.append('FORM')
        
        st.markdown("""<style>.league-table { width: 100%; border-collapse: collapse; font-size: 14px; }
            .league-table th, .league-table td { text-align: center !important; padding: 8px; border-bottom: 1px solid #eee; }
            .league-table td:nth-child(3) { text-align: left !important; font-weight: bold; }</style>""", unsafe_allow_html=True)
            
        st.write(df_disp[vis_cols].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)
