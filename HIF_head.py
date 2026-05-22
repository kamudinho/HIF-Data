import streamlit as st
import pandas as pd
import numpy as np
import re
from data.data_load import _get_snowflake_conn

# --- CSS TIL STYLING AF BOKSE (DARK MODE & RADIUS) ---
def apply_custom_style():
    st.markdown("""
        <style>
            /* Skjul standard header */
            [data-testid="stHeaderBlockContainer"] h1 { display: none; }
            
            /* Baggrund og containere */
            .stApp { background-color: #0e1117; }
            
            /* Custom boks-styling */
            .custom-card {
                background-color: #1c1c1e;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 10px;
                border: 1px solid #2c2c2e;
            }
            
            .card-title {
                color: #ffffff;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 15px;
            }
            
            /* Form-ikoner (Ligesom på billedet) */
            .form-container {
                display: flex;
                gap: 10px;
                justify-content: space-between;
            }
            
            .form-item {
                text-align: center;
                flex: 1;
            }
            
            .result-box {
                border-radius: 8px;
                padding: 4px 8px;
                font-weight: bold;
                color: white;
                font-size: 14px;
                margin-bottom: 8px;
            }
            
            .win { background-color: #1db954; }
            .loss { background-color: #e94444; }
            .draw { background-color: #727274; }
            
            .opp-logo {
                width: 30px;
                height: 30px;
                object-fit: contain;
                filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.5));
            }
        </style>
    """, unsafe_allow_html=True)

def vis_side(dp=None):
    apply_custom_style()
    
    conn = _get_snowflake_conn()
    if not conn: return

    # --- CONFIG ---
    DB = "KLUB_HVIDOVREIF.AXIS"
    LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
    HIF_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"   

    # --- DATA LOAD ---
    sql = f"SELECT * FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    if df_matches is None or df_matches.empty: return

    df_matches.columns = [str(c).upper() for c in df_matches.columns]
    hif_id = str(HIF_UUID).strip().lower()
    df_matches['MATCH_DATE_FULL'] = pd.to_datetime(df_matches['MATCH_DATE_FULL'], errors='coerce')
    
    # --- LAYOUT ---
    st.markdown("<h2 style='color: white; margin-bottom: 20px;'>Hvidovre IF Dashboard</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1.2])

    # MODUL: NÆSTE KAMP (Højre boks i dit billede)
    with col2:
        hif_m = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'].str.lower() == hif_id) | (df_matches['CONTESTANTAWAY_OPTAUUID'].str.lower() == hif_id)].copy()
        future = hif_m[~hif_m['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False)].sort_values('MATCH_DATE_FULL')
        
        if not future.empty:
            nk = future.iloc[0]
            dato = nk['MATCH_DATE_FULL'].strftime('%d. maj')
            kl = "15.00" # Eller hent fra data hvis tilgængelig
            
            st.markdown(f"""
                <div class="custom-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <span style="color: #8e8e93; font-size: 14px;">Næste kamp</span>
                        <span style="color: #8e8e93; font-size: 14px;">1. Division Oprykningsgruppe</span>
                    </div>
                    <div style="display: flex; justify-content: space-around; align-items: center; text-align: center;">
                        <div>
                            <img src="https://upload.wikimedia.org/wikipedia/da/thumb/6/62/Hvidovre_IF_logo.svg/1200px-Hvidovre_IF_logo.svg.png" style="width: 50px;"><br>
                            <p style="color: white; margin-top: 10px;">Hvidovre</p>
                        </div>
                        <div>
                            <h2 style="color: white; margin: 0;">{kl}</h2>
                            <p style="color: #8e8e93; font-size: 14px;">{dato}</p>
                        </div>
                        <div>
                            <img src="https://upload.wikimedia.org/wikipedia/da/thumb/0/07/Esbjerg_fB_logo.svg/1200px-Esbjerg_fB_logo.svg.png" style="width: 50px;"><br>
                            <p style="color: white; margin-top: 10px;">{nk['CONTESTANTAWAY_NAME'] if nk['CONTESTANTHOME_OPTAUUID'].str.lower() == hif_id else nk['CONTESTANTHOME_NAME']}</p>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # MODUL: HOLDFORM (Venstre boks i dit billede)
    with col1:
        st.markdown('<div class="custom-card"><div class="card-title">Holdform</div>', unsafe_allow_html=True)
        
        # Her henter vi de seneste 5 kampe for HIF
        played = hif_m[hif_m['MATCH_STATUS'].str.upper().str.contains('PLAY|FULL|FINISH|FT', na=False)].sort_values('MATCH_DATE_FULL', ascending=False).head(5)
        
        if not played.empty:
            cols_html = ""
            for _, m in played.iloc[::-1].iterrows():
                is_home = m['CONTESTANTHOME_OPTAUUID'].str.lower() == hif_id
                h_s, a_s = int(m['TOTAL_HOME_SCORE']), int(m['TOTAL_AWAY_SCORE'])
                
                # Resultat farve
                if h_s == a_s: res_class = "draw"
                elif (is_home and h_s > a_s) or (not is_home and a_s > h_s): res_class = "win"
                else: res_class = "loss"
                
                # Her skal du bruge dine egne logo-URL'er eller stien til dem
                opp_logo = "https://via.placeholder.com/30" # Placeholder
                
                cols_html += f"""
                    <div class="form-item">
                        <div class="result-box {res_class}">{h_s} - {a_s}</div>
                        <img src="{opp_logo}" class="opp-logo">
                    </div>
                """
            
            st.markdown(f'<div class="form-container">{cols_html}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
