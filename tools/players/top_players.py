import streamlit as st
import pandas as pd
import data.HIF_load as hif_load

def vis_side():
    st.markdown("### PHYSICAL & TECHNICAL PROFILES")
    
    try:
        # 1. HENT DATA
        dp = hif_load.get_scouting_package()
        df_stats = dp.get("players", pd.DataFrame())
        if df_stats.empty:
            df_stats = dp.get("advanced_stats", pd.DataFrame())
        df_meta = dp.get("sql_players", pd.DataFrame())

        if df_stats.empty:
            st.error("Kunne ikke finde statistik-data.")
            return

        # Normaliser navne
        df_stats.columns = [c.upper() for c in df_stats.columns]
        if not df_meta.empty:
            df_meta.columns = [c.upper() for c in df_meta.columns]

        # 2. HOLD-VÆLGER
        team_col = next((c for c in df_stats.columns if 'TEAM' in c or 'HOLD' in c), None)
        if not team_col:
            st.warning("Hold-kolonne ikke fundet.")
            return

        hold_liste = sorted(df_stats[team_col].unique().tolist())
        valgt_hold = st.selectbox("Vælg Hold", options=hold_liste)
        
        if valgt_hold:
            # Filtrér og lav en kopi
            df_hold = df_stats[df_stats[team_col] == valgt_hold].copy()

            # --- DENNE SEKTION DRÆBER FEJLEN ---
            # Vi tvinger PLAYER_NAME til at være string med det samme
            if 'PLAYER_NAME' in df_hold.columns:
                df_hold['PLAYER_NAME'] = df_hold['PLAYER_NAME'].astype(str)

            # Vi finder alle numeriske kolonner og tvinger dem til float
            # Alt der ikke er tal bliver til 0.0
            for col in df_hold.columns:
                if col not in ['PLAYER_NAME', team_col]:
                    df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0.0).astype(float)

            # Nu er vi 100% sikre på at alle beregnings-kolonner er floats
            numeric_cols = df_hold.select_dtypes(include=['number']).columns
            df_hold['TOTAL_SCORE'] = df_hold[numeric_cols].sum(axis=1)
            
            # Sortering kan ikke fejle nu
            top_5 = df_hold.sort_values(by='TOTAL_SCORE', ascending=False).head(5)
            # ----------------------------------

            # 4. GRID VISNING
            target_metrics = {
                "TOUCHES": ["TOUCHES_IN_BOX", "TOUCHES_BOX", "ATT_PEN_TOUCHES"],
                "GENNEMBRUD": ["SUCCESSFUL_PASSES_PERCENT", "PASS_ACC", "ACCURATE_PASSES_PCT"],
                "DUELLER": ["WON_DUELS", "DUELS_WON", "DEF_DUELS_WON"],
                "MÅL/CHANCER": ["GOALS", "EXPECTED_GOALS", "XG", "CHANCES_CREATED"]
            }

            cols = st.columns(5)
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    p_name = str(row.get('PLAYER_NAME', 'Ukendt'))
                    st.markdown(f"**{p_name.split()[-1].upper()}**")
                    st.caption(p_name)
                    
                    # Billede
                    img_url = None
                    if not df_meta.empty and 'PLAYER_NAME' in df_meta.columns:
                        m = df_meta[df_meta['PLAYER_NAME'] == p_name]
                        if not m.empty:
                            img_url = m.iloc[0].get('IMAGEDATAURL')
                    
                    if img_url and str(img_url).startswith('http'):
                        st.image(img_url, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150/f1f1f1/888888?text=NO+PHOTO", use_container_width=True)

                    st.markdown("<hr style='margin:10px 0; border:1px solid #eee'>", unsafe_allow_html=True)

                    for label, names in target_metrics.items():
                        found_col = next((c for c in names if c in df_hold.columns), None)
                        val_display, percent = "-", 0
                        
                        if found_col:
                            val = float(row[found_col])
                            if val > 0:
                                val_display = f"{val:.1f}"
                                max_v = float(df_hold[found_col].max())
                                percent = min(int((val / max_v) * 100), 100) if max_v > 0 else 0

                        st.markdown(f"""
                            <div style="font-size: 9px; color: #666; margin-top: 5px; text-transform: uppercase;">{label}</div>
                            <div style="background-color: #eee; height: 5px; width: 100%; border-radius: 2px;">
                                <div style="background-color: #df003b; height: 5px; width: {percent}%; border-radius: 2px;"></div>
                            </div>
                            <div style="font-size: 10px; text-align: right; font-weight: bold;">{val_display}</div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Kritisk fejl: {e}")
