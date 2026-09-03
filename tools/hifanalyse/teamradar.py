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

# --- 1. DATA OPSÆTNING MED KORREKTE KOLONNER FRA TOTAL-TABELLEN ---
METRIC_PAIRS = {
    'OFFENSIV': [
        ('Mål', 'GOALS'), 
        ('Skud', 'SHOTS'), 
        ('Konvertering', 'CONVERSION_RATE'),
        ('Offensiv Akt.', 'ATTACKING_ACTIONS'),
        ('Berøringer i Felt', 'TOUCHINBOX'),
        ('Driblinger', 'SUCCESSFULDRIBBLES'),
        ('Indlæg', 'SUCCESSFULCROSSES'),
        ('xG pr. Skud', 'XGSHOT')
    ],
    'OPBYGNING & PASNINGER': [
        ('Possession', 'POSSESSIONPERCENT'), 
        ('Pasningsfaktor', 'PASSING_FACTOR_AVGVAL'),
        ('Alle Pasninger', 'PASSES'),
        ('Succesfulde Pas.', 'SUCCESSFUL_PASSES'),
        ('Fremadrettede Pas.', 'SUCCESSFUL_FORWARD_PASSES'),
        ('Lange Pasninger', 'SUCCESSFULLONGPASSES'),
        ('Laterale Pas.', 'SUCCESSFULLATERALPASSES'),
        ('Bagudrettede Pas.', 'SUCCESSFULBACKPASSES'),
        ('Smart Passes', 'SUCCESSFULSMARTPASSES'),
        ('Pas. til Sidste 3.', 'SUCCESSFULPASSESTOFINALTHIRD'),
        ('Progressive Løb', 'PROGRESSIVERUN'),
        ('Pasningslængde', 'PASS_LENGTH')
    ],
    'DEFENSIV': [
        ('Mål Imod', 'CONCEDEDGOALS'), 
        ('Defensiv Akt.', 'DEFENSIVE_ACTIONS'),
        ('Genvindinger (Modh.)', 'OPPONENTHALFRECOVERIES'),
        ('Succes. Def. Akt.', 'SUCCESSFULDEFENSIVEACTION'),
        ('Interceptions', 'INTERCEPTIONS')
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
            t.TEAMNAME,
            t.IMAGEDATAURL,
            s.SEASONNAME,
            tp.COMPETITION_WYID,
            s.SEASON_WYID,
            tp.TEAM_WYID,
            st.TOTALPLAYED AS MATCHES,
            
            -- Mål & Generelt (fra total-tabellen)
            COALESCE(tp.GOALS, 0) AS GOALS,
            COALESCE(tp.SHOTS, 0) AS SHOTS,
            COALESCE(tp.CONCEDEDGOALS, 0) AS CONCEDEDGOALS,
            CASE WHEN COALESCE(tp.SHOTS, 0) > 0 THEN (COALESCE(tp.GOALS, 0) * 100.0 / tp.SHOTS) ELSE 0 END AS CONVERSION_RATE,
            
            -- Possession (fra average-tabellen)
            COALESCE(avg_stats.POSSESSIONPERCENT, 0) AS POSSESSIONPERCENT,
            
            -- Pasningskategorier & Detaljer (fra total-tabellen)
            COALESCE(tp.PASSES, 0) AS PASSES,
            COALESCE(tp.SUCCESSFULPASSES, 0) AS SUCCESSFUL_PASSES,
            COALESCE(tp.SUCCESSFULFORWARDPASSES, 0) AS SUCCESSFUL_FORWARD_PASSES,
            COALESCE(tp.PASSLENGTH, 0) AS PASS_LENGTH,
            COALESCE(tp.SUCCESSFULLONGPASSES, 0) AS SUCCESSFULLONGPASSES,
            COALESCE(tp.SUCCESSFULLATERALPASSES, 0) AS SUCCESSFULLATERALPASSES,
            COALESCE(tp.SUCCESSFULBACKPASSES, 0) AS SUCCESSFULBACKPASSES,
            COALESCE(tp.SUCCESSFULSMARTPASSES, 0) AS SUCCESSFULSMARTPASSES,
            
            COALESCE(tp.PROGRESSIVERUN, 0) AS PROGRESSIVERUN,
            COALESCE(tp.SUCCESSFULPASSESTOFINALTHIRD, 0) AS SUCCESSFULPASSESTOFINALTHIRD,
            COALESCE(tp.SUCCESSFULDRIBBLES, 0) AS SUCCESSFULDRIBBLES,
            COALESCE(tp.TOUCHINBOX, 0) AS TOUCHINBOX,
            COALESCE(tp.SUCCESSFULCROSSES, 0) AS SUCCESSFULCROSSES,
            COALESCE(tp.XGSHOT, 0) AS XGSHOT,
            COALESCE(tp.OPPONENTHALFRECOVERIES, 0) AS OPPONENTHALFRECOVERIES,
            COALESCE(tp.SUCCESSFULDEFENSIVEACTION, 0) AS SUCCESSFULDEFENSIVEACTION,
            COALESCE(tp.INTERCEPTIONS, 0) AS INTERCEPTIONS,
            
            COALESCE(tp.ATTACKINGACTIONS, 0) AS ATTACKING_ACTIONS,
            COALESCE(tp.DEFENSIVEACTIONS, 0) AS DEFENSIVE_ACTIONS,

            ROW_NUMBER() OVER (PARTITION BY tp.TEAM_WYID, tp.SEASON_WYID, tp.COMPETITION_WYID ORDER BY tp.TEAM_WYID) as rn
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL tp
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS s ON tp.SEASON_WYID = s.SEASON_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS t ON tp.TEAM_WYID = t.TEAM_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS_STANDINGS st 
            ON tp.TEAM_WYID = st.TEAM_WYID AND tp.SEASON_WYID = st.SEASON_WYID
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_AVERAGE avg_stats 
            ON tp.TEAM_WYID = avg_stats.TEAM_WYID 
            AND tp.SEASON_WYID = avg_stats.SEASON_WYID 
        WHERE tp.MATCHES >= 1 AND tp.COMPETITION_WYID = 328 AND s.SEASONNAME = '2025/2026'
    ),
    deduped_team_stats AS (
        SELECT * FROM team_base WHERE rn = 1
    ),
    team_percentile_calc AS (
        SELECT 
            dt.*,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.GOALS), 0) * 100 AS GOALS_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SHOTS), 0) * 100 AS SHOTS_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONVERSION_RATE), 0) * 100 AS CONVERSION_PCTILE,
            100 - (COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONCEDEDGOALS), 0) * 100) AS CONCEDEDGOALS_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.POSSESSIONPERCENT), 0) * 100 AS POSSESSION_PCTILE,
            
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PASSES), 0) * 100 AS PASSES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFUL_PASSES), 0) * 100 AS SUCCESSFUL_PASSES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFUL_FORWARD_PASSES), 0) * 100 AS SUCCESSFUL_FORWARD_PASSES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PASS_LENGTH), 0) * 100 AS PASS_LENGTH_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULLONGPASSES), 0) * 100 AS SUCCESSFULLONGPASSES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULLATERALPASSES), 0) * 100 AS SUCCESSFULLATERALPASSES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULBACKPASSES), 0) * 100 AS SUCCESSFULBACKPASSES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULSMARTPASSES), 0) * 100 AS SUCCESSFULSMARTPASSES_PCTILE,

            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PROGRESSIVERUN), 0) * 100 AS PROGRESSIVERUN_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULPASSESTOFINALTHIRD), 0) * 100 AS SUCCESSFULPASSESTOFINALTHIRD_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULDRIBBLES), 0) * 100 AS SUCCESSFULDRIBBLES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.TOUCHINBOX), 0) * 100 AS TOUCHINBOX_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULCROSSES), 0) * 100 AS SUCCESSFULCROSSES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.XGSHOT), 0) * 100 AS XGSHOT_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.OPPONENTHALFRECOVERIES), 0) * 100 AS OPPONENTHALFRECOVERIES_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULDEFENSIVEACTION), 0) * 100 AS SUCCESSFULDEFENSIVEACTION_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.INTERCEPTIONS), 0) * 100 AS INTERCEPTIONS_PCTILE,
            
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.ATTACKING_ACTIONS), 0) * 100 AS ATTACKING_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.DEFENSIVE_ACTIONS), 0) * 100 AS DEFENSIVE_PCTILE,

            -- Ranks
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.GOALS DESC) AS GOALS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SHOTS DESC) AS SHOTS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONVERSION_RATE DESC) AS CONVERSION_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONCEDEDGOALS ASC) AS CONCEDEDGOALS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.POSSESSIONPERCENT DESC) AS POSSESSION_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PASSES DESC) AS PASSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFUL_PASSES DESC) AS SUCCESSFUL_PASSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFUL_FORWARD_PASSES DESC) AS SUCCESSFUL_FORWARD_PASSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PASS_LENGTH DESC) AS PASS_LENGTH_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULLONGPASSES DESC) AS SUCCESSFULLONGPASSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULLATERALPASSES DESC) AS SUCCESSFULLATERALPASSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULBACKPASSES DESC) AS SUCCESSFULBACKPASSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULSMARTPASSES DESC) AS SUCCESSFULSMARTPASSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PROGRESSIVERUN DESC) AS PROGRESSIVERUN_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULPASSESTOFINALTHIRD DESC) AS SUCCESSFULPASSESTOFINALTHIRD_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULDRIBBLES DESC) AS SUCCESSFULDRIBBLES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.TOUCHINBOX DESC) AS TOUCHINBOX_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULCROSSES DESC) AS SUCCESSFULCROSSES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.XGSHOT DESC) AS XGSHOT_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.OPPONENTHALFRECOVERIES DESC) AS OPPONENTHALFRECOVERIES_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFULDEFENSIVEACTION DESC) AS SUCCESSFULDEFENSIVEACTION_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.INTERCEPTIONS DESC) AS INTERCEPTIONS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.ATTACKING_ACTIONS DESC) AS ATTACKING_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.DEFENSIVE_ACTIONS DESC) AS DEFENSIVE_RANK
        FROM deduped_team_stats dt
    ),
    team_combined_passing AS (
        SELECT 
            tp.*,
            (PASSES_PCTILE + SUCCESSFUL_PASSES_PCTILE + SUCCESSFUL_FORWARD_PASSES_PCTILE + PASS_LENGTH_PCTILE) / 4.0 AS PASSING_FACTOR_PCTILE,
            (PASSES + SUCCESSFUL_PASSES + SUCCESSFUL_FORWARD_PASSES + PASS_LENGTH) / 4.0 AS PASSING_FACTOR_AVGVAL
        FROM team_percentile_calc tp
    ),
    team_passing_rank AS (
        SELECT 
            cp.*,
            RANK() OVER (PARTITION BY cp.COMPETITION_WYID, cp.SEASON_WYID ORDER BY cp.PASSING_FACTOR_PCTILE DESC) AS PASS_RANK
        FROM team_combined_passing cp
    ),
    team_overall_score AS (
        SELECT 
            pr.*,
            (GOALS_PCTILE + SHOTS_PCTILE + CONVERSION_PCTILE + CONCEDEDGOALS_PCTILE + POSSESSION_PCTILE + PASSING_FACTOR_PCTILE + ATTACKING_PCTILE + DEFENSIVE_PCTILE) / 8.0 AS TOTAL_SCORE_PCTILE
        FROM team_passing_rank pr
    ),
    team_final_rank AS (
        SELECT 
            os.*,
            RANK() OVER (PARTITION BY os.COMPETITION_WYID, os.SEASON_WYID ORDER BY os.TOTAL_SCORE_PCTILE DESC) AS TOTAL_RANK_VAL
        FROM team_overall_score os
    )
    SELECT * FROM team_final_rank
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
        target_team_raw = df[df['TEAMNAME'] == valgt_hold_navn]
        if target_team_raw.empty:
            st.warning("Kunne ikke finde data for det valgte hold.")
            return

        team_id = target_team_raw['TEAM_WYID'].values[0]
        logo_url = target_team_raw['IMAGEDATAURL'].values[0]
        target_team = df[df['TEAM_WYID'] == team_id].iloc[0]

        # --- PIZZA CHART (STØRRE HJUL TIL FLERE METRIKKER) ---
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
        fig.patch.set_alpha(0)
        
        plt.subplots_adjust(left=-0.1, right=0.9, top=0.95, bottom=0.05)
        
        V_OFFSET = 25
        LIMIT_Y = 160 
        ax.set_ylim(0, LIMIT_Y)
        
        color_map = {'OFFENSIV': '#2ecc71', 'OPBYGNING & PASNINGER': '#f1c40f', 'DEFENSIV': '#e74c3c'}
        plot_labels, values, display_values, plot_colors = [], [], [], []

        for group_name, pairs in METRIC_PAIRS.items():
            for display_label, data_col in pairs:
                if data_col == 'PASSING_FACTOR_AVGVAL':
                    pctile_col, rank_col = 'PASSING_FACTOR_PCTILE', 'PASS_RANK'
                else:
                    pctile_col = f"{data_col}_PCTILE"
                    rank_col = f"{data_col}_RANK"
                
                p_val = float(target_team[pctile_col]) if pctile_col in target_team and not pd.isna(target_team[pctile_col]) else 50.0
                r_val = int(target_team[rank_col]) if rank_col in target_team and not pd.isna(target_team[rank_col]) else 1
                
                plot_labels.append(display_label)
                scaled_val = V_OFFSET + (p_val * (100 - V_OFFSET) / 100)
                values.append(scaled_val)
                
                raw_val = target_team[data_col] if data_col in target_team and not pd.isna(target_team[data_col]) else 0
                if data_col in ['CONVERSION_RATE', 'POSSESSIONPERCENT', 'PASS_LENGTH', 'PASSING_FACTOR_AVGVAL', 'XGSHOT']:
                    disp_str = f"{raw_val:.1f} (#{r_val})"
                else:
                    disp_str = f"{int(raw_val)} (#{r_val})"
                    
                display_values.append(disp_str)
                plot_colors.append(color_map[group_name])

        num_vars = len(plot_labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)
        width = (2 * np.pi) / num_vars

        ax.bar(angles, [100] * num_vars, width=width, color='none', edgecolor='white', linewidth=0.6, alpha=0.2, zorder=1)
        ax.bar(angles, values, width=width, bottom=0, color=plot_colors, alpha=0.9, edgecolor='white', linewidth=1.2, zorder=3)

        logo_img = get_logo(logo_url)
        if logo_img:
            ax.add_artist(AnnotationBbox(OffsetImage(logo_img, zoom=0.55), (0, 0), frameon=False, zorder=10))

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.axis('off')

        for angle, label, disp, color in zip(angles, plot_labels, display_values, plot_colors):
            ax.text(angle, 112, disp, ha='center', va='center', 
                    fontsize=7, fontweight='bold', color='white', zorder=12,
                    bbox=dict(facecolor=color, edgecolor='white', boxstyle='round,pad=0.25', linewidth=0.8))
            
            ax.text(angle, 146, label, ha='center', va='center',
                    fontsize=5.5, fontweight='bold', color='black', zorder=11,
                    bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.35', linewidth=0.6))

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
