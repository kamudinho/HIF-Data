import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def vis_side():
    st.markdown("### PHYSICAL & TECHNICAL PROFILES")
    st.write("Vælg et hold for at se de 5 mest kampafgørende profiler")

    # 1. HENT FORBINDELSE OG HENT ALLE HOLD TIL SELECTBOX
    conn = _get_snowflake_conn()
    
    # Her henter vi en liste over holdene, så brugeren kan vælge et
    # Jeg antager her, at dit store dataframe hedder 'df' eller at vi kan hente holdnavne
    try:
        # Hent unikke holdnavne fra din database (NordicBet Liga 25/26 jf. dine indstillinger)
        query = "SELECT DISTINCT TEAM_NAME, TEAM_WYID FROM DINE_DATA_TABEL WHERE SEASONNAME = '2025/2026'"
        df_teams = conn.query(query)
        
        hold_liste = df_teams['TEAM_NAME'].unique().tolist()
        valgt_hold = st.selectbox("Vælg Modstander", options=hold_liste)
        
        if valgt_hold:
            # 2. HENT DATA FOR DET VALGTE HOLD
            # Vi henter kun de nødvendige kolonner for at optimere hastigheden
            query_data = f"SELECT * FROM DINE_DATA_TABEL WHERE TEAM_NAME = '{valgt_hold}' AND SEASONNAME = '2025/2026'"
            df_input = conn.query(query_data)
            
            if not df_input.empty:
                # 3. DATABEHANDLING (Top 5 logik)
                stats = df_input.groupby('PLAYER_NAME').agg(
                    Touches_Box=('EVENT_X', lambda x: ((df_input.loc[x.index, 'EVENT_X'] > 83) & 
                                                       (df_input.loc[x.index, 'EVENT_Y'].between(21, 79))).sum()),
                    Gennembrud=('EVENT_TYPEID', lambda x: ((df_input.loc[x.index, 'EVENT_TYPEID'] == 1) & 
                                                           (df_input.loc[x.index, 'EVENT_X'] > 70)).sum()),
                    Dueller=('EVENT_TYPEID', lambda x: x.isin([7, 44]).sum()),
                    Chancer=('qual_list', lambda x: x.apply(lambda q: '210' in q or '209' in q).sum())
                ).reset_index()

                stats['Score'] = (stats['Touches_Box'] * 3) + (stats['Gennembrud'] * 1.5) + (stats['Chancer'] * 2)
                top_5 = stats.sort_values('Score', ascending=False).head(5)

                # 4. VISNING (De 5 kolonner)
                cols = st.columns(5)
                farver = ["#df003b", "#084594", "#238b45", "#ec7014"]

                for i, (idx, row) in enumerate(top_5.iterrows()):
                    with cols[i]:
                        efternavn = row['PLAYER_NAME'].split()[-1].upper()
                        st.markdown(f"**{efternavn}**")
                        st.caption(row['PLAYER_NAME'])
                        st.markdown("<hr style='margin:10px 0; border:1px solid #eee'>", unsafe_allow_html=True)
                        
                        def draw_bar(label, val, max_val, color):
                            percent = min(int((val / max_val) * 100), 100) if max_val > 0 else 0
                            st.markdown(f"""
                                <div style="font-size: 10px; color: #666; margin-top: 8px; text-transform: uppercase;">{label}</div>
                                <div style="background-color: #f1f1f1; border-radius: 3px; height: 6px; width: 100%;">
                                    <div style="background-color: {color}; height: 6px; width: {percent}%; border-radius: 3px;"></div>
                                </div>
                                <div style="font-size: 10px; font-weight: bold; text-align: right; margin-top: 2px;">{int(val)}</div>
                            """, unsafe_allow_html=True)

                        draw_bar("Box Touches", row['Touches_Box'], stats['Touches_Box'].max(), farver[0])
                        draw_bar("Gennembrud", row['Gennembrud'], stats['Gennembrud'].max(), farver[1])
                        draw_bar("Dueller", row['Dueller'], stats['Dueller'].max(), farver[2])
                        draw_bar("Chancer", row['Chancer'], stats['Chancer'].max(), farver[3])
            else:
                st.info("Ingen data fundet for det valgte hold.")
                
    except Exception as e:
        st.error(f"Kunne ikke hente data fra databasen: {e}")
