import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def vis_side():
    st.markdown("<h2 style='text-align: center; color: #df003b;'>EXPLOSIVE PHYSICAL PROFILES</h2>", unsafe_allow_html=True)
    
    try:
        conn = _get_snowflake_conn()
        
        # 1. FIND DEN RIGTIGE TABEL AUTOMATISK
        # Vi leder efter tabeller der indeholder 'PLAYER' i dit Snowflake-miljø
        tables_df = conn.query("SHOW TABLES")
        potential_tables = tables_df[tables_df['name'].str.contains('PLAYER', case=False)]['name'].tolist()
        
        if not potential_tables:
            st.error("Kunne ikke finde nogen spiller-tabeller i Snowflake. Kontakt admin for tabelnavn.")
            return
            
        # Vi vælger den første tabel der matcher (ofte WYSCOUT_PLAYERS eller lign.)
        tabel_navn = potential_tables[0]
        
        # 2. HENT DATA (Vi bruger dine faste værdier fra instruktionerne)
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
        valgt_hold = st.selectbox("Vælg Hold", options=hold_liste)

        if valgt_hold:
            df_hold = df_all[df_all[team_col] == valgt_hold].copy()

            # Rens alt tal-data (Dræber float/str fejlen)
            for col in df_hold.columns:
                if col not in ['PLAYER_NAME', team_col, 'IMAGEDATAURL']:
                    df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0.0)

            # Find de 5 spillere med mest data (Top Score)
            numeric_cols = df_hold.select_dtypes(include=['number']).columns
            df_hold['SCORE'] = df_hold[numeric_cols].sum(axis=1)
            top_5 = df_hold.sort_values('SCORE', ascending=False).head(5)

            # 4. DEFINER METRICS (Matcher dine kolonner)
            # Vi kigger efter kolonnenavne der indeholder disse ord
            metrics_to_show = {
                "Distance": next((c for c in df_hold.columns if 'DIST' in c), None),
                "Sprints": next((c for c in df_hold.columns if 'SPRINT' in c), None),
                "Speed": next((c for c in df_hold.columns if 'SPEED' in c or 'VMAX' in c), None),
                "Duels": next((c for c in df_hold.columns if 'DUEL' in c), None)
            }

            # 5. GRID VISNING
            cols = st.columns(5)
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    name = str(row.get('PLAYER_NAME', 'Ukendt'))
                    st.markdown(f"<div style='text-align: center; font-weight: bold;'>{name.split()[-1].upper()}</div>", unsafe_allow_html=True)
                    
                    img = row.get('IMAGEDATAURL')
                    st.image(img if img else "https://via.placeholder.com/150", use_container_width=True)
                    st.markdown("<hr style='margin:5px 0;'>", unsafe_allow_html=True)

                    for label, col_name in metrics_to_show.items():
                        val, percent = 0.0, 0
                        if col_name:
                            val = float(row[col_name])
                            max_val = float(df_hold[col_name].max())
                            percent = min(int((val / max_val) * 100), 100) if max_val > 0 else 0

                        st.markdown(f"""
                            <div style='font-size: 9px; color: #666;'>{label}</div>
                            <div style='background-color: #eee; height: 5px; width: 100%; border-radius: 2px;'>
                                <div style='background-color: #df003b; width: {percent}%; height: 5px; border-radius: 2px;'></div>
                            </div>
                            <div style='font-size: 10px; text-align: right; font-weight: bold;'>{val:.1f}</div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"System Fejl: {e}")
        st.info("Prøv at tjekke om du er logget korrekt ind på Snowflake via din Streamlit secrets.")
