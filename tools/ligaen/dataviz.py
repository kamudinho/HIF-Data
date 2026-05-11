import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. DATA LOADING & TABEL-LOGIK ---

@st.cache_data(ttl=3600)
def load_data():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    # Hent Opta kampdata
    df_opta = conn.query(f"SELECT * FROM {db}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'")
    
    # Hent Wyscout stats
    df_wy = conn.query(f"""
        SELECT t.TEAMNAME, t.TEAM_WYID,
               AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, 
               AVG(md.PPDA) as PPDA, AVG(mp.PASSES) as PASSES
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        JOIN {db}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328
        GROUP BY t.TEAMNAME, t.TEAM_WYID
    """)
    return df_opta, df_wy

# --- 2. CHART FUNKTION (TABEL VS PERFORMANCE) ---

def draw_position_performance_chart(df_merged, metric, label):
    fig = go.Figure()

    # Find min/max for Y-aksen for at skalere logoer pænt
    y_min, y_max = df_merged[metric].min(), df_merged[metric].max()
    y_range = y_max - y_min if y_max != y_min else 1

    for i, row in df_merged.iterrows():
        # Match logo via TEAMS mapping
        team_name = row['HOLD']
        logo_url = next((info['logo'] for name, info in TEAMS.items() if name.lower() in team_name.lower()), "")
        
        if logo_url:
            fig.add_layout_image(dict(
                source=logo_url, xref="x", yref="y",
                x=row['#'], y=row[metric],
                sizex=0.5, sizey=y_range * 0.15,
                xanchor="center", yanchor="middle"
            ))

    # Usynligt scatter-lag for hover-effekt
    fig.add_trace(go.Scatter(
        x=df_merged['#'], y=df_merged[metric],
        mode='markers', marker=dict(size=25, opacity=0),
        hovertext=df_merged['HOLD'],
        hovertemplate="<b>%{hovertext}</b><br>Placering: %{x}<br>"+label+": %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        height=450, margin=dict(t=40, b=40, l=40, r=40),
        xaxis=dict(title="Aktuel Tabelplacering", tickmode='linear', range=[0, len(df_merged)+1], gridcolor="#eee"),
        yaxis=dict(title=label, gridcolor="#eee"),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig, use_container_width=True)

# --- 3. HOVEDFUNKTION ---

def vis_side():
    df_opta, df_wy = load_data()
    df_opta.columns = [c.upper() for c in df_opta.columns]

    # --- BEREGN TABEL (Opta) ---
    stats = {}
    for _, row in df_opta.sort_values('MATCH_DATE_FULL').iterrows():
        status = str(row['MATCH_STATUS']).lower()
        if 'played' in status or 'full-time' in status:
            h_u, a_u = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
            for uuid, name in [(h_u, row['CONTESTANTHOME_NAME']), (a_u, row['CONTESTANTAWAY_NAME'])]:
                if uuid not in stats: stats[uuid] = {'HOLD': name, 'P': 0, 'MD': 0, 'UUID': uuid}
            
            h_g, a_g = int(row['TOTAL_HOME_SCORE'] or 0), int(row['TOTAL_AWAY_SCORE'] or 0)
            stats[h_u]['MD'] += (h_g - a_g); stats[a_u]['MD'] += (a_g - h_g)
            if h_g > a_g: stats[h_u]['P'] += 3
            elif a_g > h_g: stats[a_u]['P'] += 3
            else: stats[h_u]['P'] += 1; stats[a_u]['P'] += 1

    df_liga = pd.DataFrame(stats.values()).sort_values(['P', 'MD'], ascending=False).reset_index(drop=True)
    df_liga['#'] = df_liga.index + 1

    # --- MERGE MED PERFORMANCE (Wyscout) ---
    # Vi bruger en fuzzy match eller navne-match da vi kombinerer Opta og Wyscout
    def find_wy_stats(hold_navn):
        match = df_wy[df_wy['TEAMNAME'].apply(lambda x: x.lower() in hold_navn.lower() or hold_navn.lower() in x.lower())]
        return match.iloc[0] if not match.empty else None

    wy_data = df_liga['HOLD'].apply(find_wy_stats)
    df_final = pd.concat([df_liga, pd.DataFrame(wy_data.tolist())], axis=1)

    # --- UI ---
    st.title("Tabelplacering vs. Performance")
    
    # Split-logik visning
    max_runder = df_opta[df_opta['MATCH_STATUS'].str.contains('Played|Full', case=False, na=False)]['MATCH_ROUND'].max() if 'MATCH_ROUND' in df_opta.columns else 0
    
    if max_runder <= 22:
        st.info(f"Grundspil i gang (Runde {max_runder}/22)")
    else:
        st.success("Slutspil i gang")

    tab1, tab2 = st.tabs(["Performance Plot", "Ligaoversigt"])

    with tab1:
        metric_map = {"Expected Goals (xG)": "XG", "Mål": "GOALS", "Skud": "SHOTS", "Pres (PPDA)": "PPDA", "Afleveringer": "PASSES"}
        selected_label = st.selectbox("Vælg parameter for Y-aksen", list(metric_map.keys()))
        
        # Mulighed for at filtrere på Top 6 / Bund 6 hvis man vil zoome ind
        filter_scope = st.radio("Vis for:", ["Hele Ligaen", "Top 6 (Oprykning)", "Bund 6 (Nedrykning)"], horizontal=True)
        
        plot_df = df_final.copy()
        if filter_scope == "Top 6 (Oprykning)": plot_df = plot_df.head(6)
        elif filter_scope == "Bund 6 (Nedrykning)": plot_df = plot_df.tail(6)

        draw_position_performance_chart(plot_df, metric_map[selected_label], selected_label)

    with tab2:
        # Vis den klassiske tabel
        st.dataframe(df_final[['#', 'HOLD', 'P', 'MD', 'XG', 'GOALS']], hide_index=True, use_container_width=True)

if __name__ == "__main__":
    vis_side()
