import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def vis_side():
    st.markdown("<h2 style='text-align: center; color: #df003b;'>EXPLOSIVE PHYSICAL PROFILES</h2>", unsafe_allow_html=True)
    
    try:
        # 1. DIREKTE FORBINDELSE TIL SNOWFLAKE
        conn = _get_snowflake_conn()
        
        # Vi henter alle nødvendige data i ét hug
        # RET 'DIN_TABEL_NAVN' til navnet på din tabel i Snowflake (f.eks. WY_DATA eller lign.)
        query = """
            SELECT * FROM DIN_TABEL_NAVN 
            WHERE SEASONNAME = '2025/2026' 
            AND COMPETITION_WYID = 328
        """
        df_all = conn.query(query)

        if df_all.empty:
            st.warning("Ingen data fundet i Snowflake for den valgte sæson/liga.")
            return

        # Sørg for ensartede kolonnenavne
        df_all.columns = [c.upper() for c in df_all.columns]

        # 2. HOLD-VÆLGER
        team_col = 'TEAM_NAME' if 'TEAM_NAME' in df_all.columns else 'HOLD_NAVN'
        hold_liste = sorted(df_all[team_col].unique().tolist())
        valgt_hold = st.selectbox("Vælg Hold", options=hold_liste)

        if valgt_hold:
            df_hold = df_all[df_all[team_col] == valgt_hold].copy()

            # Rens tal-data (vigtigt mod str/float fejlen)
            for col in df_hold.columns:
                if col not in ['PLAYER_NAME', team_col, 'IMAGEDATAURL']:
                    df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0.0)

            # Find top 5 mest aktive (brug en kolonne du ved har høje værdier, f.eks. 'TOUCHES' eller summen)
            num_cols = df_hold.select_dtypes(include=['number']).columns
            df_hold['SCORE'] = df_hold[num_cols].sum(axis=1)
            top_5 = df_hold.sort_values('SCORE', ascending=False).head(5)

            # 3. GRID VISNING
            cols = st.columns(5)
            
            # Definer de metrics du vil vise i barerne
            # Disse skal matche dine kolonnenavne i Snowflake nøjagtigt
            metrics = {
                "Volume": "DISTANCE_P90",
                "Intensity": "HI_DISTANCE_P90",
                "Sprints": "SPRINTS_P90",
                "Speed": "MAX_SPEED"
            }

            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    # Spiller Information
                    name = row.get('PLAYER_NAME', 'Ukendt')
                    st.markdown(f"<div style='text-align: center; font-weight: bold;'>{name.split()[-1].upper()}</div>", unsafe_allow_html=True)
                    
                    # Billede (vi tjekker om URL findes i tabellen)
                    img = row.get('IMAGEDATAURL')
                    if img and str(img).startswith('http'):
                        st.image(img, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/150/f1f1f1/888888?text=NO+IMAGE", use_container_width=True)
                    
                    st.markdown("<hr style='margin:5px 0;'>", unsafe_allow_html=True)

                    # Bar-visning
                    for label, col_name in metrics.items():
                        val = 0.0
                        percent = 0
                        
                        if col_name in df_hold.columns:
                            val = float(row[col_name])
                            max_val = float(df_hold[col_name].max())
                            percent = min(int((val / max_val) * 100), 100) if max_val > 0 else 0

                        st.markdown(f"""
                            <div style='font-size: 10px; color: #666;'>{label}</div>
                            <div style='background-color: #eee; height: 6px; width: 100%; border-radius: 3px;'>
                                <div style='background-color: #df003b; width: {percent}%; height: 6px; border-radius: 3px;'></div>
                            </div>
                            <div style='font-size: 10px; text-align: right; font-weight: bold;'>{val:.1f}</div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Snowflake Fejl: {e}")
