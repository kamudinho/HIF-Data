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

    # Beregn range for y-aksen og giv luft i bunden
    y_vals = df_merged[metric].dropna()
    if y_vals.empty: return
    
    y_min, y_max = y_vals.min(), y_vals.max()
    # Vi sætter bunden til f.eks. 15% under den laveste værdi for at sikre hele logoet vises
    y_bottom = y_min - (y_max - y_min) * 0.15 if y_max != y_min else y_min * 0.8

    for _, row in df_merged.iterrows():
        team_name = str(row['HOLD'])
        logo_url = next((info['logo'] for name, info in TEAMS.items() if name.lower() in team_name.lower() or team_name.lower() in name.lower()), "")
        
        if logo_url:
            fig.add_layout_image(dict(
                source=logo_url, xref="x", yref="y",
                x=row['#'], y=row[metric],
                sizex=0.5, sizey=0.15 * (y_max - y_bottom), # Skalerer logo-størrelsen
                xanchor="center", yanchor="middle"
            ))

    fig.add_trace(go.Scatter(
        x=df_merged['#'], y=df_merged[metric],
        mode='markers', marker=dict(size=30, opacity=0), # Usynlige punkter til hover
        hovertext=df_merged['HOLD'],
        hovertemplate="<b>%{hovertext}</b><br>Placering: %{x}<br>"+label+": %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        height=500, margin=dict(t=20, b=40, l=40, r=40),
        xaxis=dict(
            title="Tabelplacering", 
            tickmode='linear', 
            range=[0.5, 12.5], # Fastlåst til de 12 hold i NordicBet Ligaen
            gridcolor="#eee"
        ),
        yaxis=dict(
            title=label, 
            gridcolor="#eee",
            range=[y_bottom, y_max * 1.1] # Giver luft både i top og bund
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
    st.title("NordicBet Liga: Tabel vs. Performance")
    
    metric_map = {"xG": "XG", "Mål": "GOALS", "Skud": "SHOTS", "Pres (PPDA)": "PPDA", "Afleveringer": "PASSES"}
    sel_metric = st.selectbox("Vælg Y-akse (Performance)", list(metric_map.keys()))
    
    # Vi tegner nu altid for hele ligaen (12 hold) uden radio-buttons
    draw_position_performance_chart(df_final, metric_map[sel_metric], sel_metric)

if __name__ == "__main__":
    vis_side()
