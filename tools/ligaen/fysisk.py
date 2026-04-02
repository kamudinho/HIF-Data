import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(df):
    if df is None or df.empty:
        st.error("Ingen fysiske data fundet.")
        return

    st.subheader("Fysisk Data & Tracking")

    # --- 1. DATA PROCESSERING ---
    df_phys = df.copy()
    
    # Sørg for at kolonnenavne er konsistente (Upper case)
    df_phys.columns = [str(c).strip().upper() for c in df_phys.columns]

    # --- 2. OMREGNINGER ---
    
    # Omregn MIN_SEC (sekunder) til Minutter:Sekunder format
    if 'MIN_SEC' in df_phys.columns:
        def format_tid(total_sekunder):
            try:
                val = float(total_sekunder)
                mins = int(val // 60)
                secs = int(val % 60)
                return f"{mins}:{secs:02d}"
            except:
                return "0:00"
        
        df_phys['SPILLETID'] = df_phys['MIN_SEC'].apply(format_tid)

    # Omregn DISTANCE (meter) til Kilometer (KM)
    if 'DISTANCE' in df_phys.columns:
        df_phys['DISTANCE_KM'] = (pd.to_numeric(df_phys['DISTANCE'], errors='coerce') / 1000).round(2)
    
    # --- 3. VISNING AF TABEL ---
    
    # Vi vælger de vigtigste kolonner til fremvisning
    # Tilpas listen herunder hvis du har andre specifikke kolonner (f.eks. HSR, SPRINT)
    cols_to_show = ['NAVN']
    if 'SPILLETID' in df_phys.columns: cols_to_show.append('SPILLETID')
    if 'DISTANCE_KM' in df_phys.columns: cols_to_show.append('DISTANCE_KM')
    
    # Find alle andre relevante kolonner der findes i dit ark
    for extra in ['HSR', 'SPRINT', 'ACC', 'DEC']:
        if extra in df_phys.columns:
            cols_to_show.append(extra)

    # Filtrer kun de kolonner vi faktisk har fundet
    final_cols = [c for c in cols_to_show if c in df_phys.columns]

    st.dataframe(
        df_phys[final_cols].sort_values(by='DISTANCE_KM', ascending=False if 'DISTANCE_KM' in df_phys.columns else True),
        use_container_width=True,
        hide_index=True,
        column_config={
            "DISTANCE_KM": st.column_config.NumberColumn("Distance (km)", format="%.2f km"),
            "SPILLETID": st.column_config.TextColumn("Tid (min:sek)"),
            "NAVN": "Spiller"
        }
    )

    # --- 4. STATISTIK OVERBLIK ---
    if 'DISTANCE_KM' in df_phys.columns:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Distance", f"{df_phys['DISTANCE_KM'].sum().round(1)} km")
        with c2:
            st.metric("Gns. Distance", f"{df_phys['DISTANCE_KM'].mean().round(2)} km")
        with c3:
            st.metric("Top Distance", f"{df_phys['DISTANCE_KM'].max()} km")
