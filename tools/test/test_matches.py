import streamlit as st

def vis_match_stats(match_id, dp):
    # Filtrer stats for den specifikke kamp fra vores Opta-data
    stats_df = dp["opta_team_stats"][dp["opta_team_stats"]["MATCH_OPTAUUID"] == match_id]
    
    if stats_df.empty:
        st.info("Statistikker er endnu ikke tilgængelige for denne kamp.")
        return

    # Lav en pæn sammenligning af de vigtigste Opta-tal
    # Vi pivot'er dataen så vi har stats som rækker og hold som kolonner
    pivot_stats = stats_df.pivot(index='STAT_TYPE', columns='CONTESTANT_OPTAUUID', values='STAT_TOTAL')
    
    # Eksempel på visning af Key Performance Indicators (KPIs)
    kpis = {
        "expectedGoals": "Expected Goals (xG)",
        "possessionPercentage": "Boldbesiddelse %",
        "totalPasses": "Afsluttede afleveringer",
        "shotsOnTarget": "Skud på mål"
    }

    st.write("### 📊 Kampstatistik (Opta Data)")
    for key, label in kpis.items():
        if key in pivot_stats.index:
            home_val = pivot_stats.iloc[pivot_stats.index == key, 0].values[0]
            away_val = pivot_stats.iloc[pivot_stats.index == key, 1].values[0]
            
            # Lav en visuel bar-comparison
            st.write(f"**{label}**")
            col_h, col_a = st.columns([float(home_val), float(away_val)])
            col_h.markdown(f"<div style='background:#cc0000; text-align:right; padding-right:10px; color:white;'>{home_val}</div>", unsafe_allow_html=True)
            col_a.markdown(f"<div style='background:#333; padding-left:10px; color:white;'>{away_val}</div>", unsafe_allow_html=True)
