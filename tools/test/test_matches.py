import streamlit as st
import pandas as pd
from datetime import datetime
from data.utils.stattype_map import STAT_TYPE_MAP

def format_score(val):
    """Sikrer at NaN eller tomme værdier bliver blanke, og floats bliver til pæne heltal."""
    if pd.isna(val) or val == "": 
        return ""
    try: 
        return str(int(float(val)))
    except: 
        return ""

def vis_side(data_package):
    st.subheader("KAMPOVERSIGT")
    
    df_matches = data_package.get("opta_matches")
    df_stats = data_package.get("opta_stats")
    
    if df_matches is None or df_matches.empty:
        st.warning("Ingen kampdata fundet i 'opta_matches'.")
        return

    try:
        # Forbered data
        df = df_matches.copy()
        df.columns = [c.upper() for c in df.columns]
        df['HAR_RESULTAT'] = df['TOTAL_HOME_SCORE'].notna()

        # --- KONTROLPANEL (3 KOLONNER I SAMME HØJDE) ---
        # Vi bruger vertical_alignment="bottom" så popover og radio flugter med dropdown
        col1, col2, col3 = st.columns([1.5, 1, 1], vertical_alignment="bottom")

        with col1:
            # 1. VALG AF HOLD (Dropdown)
            liga_hold = sorted(list(set(df['CONTESTANTHOME_NAME'].dropna()) | set(df['CONTESTANTAWAY_NAME'].dropna())))
            valgt_hold = st.selectbox("Vælg hold:", ["Alle hold"] + liga_hold)

        # Vi skal kende 'visning' for at vide om popover skal vises, 
        # men 'visning' vælges i col3. Derfor definerer vi den lige herunder.
        
        with col3:
            # 3. STATUS (Radio)
            visning = st.radio("Vis:", ["Spillede", "Kommende"], horizontal=True)

        with col2:
            # 2. KOLONNE-VÆLGER (Popover) - Placeret i midten som ønsket
            vis_stats = []
            if valgt_hold != "Alle hold" and visning == "Spillede":
                with st.popover("⚙️ Filter", use_container_width=True):
                    st.write("Vælg statistikker:")
                    for raw_key, dan_name in STAT_TYPE_MAP.items():
                        # Standard-markér de første 5 for brugervenlighed
                        is_default = dan_name in ["Mål", "Assists", "Skud på mål", "Besiddelse %"]
                        if st.checkbox(dan_name, value=is_default, key=f"filter_{raw_key}"):
                            vis_stats.append(dan_name)
            else:
                st.write("") # Pladsholder

        st.markdown("---")

        # --- FILTRERING OG SORTERING ---
        if visning == "Spillede":
            df = df[df['HAR_RESULTAT'] == True]
        else:
            df = df[df['HAR_RESULTAT'] == False]

        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE', 'DATO'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            # Nyeste først for spillede, ældste først for kommende
            df = df.sort_values(by=dato_col, ascending=(visning == "Kommende"))

        # Basis kolonner
        df['KAMP'] = df['CONTESTANTHOME_NAME'].astype(str) + " - " + df['CONTESTANTAWAY_NAME'].astype(str)
        df['RESULTAT'] = df.apply(lambda r: f"{format_score(r.get('TOTAL_HOME_SCORE'))} - {format_score(r.get('TOTAL_AWAY_SCORE'))}" if r['HAR_RESULTAT'] else "-", axis=1)
        df['DATO_STR'] = df[dato_col].dt.strftime('%d-%m-%Y') if dato_col else ""

        # --- VISNING AF TABEL ---
        if valgt_hold == "Alle hold":
            st.dataframe(df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)
        else:
            f_df = df[(df['CONTESTANTHOME_NAME'] == valgt_hold) | (df['CONTESTANTAWAY_NAME'] == valgt_hold)].copy()
            
            # Hvis vi har dybe stats og viser spillede kampe
            if not df_stats.empty and visning == "Spillede" and vis_stats:
                ds = df_stats.copy()
                ds.columns = [c.upper() for c in ds.columns]
                
                match_list = []
                for _, m in f_df.iterrows():
                    m_id = m.get('MATCH_OPTAUUID')
                    is_home = m['CONTESTANTHOME_NAME'] == valgt_hold
                    t_id = m.get('CONTESTANTHOME_OPTAUUID') if is_home else m.get('CONTESTANTAWAY_OPTAUUID')
                    
                    row = {"Dato": m['DATO_STR'], "Kamp": m['KAMP'], "Resultat": m['RESULTAT']}
                    
                    # Match stats for den specifikke kamp og det valgte hold
                    m_s = ds[(ds['MATCH_OPTAUUID'] == m_id) & (ds['CONTESTANT_OPTAUUID'] == t_id)]
                    
                    for _, s_row in m_s.iterrows():
                        raw_stat = s_row['STAT_TYPE']
                        if raw_stat in STAT_TYPE_MAP:
                            dan_stat_name = STAT_TYPE_MAP[raw_stat]
                            if dan_stat_name in vis_stats:
                                row[dan_stat_name] = s_row['STAT_TOTAL']
                    
                    match_list.append(row)

                final_df = pd.DataFrame(match_list)
                st.dataframe(final_df, use_container_width=True, hide_index=True)
            else:
                # Standard visning hvis ingen stats er valgt eller det er kommende kampe
                st.dataframe(f_df[['DATO_STR', 'KAMP', 'RESULTAT']], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Fejl i visning af kampoversigt: {e}")
