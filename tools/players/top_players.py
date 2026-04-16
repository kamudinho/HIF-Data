import streamlit as st
import pandas as pd
import data.HIF_load as hif_load

def vis_side():
    st.markdown("### PHYSICAL & TECHNICAL PROFILES")
    
    try:
        # 1. DATA INDLÆSNING (Prøv alle pakker)
        dp = hif_load.get_scouting_package()
        
        # Vi samler alt data vi kan finde for at få både stats og billeder
        df_stats = dp.get("players", pd.DataFrame())
        if df_stats.empty:
            df_stats = dp.get("advanced_stats", pd.DataFrame())
        
        df_meta = dp.get("sql_players", pd.DataFrame())

        if df_stats.empty:
            st.error("Kunne ikke finde statistik-data.")
            return

        # Normaliser kolonnenavne til STORE (for konsistens)
        df_stats.columns = [c.upper() for c in df_stats.columns]
        if not df_meta.empty:
            df_meta.columns = [c.upper() for c in df_meta.columns]

        # 2. FIND HOLD-KOLONNE OG VÆLG HOLD
        team_col = next((c for c in df_stats.columns if 'TEAM' in c or 'HOLD' in c), None)
        if not team_col:
            st.warning("Hold-data ikke fundet.")
            return

        hold_liste = sorted(df_stats[team_col].unique().tolist())
        valgt_hold = st.selectbox("Vælg Hold", options=hold_liste)
        
        if valgt_hold:
            df_hold = df_stats[df_stats[team_col] == valgt_hold].copy()

            # 3. DYNAMISK DATA-UDTRÆK (Hvad leder vi efter?)
            # Vi definerer de ønskede metrics og deres mulige navne i dit data
            target_metrics = {
                "TOUCHES": ["TOUCHES_IN_BOX", "TOUCHES_BOX", "ATT_PEN_TOUCHES"],
                "GENNEMBRUD": ["SUCCESSFUL_PASSES_PERCENT", "PASS_ACC", "ACCURATE_PASSES_PCT"],
                "DUELLER": ["WON_DUELS", "DUELS_WON", "DEF_DUELS_WON"],
                "MÅL/CHANCER": ["GOALS", "EXPECTED_GOALS", "XG", "CHANCES_CREATED"]
            }

            # Find de 5 mest aktive spillere (baseret på hvad der nu findes af tal)
            numeric_cols = df_hold.select_dtypes(include=['number']).columns
            df_hold['TOTAL_SCORE'] = df_hold[numeric_cols].sum(axis=1)
            top_5 = df_hold.sort_values('TOTAL_SCORE', ascending=False).head(5)

            # 4. GRID VISNING (5 Kolonner)
            cols = st.columns(5)
            
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    player_name = row.get('PLAYER_NAME', 'Ukendt Spiller')
                    efternavn = str(player_name).split()[-1].upper()
                    
                    # Vis Billede (hvis findes i df_meta)
                    img_url = None
                    if not df_meta.empty and 'PLAYER_NAME' in df_meta.columns:
                        match = df_meta[df_meta['PLAYER_NAME'] == player_name]
                        if not match.empty:
                            img_url = match.iloc[0].get('IMAGEDATAURL')
                    
                    if img_url:
                        st.image(img_url, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150?text=INGEN+FOTO", use_container_width=True)

                    st.markdown(f"**{efternavn}**")
                    st.caption(player_name)
                    st.markdown("<hr style='margin:5px 0; border:1px solid #eee'>", unsafe_allow_html=True)

                    # DYNAMISKE BARS (Tjekker hver kategori)
                    for label, potential_names in target_metrics.items():
                        # Find den første kolonne der matcher vores liste
                        found_col = next((c for c in potential_names if c in df_hold.columns), None)
                        
                        val_display = "-"
                        percent = 0
                        
                        if found_col:
                            val = row[found_col]
                            if pd.notnull(val):
                                val_display = f"{val:.1f}" if isinstance(val, (float, int)) else val
                                # Beregn procent ift. holdets max i den kolonne
                                max_val = df_hold[found_col].max()
                                percent = min(int((val / max_val) * 100), 100) if max_val > 0 else 0

                        # HTML Tegning
                        st.markdown(f"""
                            <div style="font-size: 9px; color: #666; margin-top: 5px; text-transform: uppercase;">{label}</div>
                            <div style="background-color: #eee; height: 5px; width: 100%; border-radius: 2px;">
                                <div style="background-color: #df003b; height: 5px; width: {percent}%; border-radius: 2px;"></div>
                            </div>
                            <div style="font-size: 10px; text-align: right; font-weight: bold;">{val_display}</div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Fejl: {e}")
