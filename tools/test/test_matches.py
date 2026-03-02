import streamlit as st
import pandas as pd

def vis_side():
    st.title("📅 Kampprogram & Resultater")
    
    if "dp" not in st.session_state:
        st.error("Ingen data fundet.")
        return
        
    df = st.session_state["dp"].get("opta_matches", pd.DataFrame())
    
    if df.empty:
        st.warning("Ingen kampe fundet for den valgte liga/sæson.")
        return

    # Sørg for dato-formatet er rigtigt
    df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'])
    
    # Del op i Spillede og Kommende
    df_played = df[df['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False)
    df_fixtures = df[df['MATCH_STATUS'] == 'Fixture'].sort_values('MATCH_DATE_FULL', ascending=True)

    tab1, tab2 = st.tabs(["Kommende Kampe", "Seneste Resultater"])

    with tab1:
        for _, row in df_fixtures.head(10).iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 2])
                col1.markdown(f"**{row['CONTESTANTHOME_NAME']}**")
                col2.markdown(f"<div style='text-align:center;'>VS</div>", unsafe_allow_html=True)
                col3.markdown(f"<div style='text-align:right;'>**{row['CONTESTANTAWAY_NAME']}**</div>", unsafe_allow_html=True)
                
                st.caption(f"{row['MATCH_DATE_FULL'].strftime('%d. %b %Y')} | {row['VENUE_LONGNAME']}")

    with tab2:
        for _, row in df_played.head(15).iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
                c1.write(f"{row['CONTESTANTHOME_NAME']}")
                # Highlight Hvidovre resultater hvis de spiller
                score_text = f"**{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}**"
                c2.markdown(f"<div style='text-align:center; background:#f0f2f6; border-radius:4px;'>{score_text}</div>", unsafe_allow_html=True)
                c3.write(f"{row['CONTESTANTAWAY_NAME']}")
                c4.caption(f"👥 {int(row['ATTENDANCE'])}")
