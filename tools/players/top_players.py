import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def vis_side():
    # Styling der matcher dit screenshot (Mørkegrå/Hvid kontrast og rød branding)
    st.markdown("""
        <style>
        .player-card { border-radius: 5px; padding: 10px; background-color: white; }
        .stat-label { font-size: 9px; color: #666; text-transform: uppercase; margin-top: 8px; }
        .stat-bar-bg { background-color: #f0f0f0; height: 6px; width: 100%; border-radius: 3px; }
        .stat-bar-fill { background-color: #df003b; height: 6px; border-radius: 3px; }
        .stat-val { font-size: 11px; font-weight: bold; text-align: right; margin-top: 2px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center; color: #1f1f1f; letter-spacing: 2px;'>EXPLOSIVE PHYSICAL PROFILES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; margin-top: -15px;'>NordicBet Liga Analysis | Season 2025/2026</p>", unsafe_allow_html=True)
    
    try:
        conn = _get_snowflake_conn()
        
        # 1. HENT TABEL DYNAMISK
        tables_df = conn.query("SHOW TABLES")
        potential_tables = tables_df[tables_df['name'].str.contains('PLAYER', case=False)]['name'].tolist()
        
        if not potential_tables:
            st.error("Ingen tilgængelige data-tabeller fundet.")
            return
            
        tabel_navn = potential_tables[0]
        
        # 2. DATA QUERY
        query = f"""
            SELECT * FROM {tabel_navn} 
            WHERE SEASONNAME = '2025/2026' 
            AND COMPETITION_WYID IN (328, 335)
        """
        df_all = conn.query(query)
        df_all.columns = [c.upper() for c in df_all.columns]

        # 3. HOLD-VÆLGER
        team_col = next((c for c in df_all.columns if 'TEAM_NAME' in c or 'HOLD' in c), None)
        hold_liste = sorted([str(x) for x in df_all[team_col].unique() if pd.notnull(x)])
        valgt_hold = st.selectbox("VÆLG HOLD TIL ANALYSE", options=hold_liste)

        if valgt_hold:
            df_hold = df_all[df_all[team_col] == valgt_hold].copy()

            # Rens numeriske kolonner
            for col in df_hold.columns:
                if col not in ['PLAYER_NAME', team_col, 'IMAGEDATAURL']:
                    df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0.0)

            # Find Top 5 profiler (baseret på aktivitet/score)
            num_cols = df_hold.select_dtypes(include=['number']).columns
            df_hold['SCORE'] = df_hold[num_cols].sum(axis=1)
            top_5 = df_hold.sort_values('SCORE', ascending=False).head(5)

            # Map metrics til pæne labels (Matcher dit billede)
            metrics_to_show = {
                "Distance P90": next((c for c in df_hold.columns if 'DIST' in c and 'P90' in c), 
                                   next((c for c in df_hold.columns if 'DIST' in c), None)),
                "High Intensity": next((c for c in df_hold.columns if 'HI_' in c or 'HSR' in c), None),
                "Sprints P90": next((c for c in df_hold.columns if 'SPRINT' in c), None),
                "Max Speed": next((c for c in df_hold.columns if 'SPEED' in c or 'VMAX' in c), None)
            }

            # 4. GRID VISNING (5 KOLONNER)
            cols = st.columns(5)
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    name = str(row.get('PLAYER_NAME', 'Ukendt'))
                    efternavn = name.split()[-1].upper() if " " in name else name.upper()
                    
                    # Billede sektion
                    img = row.get('IMAGEDATAURL')
                    if img and str(img).startswith('http'):
                        st.image(img, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150/f4f4f4/666666?text=PROFILE", use_container_width=True)
                    
                    # Navne-bar
                    st.markdown(f"""
                        <div style='background-color: #1f1f1f; color: white; text-align: center; 
                        padding: 5px; font-weight: bold; font-size: 14px; margin-bottom: 10px;'>
                            {efternavn}
                        </div>
                    """, unsafe_allow_html=True)

                    # Metrics bars
                    for label, col_name in metrics_to_show.items():
                        val, percent = 0.0, 0
                        if col_name:
                            val = float(row[col_name])
                            max_val = float(df_hold[col_name].max())
                            percent = min(int((val / max_val) * 100), 100) if max_val > 0 else 0

                        st.markdown(f"""
                            <div class="stat-label">{label}</div>
                            <div class="stat-bar-bg">
                                <div class="stat-bar-fill" style="width: {percent}%;"></div>
                            </div>
                            <div class="stat-val">{val:.1f}</div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"System Fejl: {e}")
