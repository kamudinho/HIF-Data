import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import requests
from io import BytesIO
from mplsoccer import PyPizza, add_image
from data.data_load import _get_snowflake_conn

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
            
            COALESCE(tp.GOALS, 0) AS GOALS,
            COALESCE(tp.SHOTS, 0) AS SHOTS,
            COALESCE(tp.CONCEDEDGOALS, 0) AS CONCEDEDGOALS,
            CASE WHEN COALESCE(tp.SHOTS, 0) > 0 THEN (COALESCE(tp.GOALS, 0) * 100.0 / tp.SHOTS) ELSE 0 END AS CONVERSION_RATE,
            COALESCE(tp.ATTACKINGACTIONS, 0) AS ATTACKING_ACTIONS,
            COALESCE(tp.DEFENSIVEACTIONS, 0) AS DEFENSIVE_ACTIONS,
            
            COALESCE(avg_stats.POSSESSIONPERCENT, 0) AS POSSESSIONPERCENT,
            COALESCE(avg_stats.PASSES, 0) AS PASSES,
            COALESCE(avg_stats.SUCCESSFULPASSES, 0) AS SUCCESSFUL_PASSES,
            COALESCE(avg_stats.SUCCESSFULFORWARDPASSES, 0) AS SUCCESSFUL_FORWARD_PASSES,
            COALESCE(avg_stats.PASSLENGTH, 0) AS PASS_LENGTH,

            ROW_NUMBER() OVER (PARTITION BY tp.TEAM_WYID, tp.SEASON_WYID, tp.COMPETITION_WYID ORDER BY tp.TEAM_WYID) as rn
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL tp
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS s ON tp.SEASON_WYID = s.SEASON_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS t ON tp.TEAM_WYID = t.TEAM_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS_STANDINGS st 
            ON tp.TEAM_WYID = st.TEAM_WYID AND tp.SEASON_WYID = st.SEASON_WYID
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_AVERAGE avg_stats 
            ON tp.TEAM_WYID = avg_stats.TEAM_WYID 
            AND tp.SEASON_WYID = avg_stats.SEASON_WYID 
        WHERE tp.MATCHES >= 1 AND tp.COMPETITION_WYID = 328 AND s.SEASONNAME = '2026/2027'
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

            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.ATTACKING_ACTIONS), 0) * 100 AS ATTACKING_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.DEFENSIVE_ACTIONS), 0) * 100 AS DEFENSIVE_PCTILE,

            ROW_NUMBER() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.GOALS DESC) AS GOALS_RANK,
            ROW_NUMBER() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SHOTS DESC) AS SHOTS_RANK,
            ROW_NUMBER() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONVERSION_RATE DESC) AS CONVERSION_RANK,
            ROW_NUMBER() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.POSSESSIONPERCENT DESC) AS POSSESSION_RANK,
            ROW_NUMBER() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONCEDEDGOALS ASC) AS CONCEDEDGOALS_RANK,
            ROW_NUMBER() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.ATTACKING_ACTIONS DESC) AS ATTACKING_RANK,
            ROW_NUMBER() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.DEFENSIVE_ACTIONS DESC) AS DEFENSIVE_RANK
        FROM deduped_team_stats dt
    ),
    team_combined_passing AS (
        SELECT 
            tp.*,
            (PASSES_PCTILE + SUCCESSFUL_PASSES_PCTILE + SUCCESSFUL_FORWARD_PASSES_PCTILE + PASS_LENGTH_PCTILE) / 4.0 AS PASSING_FACTOR_PCTILE,
            (PASSES + SUCCESSFUL_PASSES + SUCCESSFUL_FORWARD_PASSES + PASS_LENGTH) / 4.0 AS PASSING_FACTOR_AVGVAL,
            ROW_NUMBER() OVER (PARTITION BY tp.COMPETITION_WYID, tp.SEASON_WYID ORDER BY (tp.PASSES + tp.SUCCESSFUL_PASSES + tp.SUCCESSFUL_FORWARD_PASSES + tp.PASS_LENGTH) DESC) AS PASSING_FACTOR_RANK
        FROM team_percentile_calc tp
    )
    SELECT * FROM team_combined_passing
    """
    df = pd.DataFrame(conn.query(query))
    df.columns = [c.upper() for c in df.columns]
    return df

def vis_side(*args, **kwargs):
    if "df_pizza" not in st.session_state:
        st.session_state["df_pizza"] = fetch_data()
    
    df = st.session_state["df_pizza"].copy()
    if df.empty:
        st.warning("Ingen data fundet for sæsonen.")
        return

    hold_data = df[['TEAMNAME', 'IMAGEDATAURL', 'TEAM_WYID']].drop_duplicates().sort_values('TEAMNAME')
    hold_navne = hold_data['TEAMNAME'].tolist()

    st.markdown("""
        <style>
            [data-testid="column"] { padding: 0rem !important; margin: 0rem !important; }
            [data-testid="stHorizontalBlock"] { gap: 0rem !important; }
            div.stDownloadButton > button { width: auto !important; min-width: 100px; padding: 0.2rem 1rem !important; }
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

        logo_url = target_team_raw['IMAGEDATAURL'].values[0]
        target_team = target_team_raw.iloc[0]

        base_params = [
            "Mål", "Skud", "Konvertering",
            "Possession", "Pasningsfaktor", "Offensiv Akt.",
            "Mål Imod", "Defensiv Akt."
        ]
        
        percentile_cols = [
            'GOALS_PCTILE', 'SHOTS_PCTILE', 'CONVERSION_PCTILE',
            'POSSESSION_PCTILE', 'PASSING_FACTOR_PCTILE', 'ATTACKING_PCTILE',
            'CONCEDEDGOALS_PCTILE', 'DEFENSIVE_PCTILE'
        ]

        raw_cols = [
            'GOALS', 'SHOTS', 'CONVERSION_RATE',
            'POSSESSIONPERCENT', 'PASSING_FACTOR_AVGVAL', 'ATTACKING_ACTIONS',
            'CONCEDEDGOALS', 'DEFENSIVE_ACTIONS'
        ]

        rank_cols = [
            'GOALS_RANK', 'SHOTS_RANK', 'CONVERSION_RANK',
            'POSSESSION_RANK', 'PASSING_FACTOR_RANK', 'ATTACKING_RANK',
            'CONCEDEDGOALS_RANK', 'DEFENSIVE_RANK'
        ]

        params = []
        for bp, r_col in zip(base_params, rank_cols):
            rank = int(target_team[r_col]) if r_col in target_team and not pd.isna(target_team[r_col]) else 0
            params.append(f"{bp}\nRank: {rank}")

        pizza_values = []
        for p_col in percentile_cols:
            val = float(target_team[p_col]) if p_col in target_team and not pd.isna(target_team[p_col]) else 50.0
            pizza_values.append(val)

        display_values = []
        for r_col in raw_cols:
            val = float(target_team[r_col]) if r_col in target_team and not pd.isna(target_team[r_col]) else 0.0
            if r_col == 'CONVERSION_RATE':
                display_values.append(f"{val:.1f}%")
            elif r_col in ['PASSING_FACTOR_AVGVAL', 'POSSESSIONPERCENT']:
                display_values.append(f"{val:.1f}")
            else:
                display_values.append(str(int(val)))

        slice_colors = (
            ["#D32F2F"] * 3 +  
            ["#E57373"] * 3 +  
            ["#8E0000"] * 2    
        )

        baker = PyPizza(
            params=params,
            min_range=[0]*len(params),
            max_range=[100]*len(params),
            background_color="#FFFFFF",
            straight_line_color="#222222",
            last_circle_color="#222222",
            last_circle_lw=1.5,
            other_circle_lw=0,  
            other_circle_color="#DDDDDD",
            inner_circle_size=8,
        )

        fig, ax = baker.make_pizza(
            pizza_values,
            alt_text_values=display_values,
            figsize=(10, 10),
            color_blank_space="same",
            blank_alpha=0.4,
            param_location=110,
            kwargs_slices=dict(
                facecolor=slice_colors, edgecolor="#222222",
                zorder=1, linewidth=0.8
            ),
            kwargs_params=dict(
                color="#111111", fontsize=9, zorder=5,
                va="center", fontweight="bold"
            ),
            kwargs_values=dict(
                color="#FFFFFF", fontsize=9,
                zorder=3,
                bbox=dict(
                    edgecolor="#222222", facecolor="#111111",
                    boxstyle="round,pad=0.2", lw=0.8
                )
            )
        )

        ax.set_aspect('equal')
        fig.patch.set_facecolor('#FFFFFF')

        logo_img = get_logo(logo_url)
        if logo_img:
            ax_image = add_image(
                logo_img, fig, left=0.463, bottom=0.456, width=0.085, height=0.083
            )

        st.pyplot(fig, use_container_width=True)

        buf = BytesIO()
        fig.savefig(buf, format="png", facecolor="#FFFFFF", edgecolor='none', bbox_inches=None, dpi=300)
        
        with download_placeholder:
            st.download_button(
                label="Download",
                data=buf.getvalue(),
                file_name=f"Radar_{valgt_hold_navn}.png",
                mime="image/png"
            )
