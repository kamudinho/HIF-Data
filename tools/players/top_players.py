import streamlit as st
import pandas as pd
import data.HIF_load as hif_load  # Vi bruger din eksisterende loader

def vis_side():
    st.markdown("### PHYSICAL & TECHNICAL PROFILES")
    
    # 1. HENT DATA (Vi genbruger din pakke-loader)
    try:
        # Vi henter scouting-pakken, da den indeholder alle spillere/hold
        dp = hif_load.get_scouting_package()
        df_all = dp["sql_players"] # Vi bruger sql_players som udgangspunkt
        
        # 2. HOLD-VÆLGER
        hold_liste = sorted(df_all['TEAM_NAME'].unique().tolist())
        valgt_hold = st.selectbox("Vælg Hold", options=hold_liste, index=hold_liste.index("Hvidovre") if "Hvidovre" in hold_liste else 0)
        
        if valgt_hold:
            # Filtrér til det valgte hold
            df_input = df_all[df_all['TEAM_NAME'] == valgt_hold].copy()
            
            # 3. DATABEHANDLING (Selve analysen)
            # Vi tjekker kolonnenavne for at sikre de matcher din Snowflake-struktur
            # Hvis 'EVENT_X' ikke findes i sql_players, bruger vi de færdige stats
            stats = df_input.groupby('PLAYER_NAME').agg({
                'TOUCHES_IN_BOX': 'sum',
                'SUCCESSFUL_PASSES_PERCENT': 'mean', # Kan bruges som gennembrud-proxy
                'DUELS_WON': 'sum',
                'GOALS': 'sum'
            }).reset_index()

            # Find top 5 baseret på en vægtet score
            stats['Score'] = (stats['TOUCHES_IN_BOX'] * 2) + (stats['DUELS_WON'] * 1) + (stats['GOALS'] * 5)
            top_5 = stats.sort_values('Score', ascending=False).head(5)

            # 4. VISNING (Kolonnerne)
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
                            <div style="font-size: 10px; color: #666; margin-top: 8px;">{label}</div>
                            <div style="background-color: #f1f1f1; border-radius: 3px; height: 6px; width: 100%;">
                                <div style="background-color: {color}; height: 6px; width: {percent}%; border-radius: 3px;"></div>
                            </div>
                            <div style="font-size: 10px; font-weight: bold; text-align: right; margin-top: 2px;">{int(val)}</div>
                        """, unsafe_allow_html=True)

                    draw_bar("TOUCHES BOX", row['TOUCHES_IN_BOX'], stats['TOUCHES_IN_BOX'].max(), farver[0])
                    draw_bar("PASS %", row['SUCCESSFUL_PASSES_PERCENT'], 100, farver[1])
                    draw_bar("VUNDNE DUEL", row['DUELS_WON'], stats['DUELS_WON'].max(), farver[2])
                    draw_bar("MÅL", row['GOALS'], stats['GOALS'].max() if stats['GOALS'].max() > 0 else 1, farver[3])

    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")
        st.info("Tjek om kolonnenavne som 'TOUCHES_IN_BOX' findes i dit sql_players output.")
