import streamlit as st
import pandas as pd
import data.HIF_load as hif_load

def vis_side():
    st.markdown("<h2 style='text-align: center; color: #1DB954;'>EXPLOSIVE PHYSICAL PROFILES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-top: -15px;'>NordicBet Liga 2025/2026</p>", unsafe_allow_html=True)
    
    try:
        # 1. DATA INDLÆSNING
        dp = hif_load.get_scouting_package()
        
        # Prøv alle mulige kilder til fysisk data
        df_stats = dp.get("physical", dp.get("players", dp.get("advanced_stats", pd.DataFrame())))
        df_meta = dp.get("sql_players", pd.DataFrame())

        if df_stats.empty:
            st.error("Kunne ikke finde statistik-data i systemet.")
            return

        # Rens kolonnenavne (STORE bogstaver)
        df_stats.columns = [c.upper() for c in df_stats.columns]
        if not df_meta.empty:
            df_meta.columns = [c.upper() for c in df_meta.columns]

        # 2. FIND HOLD-KOLONNE
        team_col = next((c for c in df_stats.columns if 'TEAM' in c or 'HOLD' in c), None)
        if not team_col:
            st.warning("Hold-kolonne ikke fundet.")
            return

        hold_liste = sorted([str(x) for x in df_stats[team_col].unique() if pd.notnull(x)])
        valgt_hold = st.selectbox("Vælg Hold til analyse", options=hold_liste)
        
        if valgt_hold:
            df_hold = df_stats[df_stats[team_col] == valgt_hold].copy()

            # 3. RENS DATA & FIND SPILLERE
            # Tving PLAYER_NAME til string og rens for tal-fejl
            name_col = 'PLAYER_NAME' if 'PLAYER_NAME' in df_hold.columns else next((c for c in df_hold.columns if 'PLAYER' in c or 'NAVN' in c), None)
            
            if name_col:
                df_hold[name_col] = df_hold[name_col].astype(str)
                # Vi finder de 5 mest 'aktive' baseret på hvad vi har af tal
                num_cols = df_hold.select_dtypes(include=['number']).columns
                df_hold['TOTAL_SCORE'] = df_hold[num_cols].sum(axis=1)
                top_5 = df_hold.sort_values(by='TOTAL_SCORE', ascending=False).head(5)
            else:
                st.error("Kunne ikke finde kolonnen med spillernavne.")
                return

            # 4. DEFINER METRICS (Matcher dit billede)
            # Vi tilføjer flere mulige navne for hver stat
            metrics_sections = {
                "Volume Metrics": {
                    "Distance P90": ["DISTANCE", "TOT_DIST", "DISTANCE_P90"],
                    "Avg Meters/Min": ["METERS_PER_MIN", "M_MIN", "INTENSITY_AVG"],
                },
                "High Intensity Metrics": {
                    "Hi Distance P90": ["HI_DISTANCE", "HSR_DIST", "HIGH_INTENSITY_DISTANCE"],
                    "Sprint Distance": ["SPRINT_DISTANCE", "SPRINT_DIST"],
                    "Sprints P90": ["SPRINT_COUNT", "SPRINTS", "SPRINT_NUM"],
                },
                "Explosive Metrics": {
                    "Accels/Decels": ["ACCELERATIONS", "ACC_DEC", "ACCELS"],
                    "Avg Max Speed": ["MAX_SPEED", "TOP_SPEED", "V_MAX"],
                }
            }

            # 5. GRID VISNING
            cols = st.columns(5)
            
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    p_name = row[name_col]
                    efternavn = p_name.split()[-1].upper() if " " in p_name else p_name.upper()
                    
                    # Billede
                    img_url = None
                    if not df_meta.empty and 'PLAYER_NAME' in df_meta.columns:
                        m = df_meta[df_meta['PLAYER_NAME'] == p_name]
                        if not m.empty:
                            img_url = m.iloc[0].get('IMAGEDATAURL')
                    
                    st.image(img_url if img_url else "https://via.placeholder.com/150", use_container_width=True)
                    st.markdown(f"<div style='text-align: center; font-weight: bold; font-size: 14px;'>{efternavn}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align: center; font-size: 10px; color: gray;'>{p_name}</div>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

                    for section, metrics in metrics_sections.items():
                        st.markdown(f"<p style='font-size: 10px; font-weight: bold; color: #1DB954; margin-bottom: 2px;'>{section}</p>", unsafe_allow_html=True)
                        
                        for label, col_names in metrics.items():
                            # Find den første kolonne der matcher
                            found_col = next((c for c in col_names if c in df_hold.columns), None)
                            
                            val_display, percent = "-", 0
                            if found_col:
                                val = pd.to_numeric(row[found_col], errors='coerce')
                                if pd.notnull(val) and val > 0:
                                    max_v = df_hold[found_col].max()
                                    percent = min(int((val / max_v) * 100), 100) if max_v > 0 else 0
                                    val_display = f"{val:.1f}"

                            st.markdown(f"""
                                <div style='display: flex; align-items: center; margin-bottom: 4px;'>
                                    <div style='background-color: #f1f1f1; height: 6px; flex-grow: 1; border-radius: 2px;'>
                                        <div style='background-color: #ff4b4b; width: {percent}%; height: 6px; border-radius: 2px;'></div>
                                    </div>
                                    <span style='font-size: 10px; margin-left: 5px; font-weight: bold;'>{val_display}</span>
                                </div>
                            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Fejl: {e}")
