import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. DATA LOADING ---

@st.cache_data(ttl=3600)
def load_data():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    # Opta Data
    df_opta = conn.query(f"SELECT * FROM {db}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'")
    
    # Wyscout Data - Vi bruger SEASONNAME fra din info
    df_wy = conn.query(f"""
        SELECT t.TEAMNAME, t.TEAM_WYID,
               AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, 
               AVG(md.PPDA) as PPDA, AVG(mp.PASSES) as PASSES
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        JOIN {db}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        JOIN {db}.WYSCOUT_SEASONS s ON tm.SEASON_WYID = s.SEASON_WYID
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328 AND s.SEASONNAME = '2025/2026'
        GROUP BY t.TEAMNAME, t.TEAM_WYID
    """)
    return df_opta, df_wy

# --- 2. CHART FUNKTION (MED FEJLSIKRING) ---

# --- OPDATERET CHART FUNKTION ---

def draw_position_performance_chart(df_merged, metric, label):
    if df_merged is None or df_merged.empty:
        st.warning(f"Ingen data tilgængelig for {label}")
        return

    fig = go.Figure()

    # 1. Find det reelle spænd i data
    y_vals = df_merged[metric].dropna()
    if y_vals.empty: return
    
    y_min, y_max = y_vals.min(), y_vals.max()
    y_span = y_max - y_min if y_max != y_min else 1

    # 2. Definer en buffer til top og bund (20% af spændet)
    y_buffer = y_span * 0.2
    y_range_min = y_min - y_buffer
    y_range_max = y_max + y_buffer

    for _, row in df_merged.iterrows():
        team_name = str(row['HOLD'])
        logo_url = next((info['logo'] for name, info in TEAMS.items() if name.lower() in team_name.lower() or team_name.lower() in name.lower()), "")
        
        if logo_url:
            fig.add_layout_image(dict(
                source=logo_url, xref="x", yref="y",
                x=row['#'], y=row[metric],
                sizex=0.5, 
                sizey=y_span * 0.25, # Justeret logo-størrelse
                xanchor="center", 
                yanchor="bottom" # SKIFTET FRA MIDDLE TIL BOTTOM: Logoet står nu ovenpå punktet
            ))

    # 3. Usynlige punkter til hover
    fig.add_trace(go.Scatter(
        x=df_merged['#'], y=df_merged[metric],
        mode='markers', 
        marker=dict(size=40, opacity=0), 
        hovertext=df_merged['HOLD'],
        hovertemplate="<b>%{hovertext}</b><br>Placering: %{x}<br>"+label+": %{y:.2f}<extra></extra>"
    ))

    # 4. Layout: Her tvinger vi faste rammer
    fig.update_layout(
        height=600, 
        margin=dict(t=50, b=80, l=60, r=40),
        xaxis=dict(
            title="<b>Tabelplacering</b>", 
            tickmode='linear', 
            range=[0.4, 12.6],
            gridcolor="#f0f0f0",
            showline=True,
            linewidth=1,
            linecolor='black'
        ),
        yaxis=dict(
            title=f"<b>{label}</b>", 
            gridcolor="#f0f0f0",
            # Vi tvinger aksen til at bruge vores beregnede range uden at autoscale til 0
            range=[y_range_min, y_range_max],
            zeroline=False,
            showline=True,
            linewidth=1,
            linecolor='black'
        ),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig, use_container_width=True)

# --- HOVEDFUNKTION (Radio-buttons fjernet) ---

def vis_side():
    df_opta, df_wy = load_data()
    if df_opta is None or df_opta.empty:
        st.error("Kunne ikke hente Opta data."); return

    df_opta.columns = [c.upper() for c in df_opta.columns]

    # Beregn Tabel
    stats = {}
    for _, row in df_opta.sort_values('MATCH_DATE_FULL').iterrows():
        status = str(row.get('MATCH_STATUS', '')).lower()
        if any(x in status for x in ['played', 'full', 'finish']):
            h_u, a_u = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
            for uuid, name in [(h_u, row['CONTESTANTHOME_NAME']), (a_u, row['CONTESTANTAWAY_NAME'])]:
                if uuid not in stats: stats[uuid] = {'HOLD': name, 'P': 0, 'MD': 0}
            
            h_g, a_g = int(row.get('TOTAL_HOME_SCORE', 0)), int(row.get('TOTAL_AWAY_SCORE', 0))
            stats[h_u]['MD'] += (h_g - a_g); stats[a_u]['MD'] += (a_g - h_g)
            if h_g > a_g: stats[h_u]['P'] += 3
            elif a_g > h_g: stats[a_u]['P'] += 3
            else: stats[h_u]['P'] += 1; stats[a_u]['P'] += 1

    df_liga = pd.DataFrame(stats.values()).sort_values(['P', 'MD'], ascending=False).reset_index(drop=True)
    df_liga['#'] = df_liga.index + 1

    # Merge performance
    performance_list = []
    for _, row in df_liga.iterrows():
        name = row['HOLD'].lower()
        match = df_wy[df_wy['TEAMNAME'].str.lower().apply(lambda x: x in name or name in x)]
        if not match.empty:
            performance_list.append(match.iloc[0].to_dict())
        else:
            performance_list.append({col: np.nan for col in df_wy.columns})

    df_final = pd.concat([df_liga.reset_index(drop=True), pd.DataFrame(performance_list).reset_index(drop=True)], axis=1)

    # UI setup
    st.caption("NordicBet Liga: Tabel vs. Performance")
    
    metric_map = {"xG": "XG", "Mål": "GOALS", "Skud": "SHOTS", "Pres (PPDA)": "PPDA", "Afleveringer": "PASSES"}
    sel_metric = st.selectbox("Vælg Y-akse (Performance)", list(metric_map.keys()))
    
    # Vi tegner nu altid for hele ligaen (12 hold) uden radio-buttons
    draw_position_performance_chart(df_final, metric_map[sel_metric], sel_metric)

if __name__ == "__main__":
    vis_side()
