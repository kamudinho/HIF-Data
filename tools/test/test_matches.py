import streamlit as st
import pandas as pd
from datetime import datetime
from data.utils.stattype_map import STAT_TYPE_MAP

def format_score(val):
    """Håndterer NaN og konverterer floats (2.0) til pæne tekst-heltal (2)."""
    if pd.isna(val) or val == "": 
        return ""
    try: 
        # Konverterer først til float og så int for at fjerne .0
        return str(int(float(val)))
    except: 
        return ""

def vis_side(data_package):
    st.subheader("KAMPOVERSIGT")
    
    # Hent data fra pakken
    df_matches = data_package.get("opta_matches")
    df_stats = data_package.get("opta_stats")
    
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata fundet i 'opta_matches'.")
        return

    try:
        # 1. KLARGØR DATA
        df = df_matches.copy()
        df.columns = [c.upper() for c in df.columns]
        
        # Find dato-kolonnen (Opta bruger ofte MATCH_DATE_FULL)
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE', 'DATO'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])

        # Definer om en kamp er spillet (baseret på om der er en score)
        df['HAR_RESULTAT'] = df['TOTAL_HOME_SCORE'].notna()

        # --- 2. KONTROLPANEL (LAYOUT) ---
        # Vi bruger vertical_alignment="bottom" for at flugte alle elementer
        col1, col2, col3 = st.columns([1.5, 1, 1], vertical_alignment="bottom")

        with col1:
            # Vælg hold først
            liga_hold = sorted(list(set(df['CONTESTANTHOME_NAME'].dropna()) | set(df['CONTESTANTAWAY_NAME'].dropna())))
            valgt_hold = st.selectbox("Vælg hold:", ["Alle hold"] + liga_hold)

        with col3:
            # Status (Spillede vs Kommende) - Dette styrer filtreringen
            visning = st.radio("Vis:", ["Spillede", "Kommende"], horizontal=True)

        with col2:
            # Popover filter (kun relevant for spillede kampe med dybe stats)
            vis_stats = []
            if valgt_hold != "Alle hold" and visning == "Spillede":
                with st.popover("⚙️ Filter", use_container_width=True):
                    st.write("Vælg statistikker:")
                    for raw_key, dan_name in STAT_TYPE_MAP.items():
                        # Standard-valg for at gøre det hurtigt
                        is_default = dan_name in ["Mål", "Assists", "Skud på mål", "xG"]
                        if st.checkbox(dan_name, value=is_default, key=f"f_{raw_key}"):
                            vis_stats.append(dan_name)
            else:
                st.write("") # Pladsholder

        st.markdown("---")

        # --- 3. FILTRERING OG SORTERING ---
        if visning == "Spillede":
            # Vis kun kampe der har et resultat
            display_df = df[df['HAR_RESULTAT'] == True].copy()
            if dato_col:
                display_df = display_df.sort_values(by=dato_col, ascending=False) # Nyeste først
        else:
            # Vis kampe uden resultat (kommende i 2026)
            display_df = df[df['HAR_RESULTAT'] == False].copy()
            if dato_col:
                display_df = display_df.sort_values(by=dato_col, ascending=True) # Nærmeste først

        # Formatering til tabel
        display_df['KAMP'] = display_df['CONTESTANTHOME_NAME'].astype(str) + " - " + display_df['CONTESTANTAWAY_NAME'].astype(str)
        display_df['RESULTAT'] = display_df.apply(lambda r: f"{format_score(r.get('TOTAL_HOME_SCORE'))} - {format_score(r.get('TOTAL_AWAY_SCORE'))}" if r['HAR_RESULTAT'] else "-", axis=1)
        display_df['DATO_STR'] = display_df[dato_col].dt.strftime('%d-%m-%Y') if dato_col else ""

        # --- 4. VISNING AF TABEL ---
        if valgt_hold == "Alle hold":
            st.dataframe(display_df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)
        else:
            # Filtrer specifikt på det valgte hold
            f_df = display_df[(display_df['CONTESTANTHOME_NAME'] == valgt_hold) | (display_df['CONTESTANTAWAY_NAME'] == valgt_hold)].copy()
            
            # Hent dybe Opta stats hvis de findes og vi kigger på spillede kampe
            if not df_stats.empty and visning == "Spillede" and vis_stats:
                ds = df_stats.copy()
                ds.columns = [c.upper() for c in ds.columns]
                
                match_list = []
                for _, m in f_df.iterrows():
                    m_id = m.get('MATCH_OPTAUUID')
                    is_home = m['CONTESTANTHOME_NAME'] == valgt_hold
                    t_id = m.get('CONTESTANTHOME_OPTAUUID') if is_home else m.get('CONTESTANTAWAY_OPTAUUID')
                    
                    row = {"Dato": m['DATO_STR'], "Kamp": m['KAMP'], "Resultat": m['RESULTAT']}
                    
                    # Find stats for denne kamp og dette hold
                    m_s = ds[(ds['MATCH_OPTAUUID'] == m_id) & (ds['CONTESTANT_OPTAUUID'] == t_id)]
                    for _, s_row in m_s.iterrows():
                        raw_stat = s_row['STAT_TYPE']
                        if raw_stat in STAT_TYPE_MAP:
                            dan_name = STAT_TYPE_MAP[raw_stat]
                            if dan_name in vis_stats:
                                row[dan_name] = s_row['STAT_TOTAL']
                    
                    match_list.append(row)

                final_df = pd.DataFrame(match_list)
                st.dataframe(final_df, use_container_width=True, hide_index=True)
            else:
                # Basis-tabel for kommende kampe eller hvis ingen stats er valgt
                st.dataframe(f_df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Fejl i visning: {e}")
