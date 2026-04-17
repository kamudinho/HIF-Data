import streamlit as st
import pandas as pd
import data.HIF_load as hif_load

def vis_side():
    st.markdown("<h2 style='text-align: center;'>PHYSICAL PERFORMANCE PROFILES</h2>", unsafe_allow_html=True)
    
    try:
        dp = hif_load.get_scouting_package()
        df = dp.get("players", dp.get("advanced_stats", pd.DataFrame()))
        df_meta = dp.get("sql_players", pd.DataFrame())

        if df.empty:
            st.error("Ingen data fundet.")
            return

        df.columns = [c.upper() for c in df.columns]

        # DEBUG: Se hvad vi har at arbejde med (fjern denne linje når det virker)
        # st.write("Tilgængelige kolonner:", df.columns.tolist())

        # 1. FIND NAVNE-KOLONNE (Vi undgår 'WY_ID', 'PLAYER_ID' etc.)
        name_col = next((c for c in df.columns if 'NAME' in c and 'ID' not in c), 
                        next((c for c in df.columns if 'PLAYER' in c and 'ID' not in c), None))
        
        team_col = next((c for c in df.columns if 'TEAM' in c or 'HOLD' in c), None)

        if not name_col:
            st.warning("Kunne ikke finde en kolonne med navne. Bruger ID i stedet.")
            name_col = df.columns[0]

        hold_liste = sorted([str(x) for x in df[team_col].unique() if pd.notnull(x)])
        valgt_hold = st.selectbox("VÆLG HOLD", options=hold_liste)

        if valgt_hold:
            df_hold = df[df[team_col] == valgt_hold].copy()

            # 2. AUTOMATISK DETECTION AF PHYSICAL STATS
            # Vi leder efter alt der minder om de fire kategorier
            search_map = {
                "Distance": ["DIST", "METER", "KM", "COVERED"],
                "Sprints": ["SPRINT", "HI_RUN", "HSR", "HIGH_INT"],
                "Speed": ["SPEED", "MAX", "VMAX", "FAST"],
                "Accels": ["ACC", "EXPLOSIVE", "DECEL"]
            }
            
            found_metrics = {}
            for label, keys in search_map.items():
                found_metrics[label] = next((c for c in df_hold.columns if any(k in c for k in keys) and c != name_col), None)

            # Tving numerisk og find Top 5
            for col in df_hold.columns:
                if col != name_col:
                    df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0.0)

            # Sorter efter den bedste fundne metric (Distance)
            sort_col = found_metrics["Distance"] if found_metrics["Distance"] else df_hold.select_dtypes(include='number').columns[0]
            top_5 = df_hold.sort_values(sort_col, ascending=False).head(5)

            # 3. VISNING
            cols = st.columns(5)
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    raw_name = str(row[name_col])
                    
                    # Forsøg at matche med meta for rigtigt navn og billede
                    display_name = raw_name
                    img_url = None
                    if not df_meta.empty:
                        # Matcher på tværs af meta-data
                        meta_match = df_meta[df_meta.astype(str).eq(raw_name).any(axis=1)]
                        if not meta_match.empty:
                            display_name = meta_match.iloc[0].get('PLAYER_NAME', raw_name)
                            img_url = meta_match.iloc[0].get('IMAGEDATAURL')

                    st.image(img_url if img_url else "https://via.placeholder.com/150", use_container_width=True)
                    
                    # Sort header-bar med efternavn
                    clean_name = display_name.split()[-1].upper() if " " in display_name else display_name.upper()
                    st.markdown(f"<div style='background:black;color:white;text-align:center;font-weight:bold;padding:5px;font-size:12px;'>{clean_name}</div>", unsafe_allow_html=True)
                    st.caption(f"Ref: {display_name}")

                    for label, c_name in found_metrics.items():
                        if c_name:
                            val = float(row[c_name])
                            max_v = df_hold[c_name].max()
                            pct = min(int((val/max_v)*100), 100) if max_v > 0 else 0
                            val_str = f"{val:.1f}"
                        else:
                            pct, val_str = 0, "N/A"

                        st.markdown(f"""
                            <div style='margin-bottom:8px;'>
                                <div style='font-size:9px;color:gray;'>{label}</div>
                                <div style='background:#eee;height:4px;'><div style='background:#df003b;width:{pct}%;height:4px;'></div></div>
                                <div style='font-size:10px;text-align:right;font-weight:bold;'>{val_str}</div>
                            </div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Fejl: {e}")
