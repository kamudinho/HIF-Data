import streamlit as st
import pandas as pd

def vis_side(dp):
    st.markdown("### Spiller Performance – Hvidovre IF")
    
    t1, t2, t3, t4 = st.tabs(["Generelt", "Offensivt", "Defensivt", "Linebreaking Passes"])

    with t1:
        df_xg = dp.get("xg_agg", pd.DataFrame())
        if not df_xg.empty:
            res = df_xg.groupby('PLAYER_OPTAUUID')['STAT_VALUE'].sum().sort_values(ascending=False)
            st.write("Top xG (Aggregeret)")
            st.dataframe(res)
        else:
            st.info("Ingen generel data fundet.")

    with t2:
        df_shots = dp.get("playerstats", pd.DataFrame())
        if not df_shots.empty:
            off = df_shots.groupby('PLAYER_NAME').agg({'EVENT_OPTAUUID': 'count', 'XG_VAL': 'sum'})
            off.columns = ['Skud', 'Total xG']
            st.dataframe(off.sort_values('Total xG', ascending=False))

    with t3:
        st.info("Defensive stats (tacklinger/erobringer) kommer i næste opdatering.")

    with t4:
        df_lb = dp.get("linebreaks", pd.DataFrame())
        if not df_lb.empty:
            lb_pivot = df_lb.pivot_table(index='PLAYER_OPTAUUID', columns='STAT_TYPE', values='STAT_VALUE', aggfunc='sum').fillna(0)
            st.dataframe(lb_pivot)
        else:
            st.warning("Ingen Linebreak data fundet.")
