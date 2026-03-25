import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. HJÆLPEFUNKTIONER (Defineret øverst for at undgå 'not defined' fejl) ---

def get_logo_url(opta_uuid):
    """Finder logo URL baseret på Opta UUID via TEAMS mapping."""
    return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

def get_logo_html(uuid):
    url = get_logo_url(uuid)
    return f'<img src="{url}" width="20">' if url else ""

def style_form(f):
    res = ""
    for char in f[-5:]:
        color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
        res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
    return res

# --- 2. DATA LOADING ---

@st.cache_data(ttl=3600)
def load_liga_data():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
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
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    query = f"""
        SELECT t.TEAMNAME, 
               AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, 
               AVG(adv.XGPERSHOT) as XGPERSHOT, AVG(adv.SHOTSONTARGET) as SHOTSONTARGET, 
               AVG(md.INTERCEPTIONS) as INTERCEPTIONS, AVG(md.PPDA) as PPDA, AVG(mp.PASSES) as PASSES
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        JOIN {db}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328
        GROUP BY t.TEAMNAME
    """
    return pd.read_sql(query, conn)

# --- 3. HOVEDFUNKTION ---

def vis_side(dp_unused=None):
    df_opta = load_liga_data()
    df_wy = get_wyscout_stats()

    if df_opta.empty:
        st.warning("Ingen data fundet i Snowflake.")
        return

    # Beregn Ligatabel
    df_opta['MATCH_DATE_FULL'] = pd.to_datetime(df_opta['MATCH_DATE_FULL'])
    stats = {}
    for _, row in df_opta.sort_values('MATCH_DATE_FULL').iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'MD': 0, 'P': 0, 'FORM': "", 'UUID': uuid}
        
        if str(row['MATCH_STATUS']).strip().lower() == 'played':
            h_g, a_g = int(row['TOTAL_HOME_SCORE'] or 0), int(row['TOTAL_AWAY_SCORE'] or 0)
            stats[h_uuid]['K'] += 1; stats[a_uuid]['K'] += 1
            stats[h_uuid]['MD'] += (h_g - a_g); stats[a_uuid]['MD'] += (a_g - h_g)
            if h_g > a_g:
                stats[h_uuid]['P'] += 3; stats[h_uuid]['FORM'] += 'V'; stats[a_uuid]['FORM'] += 'T'
            elif a_g > h_g:
                stats[a_uuid]['P'] += 3; stats[a_uuid]['FORM'] += 'V'; stats[h_uuid]['FORM'] += 'T'
            else:
                stats[h_uuid]['P'] += 1; stats[a_uuid]['P'] += 1; stats[h_uuid]['FORM'] += 'U'; stats[a_uuid]['FORM'] += 'U'

    df_liga = pd.DataFrame(stats.values()).sort_values(['P', 'MD'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        st.markdown("<style>.league-table { width: 100%; border-collapse: collapse; font-size: 14px; text-align: center; }</style>", unsafe_allow_html=True)
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        st.write(df_disp[['#', ' ', 'HOLD', 'K', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("HB Køge") if "HB Køge" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1], index=h_list.index("AaB")-1 if "AaB" in h_list else 0)

        if not df_wy.empty:
            metrics = ['SHOTS', 'XG', 'PASSES', 'PPDA']
            labels = ['Skud', 'xG', 'Afleveringer', 'PPDA']
            
            fig = make_subplots(rows=1, cols=len(metrics), horizontal_spacing=0.08)
            
            # Find UUIDs og logoer
            u1 = df_liga[df_liga['HOLD'] == team1]['UUID'].values[0]
            u2 = df_liga[df_liga['HOLD'] == team2]['UUID'].values[0]
            l1, l2 = get_logo_url(u1), get_logo_url(u2)

            for i, m in enumerate(metrics):
                axis_suffix = f"{i+1}" if i > 0 else ""
                xref_name = f"x{axis_suffix}"
                yref_name = f"y{axis_suffix}"
                
                v1 = df_wy[df_wy['TEAMNAME'].str.contains(team1, case=False, na=False)][m].mean()
                v2 = df_wy[df_wy['TEAMNAME'].str.contains(team2, case=False, na=False)][m].mean()

                # Søjler (placeret på x=0 og x=1)
                fig.add_trace(go.Bar(x=[0], y=[v1], marker_color=TEAM_COLORS.get(team1, {}).get("primary", "#df003b"), width=0.7, showlegend=False), row=1, col=i+1)
                fig.add_trace(go.Bar(x=[1], y=[v2], marker_color=TEAM_COLORS.get(team2, {}).get("primary", "#0056a3"), width=0.7, showlegend=False), row=1, col=i+1)
                
                # Labels under graferne
                fig.add_annotation(dict(
                    x=0.5, y=-0.25, xref=f"{xref_name} domain", yref=f"{yref_name} domain",
                    text=labels[i], showarrow=False, font=dict(size=12, weight="bold")
                ))

                # Logoer placeret over hver søjle
                if l1:
                    fig.add_layout_image(dict(
                        source=l1, xref=xref_name, yref="paper",
                        x=0, y=1.05, sizex=0.35, sizey=0.35, xanchor="center", yanchor="bottom"
                    ))
                if l2:
                    fig.add_layout_image(dict(
                        source=l2, xref=xref_name, yref="paper",
                        x=1, y=1.05, sizex=0.35, sizey=0.35, xanchor="center", yanchor="bottom"
                    ))

                # Opdater akser
                fig.update_xaxes(range=[-0.8, 1.8], showticklabels=False, row=1, col=i+1)
                fig.update_yaxes(range=[0, max(v1, v2) * 1.5], visible=False, row=1, col=i+1)

            fig.update_layout(height=350, margin=dict(t=80, b=60, l=10, r=10), plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
