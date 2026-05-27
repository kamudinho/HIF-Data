import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. HJÆLPEFUNKTIONER ---

def get_logo_url(opta_uuid):
    return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

def get_logo_html(uuid):
    url = get_logo_url(uuid)
    return f'<img src="{url}" width="20">' if url else ""

def style_form(f):
    if not f: return ""
    res = ""
    for char in f[-5:]:
        color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
        res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
    return res

def beregn_tabel(df_matches, hold_liste=None):
    stats = {}
    # Initialiser stats for alle hold hvis de ikke er i df
    for uuid, info in TEAMS.items():
        o_uuid = str(info.get('opta_uuid', '')).upper()
        if o_uuid:
            stats[o_uuid] = {'HOLD': info.get('name', 'Ukendt'), 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': o_uuid}

    for _, row in df_matches.sort_values('MATCH_DATE_FULL').iterrows():
        h_uuid, a_uuid = str(row['CONTESTANTHOME_OPTAUUID']).upper(), str(row['CONTESTANTAWAY_OPTAUUID']).upper()
        h_g, a_g = int(row['TOTAL_HOME_SCORE'] or 0), int(row['TOTAL_AWAY_SCORE'] or 0)
        
        for uuid, g_for, g_against, is_home in [(h_uuid, h_g, a_g, True), (a_uuid, a_g, h_g, False)]:
            if uuid not in stats: continue
            stats[uuid]['K'] += 1
            stats[uuid]['M+'] += g_for
            stats[uuid]['M-'] += g_against
            if g_for > g_against:
                stats[uuid]['P'] += 3; stats[uuid]['V'] += 1; stats[uuid]['FORM'] += 'V'
            elif g_for == g_against:
                stats[uuid]['P'] += 1; stats[uuid]['U'] += 1; stats[uuid]['FORM'] += 'U'
            else:
                stats[uuid]['T'] += 1; stats[uuid]['FORM'] += 'T'
    
    df = pd.DataFrame(stats.values())
    df['MD'] = df['M+'] - df['M-']
    return df.sort_values(['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)

# --- 2. DATA LOADING ---

@st.cache_data(ttl=3600)
def load_data():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    df = conn.query(f"SELECT * FROM {db}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'")
    df.columns = [c.upper() for c in df.columns]
    df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'])
    return df

@st.cache_data(ttl=3600)
def get_wyscout_stats():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    return conn.query(f"SELECT t.TEAMNAME, AVG(adv.XG) as XG, AVG(adv.XGPERSHOT) as XGPERSHOT, AVG(adv.SHOTSONTARGET) as SHOTSONTARGET, AVG(adv.SHOTSBLOCKED) as SHOTSBLOCKED, AVG(adv.SHOTSFROMBOX) as SHOTSFROMBOX, AVG(adv.SHOTSFROMDANGERZONE) as SHOTSFROMDANGERZONE, AVG(md.INTERCEPTIONS) as INTERCEPTIONS, AVG(md.TACKLES) as TACKLES, AVG(md.CLEARANCES) as CLEARANCES, AVG(mp.PASSES) as PASSES, AVG(mp.CROSSESTOTAL) as CROSSESTOTAL, AVG(mp.PROGRESSIVEPASSES) as PROGRESSIVEPASSES, AVG(mp.PASSTOFINALTHIRDS) as PASSTOFINALTHIRDS FROM {db}.WYSCOUT_TEAMMATCHES tm JOIN {db}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID WHERE tm.COMPETITION_WYID = 328 GROUP BY t.TEAMNAME")

# --- 3. UI OG LOGIK ---

def vis_tabel(df):
    df_disp = df.copy()
    df_disp.insert(0, '#', df_disp.index + 1)
    df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
    df_disp['FORM'] = df_disp['FORM'].apply(style_form)
    st.write(df_disp[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

def vis_side():
    df = load_data()
    played = df[df['MATCH_STATUS'].str.lower().isin(['played', 'full-time', 'finished'])]
    
    # Grundspil (Runde 1-22)
    grundspil = played[played['WEEK'] <= 22]
    slutspil = played[played['WEEK'] > 22]
    
    tab_gs, tab_op, tab_ned, tab_h2h = st.tabs(["Grundspil", "Oprykningsspil", "Nedrykningsspil", "Head-to-head"])
    
    with tab_gs:
        vis_tabel(beregn_tabel(grundspil))
        
    with tab_op:
        gs_tabel = beregn_tabel(grundspil)
        top6_uuids = gs_tabel.head(6)['UUID'].tolist()
        # Her kombinerer vi point fra grundspil + slutspil for top 6
        vis_tabel(beregn_tabel(played[played['CONTESTANTHOME_OPTAUUID'].isin(top6_uuids)]))

    with tab_ned:
        gs_tabel = beregn_tabel(grundspil)
        bund6_uuids = gs_tabel.tail(6)['UUID'].tolist()
        vis_tabel(beregn_tabel(played[played['CONTESTANTHOME_OPTAUUID'].isin(bund6_uuids)]))

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        idx1 = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        team1 = c1.selectbox("Hold 1", h_list, index=idx1)
        h_list2 = [h for h in h_list if h != team1]
        team2 = c2.selectbox("Hold 2", h_list2, index=0)

        tabs = st.tabs(["Generelt", "xG Stats", "Afslutninger", "Defensivt", "Spilopbygning"])
        with tabs[0]: draw_h2h_chart(team1, team2, ['SHOTS', 'GOALS', 'PPDA', 'MATCHTEMPO'], ['Skud', 'Mål', 'PPDA', 'Tempo'], df_wy, "gen", df_liga)
        with tabs[1]: draw_h2h_chart(team1, team2, ['XG', 'XGPERSHOT'], ['Total xG', 'xG pr. skud'], df_wy, "xg", df_liga)
        with tabs[2]: draw_h2h_chart(team1, team2, ['SHOTSONTARGET', 'SHOTSBLOCKED', 'SHOTSFROMBOX', 'SHOTSFROMDANGERZONE'], ['På mål', 'Blokeret', 'I feltet', 'Danger Zone'], df_wy, "shot", df_liga)
        with tabs[3]: draw_h2h_chart(team1, team2, ['INTERCEPTIONS', 'TACKLES', 'CLEARANCES'], ['Interc.', 'Tackler', 'Clearing'], df_wy, "def", df_liga)
        with tabs[4]: draw_h2h_chart(team1, team2, ['PASSES', 'CROSSESTOTAL', 'PROGRESSIVEPASSES', 'PASSTOFINALTHIRDS'], ['Aflev.', 'Indlæg', 'Progr.', 'Sidste 1/3'], df_wy, "pass", df_liga)

if __name__ == "__main__":
    vis_side()
