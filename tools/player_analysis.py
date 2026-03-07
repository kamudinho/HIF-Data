import streamlit as st
import pandas as pd

def vis_side(dp):
    # 1. Hent data fra pakken
    df_shots = dp.get("playerstats", pd.DataFrame())
    df_lb = dp.get("linebreaks", pd.DataFrame())
    df_xg_agg = dp.get("xg_agg", pd.DataFrame())

    # Sikr at kolonner er i Upper Case for teknisk konsistens
    for df in [df_shots, df_lb, df_xg_agg]:
        if not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]

    st.markdown("### SPILLER PERFORMANCE ANALYSE")

    # Opret Tabs uden ikoner
    t1, t2, t3, t4 = st.tabs([
        "GENERELT", 
        "OFFENSIVT", 
        "DEFENSIVT", 
        "LINEBREAKING PASSES"
    ])

    # --- TAB 1: GENERELT (xG Aggregates fra OPTA) ---
    with t1:
        if not df_xg_agg.empty:
            st.write("OFFICIELLE OPTA XG STATS (SAESON TOTAL)")
            xg_summary = df_xg_agg.groupby(['PLAYER_OPTAUUID', 'POSITION']).agg({
                'STAT_VALUE': 'sum'
            }).rename(columns={'STAT_VALUE': 'TOTAL XG'}).sort_values('TOTAL XG', ascending=False)
            
            st.dataframe(xg_summary, use_container_width=True)
        else:
            st.info("Ingen aggregeret xG data fundet.")

    # --- TAB 2: OFFENSIVT (Afslutninger & xG pr. skud) ---
    with t2:
        if not df_shots.empty:
            st.write("AFSLUTNINGSSTATISTIK OG KVALITET")
            
            # Beregn stats pr. spiller (EVENT_TYPEID 16 = Maal)
            off_stats = df_shots.groupby('PLAYER_NAME').agg({
                'EVENT_OPTAUUID': 'count',
                'XG_VAL': 'sum',
                'EVENT_TYPEID': lambda x: (x == 16).sum() 
            }).rename(columns={
                'EVENT_OPTAUUID': 'SKUD',
                'XG_VAL': 'TOTAL XG',
                'EVENT_TYPEID': 'MAAL'
            })

            # BEREGNING: xG pr. skud
            off_stats['XG PR. SKUD'] = (off_stats['TOTAL XG'] / off_stats['SKUD']).round(3)
            
            # Sortering og udvalg
            off_stats = off_stats[['MAAL', 'SKUD', 'TOTAL XG', 'XG PR. SKUD']]
            off_stats = off_stats.sort_values('TOTAL XG', ascending=False)

            # Tabelvisning med simpel formatering
            st.dataframe(
                off_stats.style.format({
                    'TOTAL XG': '{:.2f}', 
                    'XG PR. SKUD': '{:.3f}'
                }),
                use_container_width=True
            )
        else:
            st.warning("Ingen skuddata tilgaengelig.")

    # --- TAB 3: DEFENSIVT ---
    with t3:
        st.info("Defensive metrics er under udarbejdelse.")

    # --- TAB 4: LINEBREAKING PASSES ---
    with t4:
        if not df_lb.empty:
            st.write("LINEBREAKING PASSES AGGREGATES")
            
            # Pivotér data
            lb_pivot = df_lb.pivot_table(
                index='PLAYER_OPTAUUID', 
                columns='STAT_TYPE', 
                values='STAT_VALUE', 
                aggfunc='sum'
            ).fillna(0)

            if not lb_pivot.empty:
                # Sorter efter første kolonne (oftest completed passes)
                lb_pivot = lb_pivot.sort_values(by=lb_pivot.columns[0], ascending=False)
                st.dataframe(lb_pivot, use_container_width=True)
            else:
                st.write("Data kunne ikke pivotores.")
        else:
            st.warning("Ingen Linebreak data fundet.")
