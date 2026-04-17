import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def vis_side():
    st.markdown("<h2 style='text-align: center; color: #1f1f1f;'>EXPLOSIVE PHYSICAL PROFILES</h2>", unsafe_allow_html=True)
    
    try:
        conn = _get_snowflake_conn()
        
        # 1. HENT DATA DIREKTE (Vi bruger de filtre du har oplyst)
        # Jeg har fjernet 'SHOW TABLES' for at undgå den ukendte fejl
        query = """
            SELECT * FROM WYSCOUT_PLAYERS 
            WHERE SEASONNAME = '2025/2026' 
            AND COMPETITION_WYID IN (328, 335)
        """
        
        # Hvis 'WYSCOUT_PLAYERS' ikke er det rigtige navn, så tjek din 'data/HIF_load.py'
        # og se hvad tabellen hedder der.
        try:
            df_all = conn.query(query)
        except:
            # Backup: Hvis tabellen ovenfor ikke findes, prøver vi en generel query
            df_all = conn.query("SELECT * FROM PLAYERS WHERE SEASONNAME = '2025/2026' LIMIT 1000")

        if df_all is None or df_all.empty:
            st.warning("Kunne ikke hente data. Tjek venligst om tabelnavnet i SQL-forespørgslen er korrekt.")
            return

        df_all.columns = [c.upper() for c in df_all.columns]

        # 2. FIND DE RIGTIGE KOLONNER
        team_col = next((c for c in df_all.columns if 'TEAM' in c or 'HOLD' in c), None)
        name_col = next((c for c in df_all.columns if 'PLAYER_NAME' in c or 'NAVN' in c), None)
        
        if not team_col or not name_col:
            st.error("Kunne ikke finde hold- eller spiller-kolonner.")
            return

        hold_liste = sorted([str(x) for x in df_all[team_col].unique() if pd.notnull(x)])
        valgt_hold = st.selectbox("VÆLG HOLD", options=hold_liste)

        if valgt_hold:
            df_hold = df_all[df_all[team_col] == valgt_hold].copy()

            # Rens numeriske data (Dræber float/str fejl)
            for col in df_hold.columns:
                if col not in [name_col, team_col, 'IMAGEDATAURL']:
                    df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0.0)

            # Find Top 5 (Sorteret efter Distance eller lignende stabil stat)
            sort_col = next((c for c in df_hold.columns if 'DIST' in c), df_hold.columns[-1])
            top_5 = df_hold.sort_values(sort_col, ascending=False).head(5)

            # 3. VISNING
            cols = st.columns(5)
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    name = str(row[name_col])
                    # Efternavn i sort bar
                    st.markdown(f"<div style='background:black;color:white;text-align:center;font-weight:bold;padding:5px;font-size:12px;'>{name.split()[-1].upper()}</div>", unsafe_allow_html=True)
                    
                    img = row.get('IMAGEDATAURL')
                    st.image(img if img else "https://via.placeholder.com/150", use_container_width=True)

                    # Barer for de vigtigste stats
                    metrics = {"Distance": "DIST", "Sprint": "SPRINT", "Speed": "SPEED"}
                    for label, key in metrics.items():
                        c_name = next((c for c in df_hold.columns if key in c), None)
                        if c_name:
                            val = float(row[c_name])
                            max_v = df_hold[c_name].max()
                            pct = min(int((val/max_v)*100), 100) if max_v > 0 else 0
                            st.markdown(f"""
                                <div style='font-size:9px;color:gray;margin-top:5px;'>{label}</div>
                                <div style='background:#eee;height:4px;border-radius:2px;'>
                                    <div style='background:#df003b;width:{pct}%;height:4px;border-radius:2px;'></div>
                                </div>
                                <div style='font-size:10px;text-align:right;font-weight:bold;'>{val:.1f}</div>
                            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Der opstod en fejl: {str(e)}")
