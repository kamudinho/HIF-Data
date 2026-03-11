import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- KONSTANTER FRA DIT DASHBOARD ---
HIF_ROD = "#df003b"
HIF_GULD = "#b8860b"

def get_text_color(hex_color):
    if not hex_color: return "white"
    hex_color = str(hex_color).lstrip('#')
    if len(hex_color) != 6: return "white"
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (r * 0.299 + g * 0.587 + b * 0.114)
    return "black" if luminance > 165 else "white"

def draw_h2h_chart_wyscout(n1, n2, metrics, labels, dp):
    """Bruger player_stats_total aggregeret på holdniveau fra din SQL"""
    # Vi skal bruge de avancerede stats og koble dem til holdnavne
    df_stats = dp.get("wyscout", {}).get("player_stats_total", pd.DataFrame())
    df_players = dp.get("wyscout", {}).get("wyscout_players", pd.DataFrame())
    
    if df_stats.empty or df_players.empty:
        st.warning("Wyscout performance data ikke tilgængelig.")
        return

    # 1. Join stats med holdnavne
    df_combined = pd.merge(df_stats, df_players[['PLAYER_WYID', 'TEAMNAME']], on='PLAYER_WYID')
    
    # 2. Aggregér til hold-totaler
    team_totals = df_combined.groupby('TEAMNAME')[metrics].sum().reset_index()
    
    # 3. Find data for de to valgte hold
    t1_data = team_totals[team_totals['TEAMNAME'] == n1]
    t2_data = team_totals[team_totals['TEAMNAME'] == n2]

    if t1_data.empty or t2_data.empty:
        st.info("Ingen sammenlignelige stats fundet for disse hold.")
        return

    y1 = t1_data.iloc[0][metrics].tolist()
    y2 = t2_data.iloc[0][metrics].tolist()

    # 4. Plotly Setup
    fig = go.Figure()
    c1 = TEAM_COLORS.get(n1, {"primary": HIF_ROD})
    c2 = TEAM_COLORS.get(n2, {"primary": "#0056a3"})

    fig.add_trace(go.Bar(name=n1, x=labels, y=y1, marker_color=c1["primary"], 
                         text=[f"{v:.1f}" for v in y1], textposition='auto'))
    fig.add_trace(go.Bar(name=n2, x=labels, y=y2, marker_color=c2["primary"], 
                         text=[f"{v:.1f}" for v in y2], textposition='auto'))

    fig.update_layout(barmode='group', height=350, margin=dict(t=20, b=20, l=10, r=10),
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    st.plotly_chart(fig, use_container_width=True)

def vis_side(dp):
    # --- DATA SETUP ---
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame())
    logo_map = dp.get("logo_map", {})
    
    if df_matches.empty:
        st.error("Ingen Opta kampdata fundet.")
        return

    # --- 1. LIGATABEL BEREGNING (OPTA) ---
    stats = {}
    for _, row in df_matches.iterrows():
        if row['MATCH_STATUS'] != 'Played': continue
        
        h_id, a_id = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        h_g, a_g = int(row['TOTAL_HOME_SCORE']), int(row['TOTAL_AWAY_SCORE'])
        
        for uid, name in [(h_id, h_name), (a_id, a_name)]:
            if uid not in stats:
                stats[uid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'MD': 0, 'P': 0, 'UUID': uid}
        
        stats[h_id]['K'] += 1; stats[a_id]['K'] += 1
        stats[h_id]['MD'] += (h_g - a_g); stats[a_id]['MD'] += (a_g - h_g)
        
        if h_g > a_g: stats[h_id]['V'] += 1; stats[h_id]['P'] += 3; stats[a_id]['T'] += 1
        elif h_g < a_g: stats[a_id]['V'] += 1; stats[a_id]['P'] += 3; stats[h_id]['T'] += 1
        else: stats[h_id]['U'] += 1; stats[h_id]['P'] += 1; stats[a_id]['U'] += 1; stats[a_id]['P'] += 1

    df_liga = pd.DataFrame(stats.values()).sort_values(['P', 'MD'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- 2. RENDER TABS ---
    t_table, t_h2h = st.tabs(["🏆 LIGATABEL", "⚔️ HEAD-TO-HEAD"])

    with t_table:
        # Styling af tabel
        st.markdown("""<style> .tab-style { font-size: 14px; text-align: center; } </style>""", unsafe_allow_html=True)
        # Visning af tabel (Forenklet her, du kan tilføje logoer som før)
        st.dataframe(df_liga[['#', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P']], use_container_width=True, hide_index=True)

    with t_h2h:
        c1, c2 = st.columns(2)
        h_list = sorted(df_liga['HOLD'].tolist())
        t1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        t2 = c2.selectbox("Hold 2", [h for h in h_list if h != t1])

        st.markdown("---")
        # Her kalder vi Wyscout data baseret på dine SQL kolonnenavne
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("ANGREB (Total)")
            draw_h2h_chart_wyscout(t1, t2, ['XGSHOT', 'TOUCHINBOX'], ['Expected Goals', 'Felt-berør.'], dp)
        with col_b:
            st.caption("SPILOPBYGNING (Total)")
            draw_h2h_chart_wyscout(t1, t2, ['PROGRESSIVERUN', 'SUCCESSFULDRIBBLES'], ['Prog. løb', 'Driblinger OK'], dp)
