import streamlit as st
import pandas as pd

def vis_side(dp):
    # 1. Hent data
    df_shots = dp.get("playerstats", pd.DataFrame())
    df_lb = dp.get("linebreaks", pd.DataFrame())
    df_xg_agg = dp.get("xg_agg", pd.DataFrame())

    # Standardiser kolonner
    for df in [df_shots, df_lb, df_xg_agg]:
        if not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]

    # 2. Opret Navne-Mapping (UUID -> NAVN)
    # Vi henter unikke par fra skud-dataen, da den har begge dele
    name_map = {}
    if not df_shots.empty and 'PLAYER_OPTAUUID' in df_shots.columns and 'PLAYER_NAME' in df_shots.columns:
        name_map = dict(zip(df_shots['PLAYER_OPTAUUID'], df_shots['PLAYER_NAME']))

    st.markdown("### SPILLER PERFORMANCE ANALYSE")

    t1, t2, t3, t4 = st.tabs([
        "GENERELT", 
        "OFFENSIVT", 
        "DEFENSIVT", 
        "LINEBREAKING PASSES"
    ])

    # --- TAB 1: GENERELT (Nu med navne) ---
    with t1:
        if not df_xg_agg.empty:
            st.write("OFFICIELLE OPTA XG STATS (SAESON TOTAL)")
            
            # Gruppér data
            xg_summary = df_xg_agg.groupby(['PLAYER_OPTAUUID', 'POSITION']).agg({
                'STAT_VALUE': 'sum'
            }).reset_index()

            # Oversæt UUID til Navn
            xg_summary['SPILLER'] = xg_summary['PLAYER_OPTAUUID'].map(name_map).fillna(xg_summary['PLAYER_OPTAUUID'])
            
            # Rydd op i visning
            xg_summary = xg_summary[['SPILLER', 'POSITION', 'STAT_VALUE']]
            xg_summary.columns = ['SPILLER', 'POSITION', 'TOTAL XG']
            xg_summary = xg_summary.sort_values('TOTAL XG', ascending=False)
            
            st.dataframe(xg_summary, use_container_width=True, hide_index=True)
        else:
            st.write("Ingen aggregeret xG data fundet.")

    # --- TAB 2: OFFENSIVT (xG pr. skud) ---
    with t2:
        if not df_shots.empty:
            st.write("AFSLUTNINGSSTATISTIK OG KVALITET")
            
            off_stats = df_shots.groupby('PLAYER_NAME').agg({
                'EVENT_OPTAUUID': 'count',
                'XG_VAL': 'sum',
                'EVENT_TYPEID': lambda x: (x == 16).sum() 
            }).rename(columns={
                'EVENT_OPTAUUID': 'SKUD',
                'XG_VAL': 'TOTAL XG',
                'EVENT_TYPEID': 'MAAL'
            })

            off_stats['XG PR. SKUD'] = (off_stats['TOTAL XG'] / off_stats['SKUD']).round(3)
            off_stats = off_stats[['MAAL', 'SKUD', 'TOTAL XG', 'XG PR. SKUD']].sort_values('TOTAL XG', ascending=False)

            st.dataframe(
                off_stats.style.format({'TOTAL XG': '{:.2f}', 'XG PR. SKUD': '{:.3f}'}),
                use_container_width=True
            )
        else:
            st.write("Ingen skuddata fundet.")

    # --- TAB 3: DEFENSIVT ---
    with t3:
        st.write("Defensive metrics er under udarbejdelse.")

    # --- TAB 4: LINEBREAKING PASSES (Nu med navne) ---
    with t4:
        if not df_lb.empty:
            st.write("LINEBREAKING PASSES AGGREGATES")
            
            lb_pivot = df_lb.pivot_table(
                index='PLAYER_OPTAUUID', 
                columns='STAT_TYPE', 
                values='STAT_VALUE', 
                aggfunc='sum'
            ).fillna(0).reset_index()

            # Oversæt UUID til Navn
            lb_pivot.insert(0, 'SPILLER', lb_pivot['PLAYER_OPTAUUID'].map(name_map).fillna(lb_pivot['PLAYER_OPTAUUID']))
            lb_pivot = lb_pivot.drop(columns=['PLAYER_OPTAUUID'])
            
            lb_pivot = lb_pivot.sort_values(by=lb_pivot.columns[1], ascending=False)
            st.dataframe(lb_pivot, use_container_width=True, hide_index=True)
        else:
            st.write("Ingen Linebreak data fundet.")
