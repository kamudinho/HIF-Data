import streamlit as st
from mplsoccer import VerticalPitch
import seaborn as sns

def vis_side(df_live, hold_map):
    st.header("Taktisk Modstanderanalyse")
    if df_live is None or df_live.empty:
        st.info("Ingen data fundet i Snowflake for denne sæson.")
        return

    df_live['PRIMARYTYPE'] = df_live['PRIMARYTYPE'].str.lower()
    df_live['HOLD_NAVN'] = df_live['TEAM_WYID'].astype(str).map(hold_map).fillna(df_live['TEAM_WYID'].astype(str))
    
    valgt_hold = st.sidebar.selectbox("Vælg modstander", sorted(df_live['HOLD_NAVN'].unique()))
    hold_data = df_live[df_live['HOLD_NAVN'] == valgt_hold]

    cols = st.columns(3)
    pitch = VerticalPitch(pitch_type='wyscout', pitch_color='white', line_color='#888888', linewidth=0.5)
    
    configs = [('pass', 'PASNINGER (FINAL 3RD)', 'Reds'), ('shot', 'EGNE SKUD', 'YlOrBr'), ('shot_against', 'SKUD IMOD', 'Purples')]

    for i, (t, title, cmap) in enumerate(configs):
        with cols[i]:
            st.markdown(f"<p style='text-align:center; font-weight:bold;'>{title}</p>", unsafe_allow_html=True)
            fig, ax = pitch.draw(figsize=(2, 3))
            d = hold_data[hold_data['PRIMARYTYPE'] == t]
            if not d.empty:
                sns.kdeplot(x=d['LOCATIONY'], y=d['LOCATIONX'], fill=True, alpha=.5, cmap=cmap, ax=ax)
            st.pyplot(fig)
