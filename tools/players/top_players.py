import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
import traceback

def vis_side():
    st.markdown("<h2 style='text-align: center; color: #1f1f1f;'>EXPLOSIVE PHYSICAL PROFILES</h2>", unsafe_allow_html=True)
    
    try:
        # 1. FORBINDELSE
        conn = _get_snowflake_conn()
        
        # 2. HENT TABELLER (Med ekstra fejlhåndtering)
        try:
            tables_df = conn.query("SHOW TABLES")
            if tables_df is None or tables_df.empty:
                st.error("Ingen tabeller fundet i Snowflake. Tjek dine rettigheder.")
                return
            
            # Find tabel med 'PLAYER' i navnet
            potential_tables = tables_df[tables_df['name'].str.contains('PLAYER', case=False)]['name'].tolist()
            if not potential_tables:
                st.warning("Fandt ingen tabeller med 'PLAYER' i navnet. Viser alle tilgængelige:")
                st.write(tables_df['name'].tolist())
                return
            
            tabel_navn = potential_tables[0]
        except Exception as e:
            st.error(f"Fejl ved opslag af tabeller: {e}")
            return

        # 3. HENT DATA
        # Vi bruger 'TRY' her for at fange SQL-fejl specifikt
        try:
            query = f"""
                SELECT * FROM {tabel_navn} 
                WHERE SEASONNAME = '2025/2026' 
                AND COMPETITION_WYID IN (328, 335)
            """
            df_all = conn.query(query)
        except Exception as e:
            st.error(f"SQL Fejl i tabel '{tabel_navn}': {e}")
            return

        if df_all is None or df_all.empty:
            st.info(f"Tabellen '{tabel_navn}' er tom eller matcher ikke filtrene (Season 25/26, ID 328/335).")
            return

        df_all.columns = [c.upper() for c in df_all.columns]

        # 4. HOLD-VÆLGER
        team_col = next((c for c in df_all.columns if 'TEAM_NAME' in c or 'HOLD' in c), None)
        if not team_col:
            st.error("Kunne ikke finde en kolonne til holdnavne. Kolonner i tabellen:")
            st.write(df_all.columns.tolist())
            return

        hold_liste = sorted([str(x) for x in df_all[team_col].unique() if pd.notnull(x)])
        valgt_hold = st.selectbox("VÆLG HOLD", options=hold_liste)

        if valgt_hold:
            df_hold = df_all[df_all[team_col] == valgt_hold].copy()

            # Rens numeriske data
            for col in df_hold.columns:
                if col not in ['PLAYER_NAME', team_col, 'IMAGEDATAURL']:
                    df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0.0)

            # Find Top 5
            numeric_cols = df_hold.select_dtypes(include=['number']).columns
            df_hold['SCORE'] = df_hold[numeric_cols].sum(axis=1)
            top_5 = df_hold.sort_values('SCORE', ascending=False).head(5)

            # 5. GRID VISNING (Kompakt stil)
            cols = st.columns(5)
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    name = str(row.get('PLAYER_NAME', 'Ukendt'))
                    img = row.get('IMAGEDATAURL')
                    
                    if img and str(img).startswith('http'):
                        st.image(img, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150", use_container_width=True)
                    
                    st.markdown(f"<div style='background:black;color:white;text-align:center;font-weight:bold;padding:3px;'>{name.split()[-1].upper()}</div>", unsafe_allow_html=True)

                    # Simpel bar-logik for test
                    for label, col_part in {"Dist": "DIST", "Sprint": "SPRINT", "Speed": "SPEED"}.items():
                        col_name = next((c for c in df_hold.columns if col_part in c), None)
                        if col_name:
                            val = float(row[col_name])
                            max_v = df_hold[col_name].max()
                            pct = min(int((val/max_v)*100), 100) if max_v > 0 else 0
                            st.markdown(f"""
                                <div style='font-size:9px;margin-top:5px;'>{label}</div>
                                <div style='background:#eee;height:4px;'><div style='background:#df003b;width:{pct}%;height:4px;'></div></div>
                                <div style='font-size:10px;text-align:right;'>{val:.1f}</div>
                            """, unsafe_allow_html=True)

    except Exception as e:
        # DETTE ER DEBUG-SEKTIONEN:
        st.error("--- KRITISK DEBUG INFO ---")
        st.write(f"Fejltype: {type(e).__name__}")
        st.write(f"Fejlbesked: {e}")
        st.text(traceback.format_exc()) # Viser præcis hvor i koden det går galt
