import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn

def vis_side():
    st.markdown("### Holdoversigt & Team Radar Dashboard")
    st.markdown("Dette dashboard viser samlede holdpræstationer, historiske percentiler samt en kantet radargraf baseret på nøglefaktorer fra Snowflake.")

    try:
        conn = _get_snowflake_conn()
    except Exception:
        st.cache_data.clear()
        conn = _get_snowflake_conn()
    
    query = """
    WITH team_base AS (
        SELECT 
            t.TEAMNAME,
            s.SEASONNAME,
            tp.COMPETITION_WYID,
            s.SEASON_WYID,
            tp.TEAM_WYID,
            
            COALESCE(tp.GOALS, 0) AS GOALS,
            COALESCE(tp.SHOTS, 0) AS SHOTS,
            COALESCE(tp.CONCEDEDGOALS, 0) AS CONCEDEDGOALS,
            CASE WHEN COALESCE(tp.SHOTS, 0) > 0 THEN (COALESCE(tp.GOALS, 0) * 100.0 / tp.SHOTS) ELSE 0 END AS CONVERSION_RATE,
            
            COALESCE(avg_stats.POSSESSIONPERCENT, 0) AS POSSESSIONPERCENT,
            
            COALESCE(avg_stats.PASSES, 0) AS PASSES,
            COALESCE(avg_stats.SUCCESSFULPASSES, 0) AS SUCCESSFUL_PASSES,
            COALESCE(avg_stats.SUCCESSFULFORWARDPASSES, 0) AS SUCCESSFUL_FORWARD_PASSES,
            COALESCE(avg_stats.PASSLENGTH, 0) AS PASS_LENGTH,
            
            COALESCE(tp.ATTACKINGACTIONS, 0) AS ATTACKING_ACTIONS,
            COALESCE(tp.DEFENSIVEACTIONS, 0) AS DEFENSIVE_ACTIONS,

            ROW_NUMBER() OVER (PARTITION BY tp.TEAM_WYID, tp.SEASON_WYID, tp.COMPETITION_WYID ORDER BY tp.TEAM_WYID) as rn
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_TOTAL tp
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS s ON tp.SEASON_WYID = s.SEASON_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS t ON tp.TEAM_WYID = t.TEAM_WYID
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMSADVANCEDSTATS_AVERAGE avg_stats 
            ON tp.TEAM_WYID = avg_stats.TEAM_WYID 
            AND tp.SEASON_WYID = avg_stats.SEASON_WYID 
        WHERE tp.MATCHES >= 1 AND tp.COMPETITION_WYID = 328
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
            -- Omvendt percentil for Mål Imod (færrest mål = 100% / bedst)
            100 - (COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONCEDEDGOALS), 0) * 100) AS CONCEDEDGOALS_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.POSSESSIONPERCENT), 0) * 100 AS POSSESSION_PCTILE,
            
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PASSES), 0) * 100 AS P_PASSES,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFUL_PASSES), 0) * 100 AS P_SUCC_PASSES,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SUCCESSFUL_FORWARD_PASSES), 0) * 100 AS P_FWD_PASSES,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.PASS_LENGTH), 0) * 100 AS P_PASS_LENGTH,
            
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.ATTACKING_ACTIONS), 0) * 100 AS ATTACKING_PCTILE,
            COALESCE(PERCENT_RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.DEFENSIVE_ACTIONS), 0) * 100 AS DEFENSIVE_PCTILE,

            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.GOALS DESC) AS GOALS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.SHOTS DESC) AS SHOTS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONVERSION_RATE DESC) AS CONVERSION_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.CONCEDEDGOALS ASC) AS CONCEDEDGOALS_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.POSSESSIONPERCENT DESC) AS POSSESSION_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.ATTACKING_ACTIONS DESC) AS ATTACKING_RANK,
            RANK() OVER (PARTITION BY dt.COMPETITION_WYID, dt.SEASON_WYID ORDER BY dt.DEFENSIVE_ACTIONS DESC) AS DEFENSIVE_RANK
        FROM deduped_team_stats dt
    ),
    team_combined_passing AS (
        SELECT 
            tp.*,
            (P_PASSES + P_SUCC_PASSES + P_FWD_PASSES + P_PASS_LENGTH) / 4.0 AS PASSING_FACTOR_PCTILE,
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
    SELECT * FROM team_final_rank ORDER BY SEASONNAME DESC, TEAMNAME ASC;
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
        st.warning("Ingen data fundet.")
        return

    seasons = df["SEASONNAME"].unique().tolist()
    selected_season = st.selectbox("Vælg sæson:", seasons)

    season_df = df[df["SEASONNAME"] == selected_season]
    teams = season_df["TEAMNAME"].unique().tolist()
    selected_team = st.selectbox("Vælg hold:", teams)

    team_data = season_df[season_df["TEAMNAME"] == selected_team].iloc[0]

    st.markdown(f"### {selected_team} ({selected_season})")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Samlet Rank", f"#{int(team_data['TOTAL_RANK_VAL'])}")
        st.metric("Samlet Score", f"{round(team_data['TOTAL_SCORE_PCTILE'], 1)}%")
    with col2:
        st.metric("Mål", int(team_data["GOALS"]))
        st.metric("Mål Imod", int(team_data["CONCEDEDGOALS"]))
    with col3:
        st.metric("Skud", int(team_data["SHOTS"]))
        st.metric("Konv. Rate", f"{round(team_data['CONVERSION_RATE'], 1)}%")
    with col4:
        st.metric("Possession", f"{round(team_data['POSSESSIONPERCENT'], 1)}%")
        st.metric("Pasningsfaktor", f"{round(team_data['PASSING_FACTOR_AVGVAL'], 1)}")

    st.markdown("---")
    st.markdown("#### Holdets Kantede Radar Chart & Percentil-ranking")

    metrics = [
        "Mål",
        "Skud",
        "Konvertering",
        "Mål Imod",
        "Possession",
        "Pasningsfaktor",
        "Offensiv",
        "Defensiv"
    ]
    
    percentiles = [
        float(team_data["GOALS_PCTILE"]),
        float(team_data["SHOTS_PCTILE"]),
        float(team_data["CONVERSION_PCTILE"]),
        float(team_data["CONCEDEDGOALS_PCTILE"]),
        float(team_data["POSSESSION_PCTILE"]),
        float(team_data["PASSING_FACTOR_PCTILE"]),
        float(team_data["ATTACKING_PCTILE"]),
        float(team_data["DEFENSIVE_PCTILE"])
    ]

    ranks = [
        f"#{int(team_data['GOALS_RANK'])}",
        f"#{int(team_data['SHOTS_RANK'])}",
        f"#{int(team_data['CONVERSION_RANK'])}",
        f"#{int(team_data['CONCEDEDGOALS_RANK'])}",
        f"#{int(team_data['POSSESSION_RANK'])}",
        f"#{int(team_data['PASS_RANK'])}",
        f"#{int(team_data['ATTACKING_RANK'])}",
        f"#{int(team_data['DEFENSIVE_RANK'])}"
    ]

    # Labels med både kategori, værdi og rank
    labels = [f"{m}\n{p:.1f}% ({r})" for m, p, r in zip(metrics, percentiles, ranks)]

    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    percentiles_plot = percentiles + percentiles[:1]
    angles_plot = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    
    # Tegn kantet polygon med markører på knækpunkterne
    ax.plot(angles_plot, percentiles_plot, color="#df003b", linewidth=2, linestyle="solid", marker="o", markersize=5, label=f"{selected_team} ({selected_season})")
    ax.fill(angles_plot, percentiles_plot, color="#df003b", alpha=0.25)

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=8, fontweight="bold")

    ax.set_rlim(0, 100)
    ax.set_rticks([20, 40, 60, 80, 100])
    ax.set_rlabel_position(0)
    ax.tick_params(axis="y", labelsize=8)

    plt.title(f"Holdets Percentil-oversigt vs. Ligaen ({selected_season})", size=12, fontweight="bold", pad=20)
    st.pyplot(fig)

    st.markdown("#### Detaljerede målinger (Percentil & Ranks)")
    
    detail_df = pd.DataFrame({
        "Kategori": metrics,
        "Percentil (%)": [round(p, 1) for p in percentiles],
        "Rank": ranks
    })
    
    st.dataframe(detail_df, use_container_width=True, hide_index=True)
