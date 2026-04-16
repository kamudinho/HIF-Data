import streamlit as st
import pandas as pd
import data.HIF_load as hif_load

def vis_side():
    st.markdown("### PHYSICAL & TECHNICAL PROFILES")
    
    try:
        # 1. HENT DATA
        dp = hif_load.get_scouting_package()
        df_all = dp["sql_players"]

        # --- DEBUG: Sørg for at vi rammer de rigtige kolonnenavne ---
        # Vi tvinger alle kolonnenavne til store bogstaver for at gøre det nemmere
        df_all.columns = [c.upper() for c in df_all.columns]
        
        # Tjek hvilken kolonne der indeholder holdnavnet
        team_col = 'TEAM_NAME' if 'TEAM_NAME' in df_all.columns else None
        if not team_col:
            # Hvis 'TEAM_NAME' ikke findes, leder vi efter noget der ligner
            potential_cols = [c for c in df_all.columns if 'TEAM' in c or 'HOLD' in c]
            if potential_cols:
                team_col = potential_cols[0]

        if not team_col:
            st.error(f"Kunne ikke finde en kolonne med holdnavne. Tilgængelige kolonner: {list(df_all.columns[:10])}...")
            return

        # 2. HOLD-VÆLGER
        hold_liste = sorted(df_all[team_col].unique().tolist())
        valgt_hold = st.selectbox("Vælg Hold", options=hold_liste)
        
        if valgt_hold:
            df_input = df_all[df_all[team_col] == valgt_hold].copy()
            
            # 3. DYNAMISK AGGREGERING
            # Vi definerer de metrics vi leder efter og tjekker om de findes
            metrics = {
                'TOUCHES_IN_BOX': 'TOUCHES IN BOX',
                'SUCCESSFUL_PASSES_PERCENT': 'PASS %',
                'DUELS_WON': 'VUNDNE DUEL',
                'GOALS': 'MÅL'
            }
            
            # Vi opbygger en agg_dict kun med de kolonner der faktisk findes
            agg_dict = {}
            found_metrics = []
            
            for col, label in metrics.items():
                if col in df_input.columns:
                    agg_dict[col] = 'sum' if col != 'SUCCESSFUL_PASSES_PERCENT' else 'mean'
                    found_metrics.append((col, label))
            
            if not agg_dict:
                st.warning(f"Ingen af de forventede statistikker blev fundet. Kolonner i dit data: {list(df_input.columns)}")
                return

            stats = df_input.groupby('PLAYER_NAME').agg(agg_dict).reset_index()

            # Beregn en score baseret på hvad vi har fundet
            stats['Score'] = 0
            for col in agg_dict.keys():
                stats['Score'] += stats[col]

            top_5 = stats.sort_values('Score', ascending=False).head(5)

            # 4. VISNING
            cols = st.columns(5)
            farver = ["#df003b", "#084594", "#238b45", "#ec7014"]

            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    navn_dele = row['PLAYER_NAME'].split()
                    st.markdown(f"**{navn_dele[-1].upper() if navn_dele else 'SPILLER'}**")
                    st.caption(row['PLAYER_NAME'])
                    st.markdown("<hr style='margin:10px 0; border:1px solid #eee'>", unsafe_allow_html=True)
                    
                    def draw_bar(label, val, max_val, color):
                        percent = min(int((val / max_val) * 100), 100) if max_val > 0 else 0
                        st.markdown(f"""
                            <div style="font-size: 10px; color: #666; margin-top: 8px;">{label}</div>
                            <div style="background-color: #f1f1f1; border-radius: 3px; height: 6px; width: 100%;">
                                <div style="background-color: {color}; height: 6px; width: {percent}%; border-radius: 3px;"></div>
                            </div>
                            <div style="font-size: 10px; font-weight: bold; text-align: right; margin-top: 2px;">{val:.1f}</div>
                        """, unsafe_allow_html=True)

                    # Tegn de metrics vi har fundet
                    for j, (col, label) in enumerate(found_metrics):
                        draw_bar(label, row[col], stats[col].max() if stats[col].max() > 0 else 1, farver[j % len(farver)])

    except Exception as e:
        st.error(f"Kritisk fejl: {e}")
