# tools/players/percentile_charts.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from data.sql.percentile_players import fetch_player_percentiles

def vis_side():
    """
    Hovedfunktion der kaldes af appen uden argumenter.
    Henter data via fetch_player_percentiles().
    """
    st.title("Spillerprofiler & Percentiler")
    st.markdown("Her kan du se rangeringer, top 10-spillere og generere visuelle spillerprofiler i Opta/FBref-stil.")

    # Hent data
    try:
        df = fetch_player_percentiles()
    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
        return

    if df.empty:
        st.warning("Ingen data fundet med de aktuelle filtre.")
        return

    # Opret tabs til navigation
    tab_overview, tab_profile = st.tabs(["🏆 Oversigt & Top 10", "📊 Generér Spillerprofil"])

    with tab_overview:
        st.subheader("Top 10 Spillere per Kategori")
        
        metric_cols = [col for col in df.columns if col not in ['HOLD_NAVN', 'SPILLER_NAVN', 'MINUTTER', 'KAMPE']]
        selected_metric = st.selectbox("Vælg metrik / kategori for Top 10:", metric_cols)

        if selected_metric:
            top_10 = df[['SPILLER_NAVN', 'HOLD_NAVN', 'MINUTTER', selected_metric]].sort_values(by=selected_metric, ascending=False).head(10)
            st.dataframe(top_10.reset_index(drop=True), use_container_width=True)

        st.markdown("---")
        st.subheader("Komplet Datatabel")
        st.dataframe(df, use_container_width=True)

    with tab_profile:
        st.subheader("Visuel Spillerprofil Generator (Opta-stil)")
        
        teams = sorted(df['HOLD_NAVN'].unique())
        selected_team = st.selectbox("Vælg hold:", teams, key="profile_team")
        
        team_players = sorted(df[df['HOLD_NAVN'] == selected_team]['SPILLER_NAVN'].unique())
        selected_player = st.selectbox("Vælg spiller:", team_players, key="profile_player")

        if selected_player:
            player_row = df[df['SPILLER_NAVN'] == selected_player].iloc[0]

            # Opsætning af data til grafen
            metrics_config = [
                ("Non-Penalty Goals", "NP_GOALS_P90", "NP_GOALS_PCTILE"),
                ("npxG", "NP_XG_P90", "NP_XG_PCTILE"),
                ("Shots Total", "SHOTS_P90", "SHOTS_PCTILE"),
                ("Assists", "ASSISTS_P90", "ASSISTS_PCTILE"),
                ("xA", "XA_P90", "XA_PCTILE"),
                ("Key Passes", "KEY_PASSES_P90", "KEY_PASSES_PCTILE"),
                ("Passes Attempted", "PASSES_ATTEMPTED_P90", "PASSES_ATTEMPTED_PCTILE"),
                ("Pass Completion %", "PASS_COMPLETION_PCT", "PASS_COMPLETION_PCTILE"),
                ("Touches (Att Pen)", "TOUCHES_IN_BOX_P90", "TOUCHES_IN_BOX_PCTILE"),
                ("Tackles Won", "TACKLES_WON_P90", "TACKLES_WON_PCTILE"),
                ("Interceptions", "INTERCEPTIONS_P90", "INTERCEPTIONS_PCTILE"),
                ("Clearances", "CLEARANCES_P90", "CLEARANCES_PCTILE"),
                ("Ball Recoveries", "BALL_RECOVERIES_P90", "BALL_RECOVERIES_PCTILE"),
                ("Dribbles Succ.", "DRIBBLES_SUCC_P90", "DRIBBLES_SUCC_PCTILE"),
                ("Aerial Duels Won", "AERIAL_DUELS_WON_P90", "AERIAL_DUELS_WON_PCTILE")
            ]

            labels = []
            values_p90 = []
            percentiles = []

            for label, p90_col, pct_col in metrics_config:
                if p90_col in player_row and pct_col in player_row:
                    labels.append(label)
                    values_p90.append(player_row[p90_col])
                    percentiles.append(player_row[pct_col])

            # Byg matplotlib-figur
            fig, ax = plt.subplots(figsize=(8, len(labels) * 0.45 + 1.5))
            
            y_pos = np.arange(len(labels))

            bar_colors = []
            for p in percentiles:
                if p >= 75:
                    bar_colors.append('#55a868') # Grøn
                elif p >= 40:
                    bar_colors.append('#999999') # Grå
                else:
                    bar_colors.append('#c44e52') # Rødbrun

            ax.barh(y_pos, percentiles, height=0.6, color=bar_colors, alpha=0.85)

            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=10)
            ax.invert_yaxis()
            ax.set_xlim(0, 100)
            ax.xaxis.set_visible(False)
            
            for spine in ['top', 'right', 'bottom', 'left']:
                ax.spines[spine].set_visible(False)

            ax.axvline(0, color='black', linewidth=1)
            
            for i, (val, pct) in enumerate(zip(values_p90, percentiles)):
                ax.text(-5, i, f"{val:.2f}" if isinstance(val, float) else str(val), 
                        va='center', ha='right', fontsize=9, fontweight='semibold')
                
                pct_text_x = max(pct + 2, 5) if pct < 90 else pct - 6
                ax.text(pct_text_x, i, f"{int(pct)}", va='center', ha='center', fontsize=9, fontweight='bold', color='white' if pct >= 40 else 'black')

            ax.set_title("vs. Forwards / Spillere", fontsize=12, fontweight='bold', color='white', backgroundcolor='#1b4d3e', pad=15, loc='left')

            minutter = player_row['MINUTTER']
            kampe = player_row['KAMPE']
            fig.text(0.1, 0.02, f"Spiller sammenlignet med ligastandarder. Baseret på {minutter} minutter fordelt på {kampe} kampe.", fontsize=9, fontstyle='italic')

            plt.tight_layout()
            st.pyplot(fig)
