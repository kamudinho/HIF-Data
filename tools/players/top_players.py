import streamlit as st
import pandas as pd
import data.HIF_load as hif_load

def vis_side():
    # Overskrift der matcher dit billede
    st.markdown("<h2 style='text-align: center; color: #1DB954;'>EXPLOSIVE PHYSICAL PROFILES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-top: -15px;'>NordicBet Liga 2025/2026</p>", unsafe_allow_html=True)
    
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

        # Normaliser kolonnenavne
        df_stats.columns = [c.upper() for c in df_stats.columns]
        if not df_meta.empty:
            df_meta.columns = [c.upper() for c in df_meta.columns]

        # 2. SIKKER HOLD-VÆLGER (Undgår float/str fejl i sortering af holdnavne)
        team_col = next((c for c in df_stats.columns if 'TEAM' in c or 'HOLD' in c), None)
        if not team_col:
            st.warning("Hold-kolonne ikke fundet.")
            return

        # Vi renser holdlisten for None/tal for at kunne sortere den alfabetisk som tekst
        hold_liste = sorted([str(x) for x in df_stats[team_col].unique() if pd.notnull(x)])
        valgt_hold = st.selectbox("Vælg Hold til analyse", options=hold_liste)
        
        if valgt_hold:
            df_hold = df_stats[df_stats[team_col] == valgt_hold].copy()

            # 3. RENS DATA (Nuklear løsning mod float/str fejl)
            if 'PLAYER_NAME' in df_hold.columns:
                df_hold['PLAYER_NAME'] = df_hold['PLAYER_NAME'].astype(str)

            for col in df_hold.columns:
                if col not in ['PLAYER_NAME', team_col]:
                    df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0.0).astype(float)

            # Beregn samlet score for at finde de 5 vigtigste profiler
            numeric_cols = df_hold.select_dtypes(include=['number']).columns
            df_hold['TOTAL_SCORE'] = df_hold[numeric_cols].sum(axis=1)
            top_5 = df_hold.sort_values(by='TOTAL_SCORE', ascending=False).head(5)

            # 4. DEFINER METRICS (Matcher kategorierne i dit billede)
            # Vi bruger her typiske navne - ret dem hvis dine kolonner hedder noget andet
            metrics_sections = {
                "Volume Metrics": {
                    "Distance P90": ["DISTANCE", "TOTAL_DISTANCE"],
                    "Avg Meters/Min": ["METERS_PER_MIN", "AVG_METERS_MIN"],
                },
                "High Intensity Metrics": {
                    "Hi Distance P90": ["HI_DISTANCE", "HSR_DISTANCE"],
                    "Sprint Distance": ["SPRINT_DISTANCE"],
                    "Sprints P90": ["SPRINT_COUNT", "SPRINTS"],
                },
                "Explosive Metrics": {
                    "Accels/Decels": ["ACCELERATIONS", "DECELERATIONS"],
                    "Avg Max Speed": ["MAX_SPEED", "TOP_SPEED"],
                }
            }

            # 5. GRID VISNING (7 kolonner ligesom i billedet, vi bruger 5 til top spillere)
            cols = st.columns(len(top_5))
            
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    p_name = str(row.get('PLAYER_NAME', 'Ukendt'))
                    
                    # Spillerbillede match
                    img_url = None
                    if not df_meta.empty and 'PLAYER_NAME' in df_meta.columns:
                        m = df_meta[df_meta['PLAYER_NAME'] == p_name]
                        if not m.empty:
                            img_url = m.iloc[0].get('IMAGEDATAURL')
                    
                    # Visning af hoved og navn
                    if img_url and str(img_url).startswith('http'):
                        st.image(img_url, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150/f1f1f1/888888?text=FOTO", use_container_width=True)
                    
                    st.markdown(f"<div style='text-align: center; font-weight: bold;'>{p_name.split()[-1].upper()}</div>", unsafe_allow_html=True)
                    st.markdown("<hr style='margin:5px 0;'>", unsafe_allow_html=True)

                    # Tegn de forskellige sektioner af stats
                    for section, metrics in metrics_sections.items():
                        st.markdown(f"<p style='font-size: 10px; font-weight: bold; color: #555; margin-bottom: 2px;'>{section}</p>", unsafe_allow_html=True)
                        
                        for label, col_names in metrics.items():
                            found_col = next((c for c in col_names if c in df_hold.columns), None)
                            val_display, percent = "-", 0
                            
                            if found_col:
                                val = float(row[found_col])
                                if val > 0:
                                    # Vi bruger holdets max til at definere baren (ligesom rank i dit billede)
                                    max_v = float(df_hold[found_col].max())
                                    percent = min(int((val / max_v) * 100), 100) if max_v > 0 else 0
                                    val_display = f"{val:.1f}"

                            # HTML Bar (rød/pink ligesom i dit screenshot)
                            st.markdown(f"""
                                <div style='display: flex; align-items: center; margin-bottom: 4px;'>
                                    <div style='background-color: #eee; height: 8px; flex-grow: 1; border-radius: 2px; position: relative;'>
                                        <div style='background-color: #ff8a8a; width: {percent}%; height: 8px; border-radius: 2px;'></div>
                                    </div>
                                    <span style='font-size: 10px; margin-left: 5px; min-width: 25px; text-align: right;'>{val_display}</span>
                                </div>
                            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Kritisk fejl i visning: {e}")
