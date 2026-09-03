import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import requests
from io import BytesIO
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from mplsoccer import PyPizza
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
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.DEFENSIVE_ACTIONS), 0) * 100 AS DEFENSIVE_PCTILE
        FROM deduped_team_stats dt
    ),
    team_combined_passing AS (
        SELECT 
            tp.*,
            (PASSES_PCTILE + SUCCESSFUL_PASSES_PCTILE + SUCCESSFUL_FORWARD_PASSES_PCTILE + PASS_LENGTH_PCTILE) / 4.0 AS PASSING_FACTOR_PCTILE,
            (PASSES + SUCCESSFUL_PASSES + SUCCESSFUL_FORWARD_PASSES + PASS_LENGTH) / 4.0 AS PASSING_FACTOR_AVGVAL
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

        params = [
            "Mål", "Skud", "Konvertering", "Offensiv Akt.",
            "Possession", "Pasningsfaktor",
            "Mål Imod", "Defensiv Akt."
        ]
        
        raw_cols = [
            'GOALS', 'SHOTS', 'CONVERSION_RATE', 'ATTACKING_ACTIONS',
            'POSSESSIONPERCENT', 'PASSING_FACTOR_AVGVAL',
            'CONCEDEDGOALS', 'DEFENSIVE_ACTIONS'
        ]

        values = []
        for r_col in raw_cols:
            val = float(target_team[r_col]) if r_col in target_team and not pd.isna(target_team[r_col]) else 0.0
            values.append(val)

        min_range = []
        max_range = []
        for r_col in raw_cols:
            col_min = float(df[r_col].min())
            col_max = float(df[r_col].max())
            if col_min == col_max:
                col_min = 0.0
                col_max = max(col_max, 1.0)
            
            min_range.append(col_min * 0.9 if col_min > 0 else 0)
            max_range.append(col_max * 1.1 if col_max > 0 else 10.0)

        baker = PyPizza(
            params=params,
            min_range=min_range,
            max_range=max_range,
            background_color="#FFFFFF",
            straight_line_color="#111111",
            last_circle_color="#111111",
            last_circle_lw=1.5,
            other_circle_lw=0.8,
            other_circle_color="#E0E0E0",
            inner_circle_size=18,
        )

        fig, ax = baker.make_pizza(
            values,
            figsize=(9, 9),
            color_blank_space="same",
            blank_alpha=0.2,
            param_location=110,
            kwargs_slices=dict(
                facecolor="#DA291C", edgecolor="#111111",
                zorder=1, linewidth=0.8
            ),
            kwargs_params=dict(
                color="#111111", fontsize=10, zorder=5,
                va="center", fontweight="bold"
            ),
            kwargs_values=dict(
                color="#111111", fontsize=9,
                zorder=3,
                bbox=dict(
                    edgecolor="#111111", facecolor="#FFFFFF",
                    boxstyle="round,pad=0.2", lw=0.6
                )
            )
        )

        # Formater værdierne sikkert ved at matche tekstobjekterne i midten
        val_idx = 0
        for txt in ax.texts:
            pos = txt.get_position()
            # Værdierne i PyPizza placeres tæt på kilerne (typisk radius < 100)
            if pos[1] < 100 and val_idx < len(values):
                val = values[val_idx]
                if raw_cols[val_idx] in ['CONVERSION_RATE', 'POSSESSIONPERCENT', 'PASSING_FACTOR_AVGVAL']:
                    txt.set_text(f"{val:.1f}")
                else:
                    txt.set_text(str(int(val)))
                val_idx += 1

        # Indsæt holdets logo i midten
        logo_img = get_logo(logo_url)
        if logo_img:
            ax.add_artist(AnnotationBbox(OffsetImage(logo_img, zoom=0.30), (0, 0), frameon=True, 
                                          bboxprops=dict(facecolor='white', edgecolor='#111111', linewidth=1.2, boxstyle='circle'), 
                                          zorder=10))

        st.pyplot(fig, use_container_width=True)

        buf = BytesIO()
        fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight', pad_inches=0.1, dpi=300)
        
        with download_placeholder:
            st.download_button(
                label="Download",
                data=buf.getvalue(),
                file_name=f"Radar_{valgt_hold_navn}.png",
                mime="image/png"
            )
