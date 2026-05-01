import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def generer_konklusion(aktuel, base, metric_navn):
    """Matcher stilen fra dit screenshot med specifikke tekst-output"""
    diff = aktuel - base
    # For PPDA og xG imod er lavere tal bedre
    if metric_navn in ["PPDA", "xG imod"]:
        if diff < 0: return "Strong defensive organization and pressure"
        return "Struggling to limit opposition chances"
    
    if diff > 0: return "Performing above league average in this area"
    return "Limited output - currently underperforming"

def vis_side():
    # Overskrift der matcher din branding
    st.markdown("### Performance Analysis")
    
    # 1. Load data
    conn = _get_snowflake_conn()
    # Bruger dine gemte værdier for sæson og liga
    query = """
        SELECT t.TEAMNAME, AVG(adv.XG) as XG, AVG(adv.GOALS) as GOALS
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMMATCHES tm
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID
        WHERE tm.COMPETITION_WYID = 328 AND tm.SEASONNAME = '2025/2026'
        GROUP BY t.TEAMNAME
    """
    df_wy = conn.query(query)
    
    # 2. Vælg hold
    hold_liste = sorted(df_wy['TEAMNAME'].unique().tolist())
    valgt_hold = st.selectbox("Vælg hold til analyse:", hold_liste)
    
    # 3. Metrics Setup (Her kan du tilføje flere fra dine data)
    # Som eksempel bruger vi faste værdier for at matche dit billede 1:1
    sections = {
        "Attacking Output": {
            "Total goals scored": {"val": 63, "rank": "8th"},
            "Open-play goals": {"val": 25, "rank": "15th"},
            "xG Difference": {"val": -10, "text": "10 fewer goals scored than xG created"},
            "conclusion": "limited by poor quality finishing"
        },
        "Chance Creation": {
            "xG per shot": {"val": 0.14, "rank": "1st"},
            "Shots outside box": {"val": "27%", "rank": "24th"},
            "Final-third to box entries": {"val": "16%", "rank": "18th"},
            "conclusion": "prefer high quality chances, but struggle to get into the box"
        }
    }

    # 4. Rendering i det ønskede liste-format
    for section, metrics in sections.items():
        st.markdown(f"#### {section}:")
        
        # Loop gennem metrics i sektionen (undtagen konklusionen)
        for m_navn, m_data in metrics.items():
            if m_navn == "conclusion":
                continue
                
            # Formater linjen: Rank (hvis findes) + Navn + Værdi
            if "rank" in m_data:
                st.markdown(f"• **{m_data['rank']}** for {m_navn.lower()} ({m_data['val']})")
            else:
                st.markdown(f"• {m_data['text']}")
        
        # Tilføj den farvede konklusion nederst i hver sektion
        st.markdown(f"<p style='color:#df003b; font-weight:bold; margin-top:5px;'>Conclusion – {metrics['conclusion']}</p>", unsafe_allow_html=True)
        st.write("") # Skaber luft mellem sektioner

if __name__ == "__main__":
    vis_side()
