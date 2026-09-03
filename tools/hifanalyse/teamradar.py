import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from PIL import Image
import requests
from io import BytesIO
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from data.data_load import _get_snowflake_conn

# --- 1. DATA OPSÆTNING ---
METRIC_PAIRS = {
    'OFFENSIV': [
        ('GOALS', 'GOALS'), ('SHOTS', 'SHOTS'), ('DRIBBLES', 'SUCCESSFULDRIBBLES'),
        ('ATTACKING ACTIONS', 'SUCCESSFULATTACKINGACTIONS'), ('TOUCH IN BOX', 'TOUCHINBOX'),
        ('CROSSES', 'SUCCESSFULCROSSES'), ('XGSHOT', 'XGSHOT')
    ],
    'OPBYGNING': [
        ('FORWARD PASSES', 'SUCCESSFULFORWARDPASSES'),
        ('PROGRESSIVE RUN', 'PROGRESSIVERUN'), ('PASSES', 'SUCCESSFULPASSES'),
        ('PASSES TO FINAL THIRD', 'SUCCESSFULPASSESTOFINALTHIRD')
    ],
    'DEFENSIV': [
        ('DEFENSIVEDUELS', 'DEFENSIVEDUELSWON'), ('AERIALDUELS', 'AERIALDUELSWON'),
        ('PPDA', 'PPDA'), ('INTERCEPTIONS', 'INTERCEPTIONS'),
        ('CONCEDEDGOALS', 'CONCEDEDGOALS'), ('RECOVERIES', 'RECOVERIES')
    ]
}

def get_logo(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except:
        return None

def fetch_data():
    conn = _get_snowflake_conn()
    query = """
    WITH team_base AS (
        SELECT 
            tm.TEAMNAME,
            tm.IMAGEDATAURL,
            s.SEASONNAME,
            t.COMPETITION_WYID,
            s.SEASON_WYID,
            t.TEAM_WYID,
            st.TOTALPLAYED AS MATCHES,
            
            COALESCE(t.GOALS, 0) AS GOALS,
            COALESCE(t.SHOTS, 0) AS SHOTS,
            COALESCE(t.SUCCESSFULDRIBBLES, 0) AS SUCCESSFULDRIBBLES,
            COALESCE(t.SUCCESSFULATTACKINGACTIONS, 0) AS SUCCESSFULATTACKINGACTIONS,
            COALESCE(t.TOUCHINBOX, 0) AS TOUCHINBOX,
            COALESCE(t.SUCCESSFULCROSSES, 0) AS SUCCESSFULCROSSES,
            COALESCE(t.XGSHOT, 0) AS XGSHOT,
            
            COALESCE(t.SUCCESSFULFORWARDPASSES, 0) AS SUCCESSFULFORWARDPASSES,
            COALESCE(t.PROGRESSIVERUN, 0) AS PROGRESSIVERUN,
            COALESCE(t.SUCCESSFULPASSES, 0) AS SUCCESSFULPASSES,
            COALESCE(t.SUCCESSFULPASSESTOFINALTHIRD, 0) AS SUCCESSFULPASSESTOFINALTHIRD,
            
            COALESCE(t.DEFENSIVEDUELSWON, 0) AS DEFENSIVEDUELSWON,
            COALESCE(t.AERIALDUELSWON, 0) AS AERIALDUELSWON,
            COALESCE(t.PPDA, 0) AS PPDA,
            COALESCE(t.INTERCEPTIONS, 0) AS INTERCEPTIONS,
            COALESCE(t.CONCEDEDGOALS, 0) AS CONCEDEDGOALS,
            COALESCE(t.RECOVERIES, 0) AS RECOVERIES,

            ROW_NUMBER() OVER (PARTITION BY t.TEAM_WYID, t.SEASON_WYID, t.COMPETITION_WYID ORDER BY t.TEAM_WYID) as rn
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL AS t
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS AS s ON t.SEASON_WYID = s.SEASON_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS AS tm ON t.TEAM_WYID = tm.TEAM_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS_STANDINGS AS st 
            ON t.TEAM_WYID = st.TEAM_WYID AND t.SEASON_WYID = st.SEASON_WYID
        WHERE t.COMPETITION_WYID = 328
        AND s.SEASONNAME = '2025/2026'
    ),
    deduped_team_stats AS (
        SELECT * FROM team_base WHERE rn = 1
    ),
    team_percentile_calc AS (
        SELECT 
            dt.*,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.GOALS), 0) * 100 AS GOALS_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SHOTS), 0) * 100 AS SHOTS_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULDRIBBLES), 0) * 100 AS SUCCESSFULDRIBBLES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULATTACKINGACTIONS), 0) * 100 AS SUCCESSFULATTACKINGACTIONS_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.TOUCHINBOX), 0) * 100 AS TOUCHINBOX_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULCROSSES), 0) * 100 AS SUCCESSFULCROSSES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.XGSHOT), 0) * 100 AS XGSHOT_PCTILE,
            
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULFORWARDPASSES), 0) * 100 AS SUCCESSFULFORWARDPASSES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PROGRESSIVERUN), 0) * 100 AS PROGRESSIVERUN_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULPASSES), 0) * 100 AS SUCCESSFULPASSES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULPASSESTOFINALTHIRD), 0) * 100 AS SUCCESSFULPASSESTOFINALTHIRD_PCTILE,
            
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.DEFENSIVEDUELSWON), 0) * 100 AS DEFENSIVEDUELSWON_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.AERIALDUELSWON), 0) * 100 AS AERIALDUELSWON_PCTILE,
            100 - (COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PPDA), 0) * 100) AS PPDA_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.INTERCEPTIONS), 0) * 100 AS INTERCEPTIONS_PCTILE,
            100 - (COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONCEDEDGOALS), 0) * 100) AS CONCEDEDGOALS_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.RECOVERIES), 0) * 100 AS RECOVERIES_PCTILE,

            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.GOALS DESC) AS GOALS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SHOTS DESC) AS SHOTS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULDRIBBLES DESC) AS SUCCESSFULDRIBBLES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULATTACKINGACTIONS DESC) AS SUCCESSFULATTACKINGACTIONS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.TOUCHINBOX DESC) AS TOUCHINBOX_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULCROSSES DESC) AS SUCCESSFULCROSSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.XGSHOT DESC) AS XGSHOT_RANK,
            
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULFORWARDPASSES DESC) AS SUCCESSFULFORWARDPASSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PROGRESSIVERUN DESC) AS PROGRESSIVERUN_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULPASSES DESC) AS SUCCESSFULPASSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULPASSESTOFINALTHIRD DESC) AS SUCCESSFULPASSESTOFINALTHIRD_RANK,
            
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.DEFENSIVEDUELSWON DESC) AS DEFENSIVEDUELSWON_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.AERIALDUELSWON DESC) AS AERIALDUELSWON_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PPDA ASC) AS PPDA_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.INTERCEPTIONS DESC) AS INTERCEPTIONS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONCEDEDGOALS ASC) AS CONCEDEDGOALS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.RECOVERIES DESC) AS RECOVERIES_RANK
        FROM deduped_team_stats dt
    )
    SELECT * FROM team_percentile_calc
    """
    df = pd.DataFrame(conn.query(query))
    df.columns = [c.upper() for c in df.columns]
    return df

def vis_side(*args, **kwargs):
    if "df_pizza" not in st.session_state:
        st.session_state["df_pizza"] = fetch_data()
    
    df = st.session_state["df_pizza"].copy()
    hold_data = df[['TEAMNAME', 'IMAGEDATAURL', 'TEAM_WYID']].drop_duplicates().sort_values('TEAMNAME')
    hold_navne = hold_data['TEAMNAME'].tolist()

    # --- CSS: TVING INDHOLDET SAMMEN ---
    st.markdown("""
        <style>
            [data-testid="column"] {
                padding: 0rem !important;
                margin: 0rem !important;
            }
            [data-testid="stHorizontalBlock"] {
                gap: 0rem !important;
            }
            div.stDownloadButton > button {
                width: auto !important;
                min-width: 100px;
                padding: 0.2rem 1rem !important;
            }
        </style>
    """, unsafe_allow_html=True)

    menu_col, chart_col = st.columns([1, 5])

    with menu_col:
        st.caption("Vælg Hold")
        valgt_hold_navn = st.radio("Hold", hold_navne, label_visibility="collapsed", key="team_radio_select")
        st.write("") 
        download_placeholder = st.empty()

    with chart_col:
        # --- FEJLFINDING: VIS KOLONNERNE DIREKTE PÅ SKÆRMEN ---
        st.write("Faktiske kolonner i DataFrame:", list(df.columns))

        target_team_raw = df[df['TEAMNAME'] == valgt_hold_navn]
        if target_team_raw.empty:
            st.warning("Kunne ikke finde data for det valgte hold.")
            return

        team_id = target_team_raw['TEAM_WYID'].values[0]
        logo_url = target_team_raw['IMAGEDATAURL'].values[0]

        all_metrics_cols = [pair[1] for group in METRIC_PAIRS.values() for pair in group]
        for col in list(set(all_metrics_cols)):
            if col in df.columns and col != 'PPDA':
                df[col] = pd.to_numeric(df[col], errors='coerce') / df['MATCHES']
        
        target_team = df[df['TEAM_WYID'] == team_id].iloc[0]

        # --- PIZZA CHART POSITIONERING ---
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
        fig.patch.set_alpha(0)
        
        plt.subplots_adjust(left=-0.1, right=0.9, top=0.95, bottom=0.05)
        
        V_OFFSET = 25
        LIMIT_Y = 160 
        ax.set_ylim(0, LIMIT_Y)
        
        color_map = {'OFFENSIV': '#2ecc71', 'OPBYGNING': '#f1c40f', 'DEFENSIV': '#e74c3c'}
        plot_labels, values, display_values, plot_colors = [], [], [], []

        for group_name, pairs in METRIC_PAIRS.items():
            for display_label, data_col in pairs:
                if data_col not in df.columns: 
                    continue
                
                pctile_col = f"{data_col}_PCTILE"
                rank_col = f"{data_col}_RANK"
                
                p_val = float(target_team[pctile_col]) if pctile_col in target_team else 50.0
                r_val = int(target_team[rank_col]) if rank_col in target_team else 1
                
                plot_labels.append(display_label)
                scaled_val = V_OFFSET + (p_val * (100 - V_OFFSET) / 100)
                values.append(scaled_val)
                
                raw_val = target_team[data_col]
                if data_col == 'XGSHOT':
                    disp_str = f"{raw_val:.2f} (#{r_val})"
                else:
                    disp_str = f"{raw_val:.1f} (#{r_val})"
                    
                display_values.append(disp_str)
                plot_colors.append(color_map[group_name])

        num_vars = len(plot_labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)
        width = (2 * np.pi) / num_vars

        ax.bar(angles, [100] * num_vars, width=width, color='none', edgecolor='white', linewidth=0.6, alpha=0.2, zorder=1)
        ax.bar(angles, values, width=width, bottom=0, color=plot_colors, alpha=0.9, edgecolor='white', linewidth=1.2, zorder=3)

        logo_img = get_logo(logo_url)
        if logo_img:
            ax.add_artist(AnnotationBbox(OffsetImage(logo_img, zoom=0.6), (0, 0), frameon=False, zorder=10))

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.axis('off')

        for angle, label, disp, color in zip(angles, plot_labels, display_values, plot_colors):
            ax.text(angle, 112, disp, ha='center', va='center', 
                    fontsize=9, fontweight='bold', color='white', zorder=12,
                    bbox=dict(facecolor=color, edgecolor='white', boxstyle='round,pad=0.3', linewidth=1))
            
            ax.text(angle, 145, label, ha='center', va='center',
                    fontsize=7, fontweight='bold', color='black', zorder=11,
                    bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.4', linewidth=0.8))

        st.pyplot(fig, use_container_width=True)

        buf = BytesIO()
        fig.savefig(buf, format="png", transparent=True, bbox_inches='tight', pad_inches=0.1, dpi=300)
        
        with download_placeholder:
            st.download_button(
                label="Download",
                data=buf.getvalue(),
                file_name=f"Pizzachart_{valgt_hold_navn}.png",
                mime="image/png"
            )
