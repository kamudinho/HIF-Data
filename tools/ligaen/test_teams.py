import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. DATA LOADING (SELVSTÆNDIG) ---

@st.cache_data(ttl=3600)
def load_liga_data():
    """Henter Opta kampsats til ligatabellen."""
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    # Vi henter kun de nødvendige kolonner for at bygge tabellen
    query = f"""
        SELECT 
            MATCH_DATE_FULL, MATCH_STATUS,
            CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME,
            CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
            TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
        FROM {db}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'
    """
    return pd.read_sql(query, conn)

@st.cache_data(ttl=3600)
def get_wyscout_stats():
    """Henter de avancerede stats fra Wyscout."""
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    query = f"""
        SELECT t.TEAMNAME, 
               AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, 
               AVG(adv.XGPERSHOT) as XGPERSHOT, AVG(adv.SHOTSONTARGET) as SHOTSONTARGET, 
               AVG(adv.SHOTSBLOCKED) as SHOTSBLOCKED, AVG(adv.SHOTSOUTSIDEBOX) as SHOTSOUTSIDEBOX, 
               AVG(adv.SHOTSFROMBOX) as SHOTSFROMBOX, AVG(md.INTERCEPTIONS) as INTERCEPTIONS, 
               AVG(md.TACKLES) as TACKLES, AVG(md.PPDA) as PPDA, AVG(mp.PASSES) as PASSES,
               AVG(mp.PROGRESSIVEPASSES) as PROGRESSIVEPASSES, AVG(mp.MATCHTEMPO) as MATCHTEMPO
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        JOIN {db}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328
        GROUP BY t.TEAMNAME
    """
    return pd.read_sql(query, conn)

# --- 2. HJÆLPEFUNKTIONER ---

def get_logo_url(opta_uuid):
    wy_id = next((info.get('team_wyid') for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    # Fallback til standard logos i TEAMS hvis mapping fejler
    return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

def get_logo_html(uuid):
    url = get_logo_url(uuid)
    return f'<img src="{url}" width="20">' if url else ""

def style_form(f):
    res = ""
    for char in f[-5:]: # Vis kun de sidste 5
        color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
        res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
    return res

def get_text_color(hex_color):
    if not hex_color: return "white"
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return "black" if (r * 0.299 + g * 0.587 + b * 0.114) > 165 else "white"

# --- 3. HOVEDFUNKTION ---

def vis_side(dp_unused=None):
    st.subheader("Holdoversigt & Ligatabel")

    # Load data
    df_opta = load_liga_data()
    df_wy = get_wyscout_stats()

    if df_opta.empty:
        st.warning("Kunne ikke hente data fra Snowflake.")
        return

    # --- DATABEREGNING (LIGATABEL) ---
    df_opta['MATCH_DATE_FULL'] = pd.to_datetime(df_opta['MATCH_DATE_FULL'])
    df_opta = df_opta.sort_values('MATCH_DATE_FULL')

    stats = {}
    for _, row in df_opta.iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid}
        
        if str(row['MATCH_STATUS']).strip().capitalize() == 'Played':
            h_g = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
            a_g = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            s_h['K'] += 1; s_a['K'] += 1
            s_h['M+'] += h_g; s_h['M-'] += a_g
            s_a['M+'] += a_g; s_a['M-'] += h_g
            
            if h_g > a_g:
                s_h['V'] += 1; s_h['P'] += 3; s_h['FORM'] += 'V'
                s_a['T'] += 1; s_a['FORM'] += 'T'
            elif a_g > h_g:
                s_a['V'] += 1; s_a['P'] += 3; s_a['FORM'] += 'V'
                s_h['T'] += 1; s_h['FORM'] += 'T'
            else:
                s_h['U'] += 1; s_h['P'] += 1; s_h['FORM'] += 'U'
                s_a['U'] += 1; s_a['P'] += 1; s_a['FORM'] += 'U'

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- LAYOUT TABS ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head (Stats)"])

    with t_liga:
        st.markdown("""<style>
            .league-table { width: 100%; border-collapse: collapse; font-size: 14px; }
            .league-table th { background-color: rgba(128,128,128,0.1); padding: 8px; text-align: center; }
            .league-table td { padding: 8px; border-bottom: 1px solid rgba(128,128,128,0.2); text-align: center; }
            .league-table td:nth-child(3) { text-align: left !important; font-weight: bold; }
        </style>""", unsafe_allow_html=True)
        
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        
        st.write(df_disp[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        # Tegn sammenligning
        if not df_wy.empty:
            metrics = ['SHOTS', 'XG', 'PASSES', 'PPDA']
            labels = ['Skud', 'xG', 'Afleveringer', 'PPDA']
            
            d1 = df_wy[df_wy['TEAMNAME'].str.contains(team1, case=False, na=False)].iloc[0]
            d2 = df_wy[df_wy['TEAMNAME'].str.contains(team2, case=False, na=False)].iloc[0]

            fig = make_subplots(rows=1, cols=len(metrics))
            
            for i, m in enumerate(metrics):
                v1, v2 = d1[m], d2[m]
                
                fig.add_trace(go.Bar(x=[team1], y=[v1], marker_color=TEAM_COLORS.get(team1, {"primary": "#df003b"})["primary"], showlegend=False), row=1, col=i+1)
                fig.add_trace(go.Bar(x=[team2], y=[v2], marker_color=TEAM_COLORS.get(team2, {"primary": "#0056a3"})["primary"], showlegend=False), row=1, col=i+1)
                fig.update_xaxes(showticklabels=False, row=1, col=i+1)
                fig.add_annotation(dict(x=0.5, y=-0.15, xref=f"x{i+1} domain", yref=f"y{i+1} domain", text=labels[i], showarrow=False))

            fig.update_layout(height=300, margin=dict(t=20, b=50), plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

