import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn

def vis_side():
    st.markdown("### Jerailly Wielzen - Spillerprofil & Admin Dashboard")
    st.markdown("Dette dashboard er låst til at vise en komplet spillerprofil, historiske percentiler samt grunddata for **Jerailly Wielzen** direkte fra Snowflake.")

    try:
        conn = _get_snowflake_conn()
    except Exception:
        st.cache_data.clear()
        conn = _get_snowflake_conn()
    
    query = """
    WITH ranked_base AS (
        SELECT 
            PLAYER_WYID,
            SEASON_WYID,
            CASE 
                WHEN COALESCE(POSITIONS1PERCENT, 0) >= GREATEST(COALESCE(POSITIONS2PERCENT,0), COALESCE(POSITIONS3PERCENT,0), COALESCE(POSITIONS4PERCENT,0)) THEN POSITION1CODE
                WHEN COALESCE(POSITIONS2PERCENT, 0) >= GREATEST(COALESCE(POSITIONS1PERCENT,0), COALESCE(POSITIONS3PERCENT,0), COALESCE(POSITIONS4PERCENT,0)) THEN POSITION2CODE
                WHEN COALESCE(POSITIONS3PERCENT, 0) >= GREATEST(COALESCE(POSITIONS1PERCENT,0), COALESCE(POSITIONS2PERCENT,0), COALESCE(POSITIONS4PERCENT,0)) THEN POSITION3CODE
                ELSE POSITION4CODE
            END AS PRIMARY_POS_CODE
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERADVANCEDSTATS_BASE
    ),
    base_stats AS (
        SELECT 
            p.SHORTNAME AS PLAYER_NAME,
            p.FIRSTNAME,
            p.LASTNAME,
            p.BIRTHDATE,
            p.HEIGHT,
            p.WEIGHT,
            p.FOOT,
            t.TEAMNAME,
            s.SEASONNAME,
            pt.COMPETITION_WYID,
            s.SEASON_WYID,
            pt.PLAYER_WYID,
            
            COALESCE(pt.MATCHES, 0) AS MATCHESPLAYED,
            pt.MINUTESONFIELD,
            COALESCE(pt.GOALS, 0) AS GOALS,
            COALESCE(pt.ASSISTS, 0) AS ASSISTS,
            COALESCE(pt.YELLOWCARDS, 0) AS YELLOWCARDS,
            COALESCE(pt.REDCARDS, 0) AS REDCARDS,
            
            COALESCE(rb.PRIMARY_POS_CODE, 'RB') AS EVAL_POSITION_CODE,
            
            CASE WHEN pt.MINUTESONFIELD > 0 THEN (pt.ASSISTS * 90.0 / pt.MINUTESONFIELD) ELSE 0 END AS ASSISTS_P90,
            CASE WHEN pt.MINUTESONFIELD > 0 THEN (pt.SUCCESSFULCROSSES * 90.0 / pt.MINUTESONFIELD) ELSE 0 END AS SUCCESSFUL_CROSSES_P90,
            CASE WHEN pt.MINUTESONFIELD > 0 THEN (pt.PROGRESSIVERUN * 90.0 / pt.MINUTESONFIELD) ELSE 0 END AS PROGRESSIVE_RUN_P90,
            CASE WHEN pt.MINUTESONFIELD > 0 THEN (pt.ACCELERATIONS * 90.0 / pt.MINUTESONFIELD) ELSE 0 END AS ACCELERATIONS_P90,
            CASE WHEN pt.MINUTESONFIELD > 0 THEN (pt.NEWOFFENSIVEDUELSWON * 90.0 / pt.MINUTESONFIELD) ELSE 0 END AS OFF_1V1_WON_P90,
            CASE WHEN pt.MINUTESONFIELD > 0 THEN (pt.NEWDEFENSIVEDUELSWON * 90.0 / pt.MINUTESONFIELD) ELSE 0 END AS DEF_1V1_WON_P90,
            CASE WHEN pt.MINUTESONFIELD > 0 THEN (pt.TOUCHINBOX * 90.0 / pt.MINUTESONFIELD) ELSE 0 END AS TOUCH_IN_BOX_P90,

            ROW_NUMBER() OVER (PARTITION BY pt.PLAYER_WYID, pt.SEASON_WYID, pt.COMPETITION_WYID ORDER BY pt.MINUTESONFIELD DESC) as rn
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL pt
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS s ON pt.SEASON_WYID = s.SEASON_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS p ON pt.PLAYER_WYID = p.PLAYER_WYID AND pt.SEASON_WYID = p.SEASON_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
        LEFT JOIN ranked_base rb ON pt.PLAYER_WYID = rb.PLAYER_WYID AND pt.SEASON_WYID = rb.SEASON_WYID
        WHERE UPPER(p.SHORTNAME) LIKE '%WIELZEN%'
    ),
    deduped_stats AS (
        SELECT * FROM base_stats WHERE rn = 1
    ),
    percentile_calc AS (
        SELECT 
            ds.*,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY ds.COMPETITION_WYID, ds.SEASON_WYID ORDER BY ds.ASSISTS_P90), 0) * 100 AS ASSISTS_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY ds.COMPETITION_WYID, ds.SEASON_WYID ORDER BY ds.SUCCESSFUL_CROSSES_P90), 0) * 100 AS CROSS_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY ds.COMPETITION_WYID, ds.SEASON_WYID ORDER BY ds.PROGRESSIVE_RUN_P90), 0) * 100 AS PROG_RUN_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY ds.COMPETITION_WYID, ds.SEASON_WYID ORDER BY ds.ACCELERATIONS_P90), 0) * 100 AS HI_RUN_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY ds.COMPETITION_WYID, ds.SEASON_WYID ORDER BY ds.OFF_1V1_WON_P90), 0) * 100 AS OFF_1V1_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY ds.COMPETITION_WYID, ds.SEASON_WYID ORDER BY ds.DEF_1V1_WON_P90), 0) * 100 AS DEF_1V1_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY ds.COMPETITION_WYID, ds.SEASON_WYID ORDER BY ds.TOUCH_IN_BOX_P90), 0) * 100 AS TOUCH_IN_BOX_PCTILE
        FROM deduped_stats ds
    )
    SELECT * FROM percentile_calc ORDER BY SEASONNAME DESC;
    """

    @st.cache_data(ttl=600)
    def load_data(q):
        try:
            current_conn = _get_snowflake_conn()
            return pd.read_sql(q, current_conn)
        except Exception:
            st.cache_data.clear()
            current_conn = _get_snowflake_conn()
            return pd.read_sql(q, current_conn)

    try:
        df = load_data(query)
    except Exception as e:
        st.error(f"Fejl ved hentning af data fra Snowflake: {e}")
        return

    if df.empty:
        st.warning("Ingen data fundet for Jerailly Wielzen.")
        return

    seasons = df["SEASONNAME"].unique().tolist()
    selected_season = st.selectbox("Vælg sæson for profil:", seasons)

    player_data = df[df["SEASONNAME"] == selected_season].iloc[0]

    st.markdown(f"### {player_data['PLAYER_NAME']} ({player_data['TEAMNAME']})")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Kampe", int(player_data["MATCHESPLAYED"]))
        st.metric("Minutter", int(player_data["MINUTESONFIELD"]))
    with col2:
        st.metric("Mål", int(player_data["GOALS"]))
        st.metric("Assists", int(player_data["ASSISTS"]))
    with col3:
        st.metric("Gule Kort", int(player_data["YELLOWCARDS"]))
        st.metric("Røde Kort", int(player_data["REDCARDS"]))
    with col4:
        st.metric("Højde / Vægt", f"{player_data.get('HEIGHT', '-')} cm / {player_data.get('WEIGHT', '-')} kg")
        st.metric("Primær Position", player_data["EVAL_POSITION_CODE"])

    st.markdown("---")

    st.markdown("#### Spillerprofil & Percentil-ranking")

    metrics = [
        "Assist",
        "Cross",
        "HI RUN",
        "Progressive run",
        "1v1 OFF",
        "1v1 DEF",
        "Touch/Pass in Box"
    ]
    
    percentiles = [
        float(player_data["ASSISTS_PCTILE"]),
        float(player_data["CROSS_PCTILE"]),
        float(player_data["HI_RUN_PCTILE"]),
        float(player_data["PROG_RUN_PCTILE"]),
        float(player_data["OFF_1V1_PCTILE"]),
        float(player_data["DEF_1V1_PCTILE"]),
        float(player_data["TOUCH_IN_BOX_PCTILE"])
    ]

    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    percentiles_plot = percentiles + percentiles[:1]
    angles_plot = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles_plot, percentiles_plot, color="#df003b", linewidth=2.5, linestyle="solid", label=f"{player_data['PLAYER_NAME']} ({selected_season})")
    ax.fill(angles_plot, percentiles_plot, color="#df003b", alpha=0.25)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles)
    ax.set_xticklabels(metrics, fontsize=10, fontweight="bold")

    ax.set_rlim(0, 100)
    ax.set_rticks([20, 40, 60, 80, 100])
    ax.set_rlabel_position(0)
    ax.tick_params(axis="y", labelsize=8)

    plt.title(f"Percentil-oversigt vs. Ligaen ({selected_season})", size=12, fontweight="bold", pad=15)
    st.pyplot(fig)

    st.markdown("#### Detaljerede målinger (Percentil & P90 værdier)")
    
    detail_df = pd.DataFrame({
        "Metrik": metrics,
        "Percentil (%)": [round(p, 1) for p in percentiles],
        "Rå P90 Værdi": [
            round(player_data["ASSISTS_P90"], 2),
            round(player_data["SUCCESSFUL_CROSSES_P90"], 2),
            round(player_data["ACCELERATIONS_P90"], 2),
            round(player_data["PROGRESSIVE_RUN_P90"], 2),
            round(player_data["OFF_1V1_WON_P90"], 2),
            round(player_data["DEF_1V1_WON_P90"], 2),
            round(player_data["TOUCH_IN_BOX_P90"], 2)
        ]
    })
    
    st.dataframe(detail_df, use_container_width=True, hide_index=True)
