import streamlit as st
import pandas as pd
import data.HIF_load as hif_load

def vis_side():
    st.markdown("### PHYSICAL & TECHNICAL PROFILES")
    
    try:
        # 1. DATA INDLÆSNING
        dp = hif_load.get_scouting_package()
        
        # Forsøg at hente fra de mest sandsynlige kilder i din datapakke
        df_stats = dp.get("players", pd.DataFrame())
        if df_stats.empty:
            df_stats = dp.get("advanced_stats", pd.DataFrame())
        
        df_meta = dp.get("sql_players", pd.DataFrame())

        if df_stats.empty:
            st.error("Kunne ikke finde statistik-data i systemet.")
            return

        # Normaliser kolonnenavne til STORE for at undgå case-fejl
        df_stats.columns = [c.upper() for c in df_stats.columns]
        if not df_meta.empty:
            df_meta.columns = [c.upper() for c in df_meta.columns]

        # 2. FIND HOLD-KOLONNE OG VÆLG HOLD
        team_col = next((c for c in df_stats.columns if 'TEAM' in c or 'HOLD' in c), None)
        if not team_col:
            st.warning("Kunne ikke finde en kolonne med holdnavne.")
            return

        hold_liste = sorted(df_stats[team_col].unique().tolist())
        valgt_hold = st.selectbox("Vælg Hold", options=hold_liste)
        
        if valgt_hold:
            # Filtrér til det valgte hold
            df_hold = df_stats[df_stats[team_col] == valgt_hold].copy()

            # 3. DATABLIKKEN (RENSNING AF TAL)
            # Her definerer vi de kategorier, vi leder efter (aliasing)
            target_metrics = {
                "TOUCHES": ["TOUCHES_IN_BOX", "TOUCHES_BOX", "ATT_PEN_TOUCHES", "TOUCHES"],
                "GENNEMBRUD": ["SUCCESSFUL_PASSES_PERCENT", "PASS_ACC", "ACCURATE_PASSES_PCT", "PASS_PCT"],
                "DUELLER": ["WON_DUELS", "DUELS_WON", "DEF_DUELS_WON", "DUELS_PCT"],
                "MÅL/CHANCER": ["GOALS", "EXPECTED_GOALS", "XG", "CHANCES_CREATED", "ASSISTS"]
            }

            # VIGTIGT: Rens alle potentielle tal-kolonner for tekst (fjerner float/str fejl)
            potential_cols = df_hold.columns.drop(['PLAYER_NAME', team_col]) if 'PLAYER_NAME' in df_hold.columns else df_hold.columns
            for col in potential_cols:
                # Konverter til tal, gør fejl til NaN, og NaN til 0
                df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0)

            # Find de 5 mest aktive spillere baseret på summen af deres stats
            numeric_cols = df_hold.select_dtypes(include=['number']).columns
            df_hold['TOTAL_SCORE'] = df_hold[numeric_cols].sum(axis=1)
            top_5 = df_hold.sort_values('TOTAL_SCORE', ascending=False).head(5)

            # 4. GRID VISNING (5 Kolonner)
            cols = st.columns(5)
            
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    player_name = row.get('PLAYER_NAME', 'Ukendt')
                    efternavn = str(player_name).split()[-1].upper()
                    
                    # Billede-logik
                    img_url = None
                    if not df_meta.empty and 'PLAYER_NAME' in df_meta.columns:
                        match = df_meta[df_meta['PLAYER_NAME'] == player_name]
                        if not match.empty:
                            img_url = match.iloc[0].get('IMAGEDATAURL')
                    
                    if img_url:
                        st.image(img_url, use_container_width=True)
                    else:
                        # Placeholder hvis billede mangler
                        st.image("https://via.placeholder.com/150/f1f1f1/888888?text=NO+PHOTO", use_container_width=True)

                    st.markdown(f"**{efternavn}**")
                    st.caption(player_name)
                    st.markdown("<hr style='margin:5px 0; border:1px solid #eee'>", unsafe_allow_html=True)

                    # DYNAMISKE BARS
                    for label, potential_names in target_metrics.items():
                        # Find den første kolonne der matcher vores liste
                        found_col = next((c for c in potential_names if c in df_hold.columns), None)
                        
                        val_display = "-"
                        percent = 0
                        
                        if found_col:
                            val = row[found_col]
                            # Tjek om vi har et brugbart tal
                            if pd.notnull(val) and val != 0:
                                val_display = f"{val:.1f}"
                                # Beregn procent ift. holdets max i netop denne kolonne
                                max_val = df_hold[found_col].max()
                                percent = min(int((val / max_val) * 100), 100) if max_val > 0 else 0

                        # HTML Styling af barerne
                        st.markdown(f"""
                            <div style="font-size: 9px; color: #666; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.5px;">{label}</div>
                            <div style="background-color: #f0f2f6; height: 6px; width: 100%; border-radius: 3px; margin-top: 2px;">
                                <div style="background-color: #df003b; height: 6px; width: {percent}%; border-radius: 3px;"></div>
                            </div>
                            <div style="font-size: 10px; text-align: right; font-weight: 700; color: #1f1f1f; margin-top: 2px;">{val_display}</div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Der opstod en fejl: {e}")
