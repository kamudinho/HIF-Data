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

def beregn_tabel(df_matches):
    stats = []
    # Vi henter alle holdnavne og UUID'er fra din TEAMS mapping
    for hold_navn, info in TEAMS.items():
        o_uuid = str(info.get('opta_uuid', '')).upper()
        if o_uuid:
            stats.append({
                'HOLD': hold_navn, 'UUID': o_uuid,
                'K': 0, 'V': 0, 'U': 0, 'T': 0, 
                'M+': 0, 'M-': 0, 'P': 0, 'FORM': ""
            })
    
    df_stats = pd.DataFrame(stats)
    
    # Opdater stats baseret på kampe
    for _, row in df_matches.iterrows():
        h_uuid = str(row['CONTESTANTHOME_OPTAUUID']).upper()
        a_uuid = str(row['CONTESTANTAWAY_OPTAUUID']).upper()
        h_g = int(row['TOTAL_HOME_SCORE'] or 0)
        a_g = int(row['TOTAL_AWAY_SCORE'] or 0)
        
        for uuid, g_for, g_against in [(h_uuid, h_g, a_g), (a_uuid, a_g, h_g)]:
            idx = df_stats[df_stats['UUID'] == uuid].index
            if not idx.empty:
                i = idx[0]
                df_stats.at[i, 'K'] += 1
                df_stats.at[i, 'M+'] += g_for
                df_stats.at[i, 'M-'] += g_against
                if g_for > g_against:
                    df_stats.at[i, 'P'] += 3; df_stats.at[i, 'V'] += 1; df_stats.at[i, 'FORM'] += 'V'
                elif g_for == g_against:
                    df_stats.at[i, 'P'] += 1; df_stats.at[i, 'U'] += 1; df_stats.at[i, 'FORM'] += 'U'
                else:
                    df_stats.at[i, 'T'] += 1; df_stats.at[i, 'FORM'] += 'T'
    
    # Beregn MD og filtrer
    df_stats = df_stats[df_stats['K'] > 0].copy()
    df_stats['MD'] = df_stats['M+'] - df_stats['M-']
    return df_stats.sort_values(['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    
# --- 2. DATA LOADING ---
@st.cache_data(ttl=3600)
def load_data():
    conn = _get_snowflake_conn()
    df = conn.query("SELECT * FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'")
    df.columns = [c.upper() for c in df.columns]
    df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'])
    return df

@st.cache_data(ttl=3600)
def get_wyscout_stats():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    return conn.query(f"SELECT t.TEAMNAME, AVG(adv.XG) as XG, AVG(adv.XGPERSHOT) as XGPERSHOT, AVG(adv.SHOTSONTARGET) as SHOTSONTARGET, AVG(adv.SHOTSBLOCKED) as SHOTSBLOCKED, AVG(adv.SHOTSFROMBOX) as SHOTSFROMBOX, AVG(adv.SHOTSFROMDANGERZONE) as SHOTSFROMDANGERZONE, AVG(md.INTERCEPTIONS) as INTERCEPTIONS, AVG(md.TACKLES) as TACKLES, AVG(md.CLEARANCES) as CLEARANCES, AVG(mp.PASSES) as PASSES, AVG(mp.CROSSESTOTAL) as CROSSESTOTAL, AVG(mp.PROGRESSIVEPASSES) as PROGRESSIVEPASSES, AVG(mp.PASSTOFINALTHIRDS) as PASSTOFINALTHIRDS FROM {db}.WYSCOUT_TEAMMATCHES tm JOIN {db}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID WHERE tm.COMPETITION_WYID = 328 GROUP BY t.TEAMNAME")

# --- 3. CHART FUNKTION (HEAD-TO-HEAD) ---
def draw_h2h_chart(team1, team2, metrics, labels, df_wy, chart_key, df_liga):
    fig = go.Figure()
    col_width = 0.18
    gap = 0.05
    for i, m in enumerate(metrics):
        suffix = f"{i+1}" if i > 0 else ""
        xref, yref = f"x{suffix}", f"y{suffix}"
        d1 = df_wy[df_wy['TEAMNAME'].str.contains(team1, case=False, na=False)]
        d2 = df_wy[df_wy['TEAMNAME'].str.contains(team2, case=False, na=False)]
        v1 = float(d1[m.upper()].iloc[0] if not d1.empty else 0)
        v2 = float(d2[m.upper()].iloc[0] if not d2.empty else 0)
        fig.add_trace(go.Bar(x=[0, 1], y=[v1, v2], marker_color=[TEAM_COLORS.get(team1, {}).get("primary", "#df003b"), TEAM_COLORS.get(team2, {}).get("primary", "#0056a3")], xaxis=xref, yaxis=yref))
        fig.add_annotation(dict(x=0, y=v1, xref=xref, yref=yref, text=f"<b>{v1:.1f}</b>", showarrow=False, yshift=15))
        fig.add_annotation(dict(x=1, y=v2, xref=xref, yref=yref, text=f"<b>{v2:.1f}</b>", showarrow=False, yshift=15))
        fig.update_layout({f"xaxis{suffix}": dict(domain=[i*(col_width+gap), i*(col_width+gap)+col_width], showticklabels=False), f"yaxis{suffix}": dict(visible=False)})
    fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20), plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True, key=chart_key)

# --- 4. HOVEDFUNKTION ---
def vis_side():
    df = load_data()
    df_wy = get_wyscout_stats()
    played = df[df['MATCH_STATUS'].str.lower().isin(['played', 'full-time', 'finished'])]
    
    gs_tabel = beregn_tabel(played[played['WEEK'] <= 22])
    top6_uuids = gs_tabel.head(6)['UUID'].tolist()
    
    tab_gs, tab_op, tab_ned, tab_h2h = st.tabs(["Grundspil", "Oprykningsspil", "Nedrykningsspil", "Head-to-head"])
    
    def render_tabel_ui(df_tabel):
        df_disp = df_tabel.copy()
        df_disp.insert(0, '#', df_disp.index + 1)
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        st.write(df_disp[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with tab_gs: render_tabel_ui(gs_tabel)
    with tab_op: render_tabel_ui(beregn_tabel(played[played['CONTESTANTHOME_OPTAUUID'].isin(top6_uuids)]))
    with tab_ned: render_tabel_ui(beregn_tabel(played[~played['CONTESTANTHOME_OPTAUUID'].isin(top6_uuids)]))
    
    with tab_h2h:
        h_list = sorted(beregn_tabel(played)['HOLD'].tolist())
        c1, c2 = st.columns(2)
        t1 = c1.selectbox("Hold 1", h_list, index=0)
        t2 = c2.selectbox("Hold 2", [h for h in h_list if h != t1], index=0)
        draw_h2h_chart(t1, t2, ['SHOTS', 'GOALS', 'XG'], ['Skud', 'Mål', 'xG'], df_wy, "h2h", beregn_tabel(played))

if __name__ == "__main__":
    st.markdown("<style>.league-table { width: 100%; }</style>", unsafe_allow_html=True)
    vis_side()
