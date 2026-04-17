import streamlit as st
import pandas as pd
import data.HIF_load as hif_load

def vis_side():
    # CSS forbedret til at sikre at tekst og bars altid er synlige
    st.markdown("""
        <style>
        .player-header { background-color: #1f1f1f; color: white; text-align: center; font-weight: bold; padding: 5px; margin-bottom: 10px; border-radius: 2px; font-size: 14px; }
        .stat-box { margin-bottom: 8px; border-bottom: 1px solid #f0f0f0; padding-bottom: 2px; }
        .bar-bg { background-color: #f1f1f1; height: 6px; width: 100%; border-radius: 3px; margin: 2px 0; }
        .bar-fill { background-color: #df003b; height: 6px; border-radius: 3px; transition: width 0.5s; }
        .val-text { font-size: 11px; font-weight: bold; text-align: right; color: #333; }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center; color: #1f1f1f;'>PHYSICAL PERFORMANCE PROFILES</h2>", unsafe_allow_html=True)
    
    try:
        # 1. DATA INDLÆSNING
        dp = hif_load.get_scouting_package()
        df = dp.get("players", pd.DataFrame())
        if df.empty:
            df = dp.get("advanced_stats", pd.DataFrame())
            
        df_meta = dp.get("sql_players", pd.DataFrame())

        if df.empty:
            st.error("Kunne ikke hente data. Tjek hif_load.")
            return

        df.columns = [c.upper() for c in df.columns]
        if not df_meta.empty:
            df_meta.columns = [c.upper() for c in df_meta.columns]

        # 2. FIND DINE FILTRE
        # Identificer spiller- og hold-kolonner dynamisk
        team_col = next((c for c in df.columns if any(x in c for x in ['TEAM', 'HOLD', 'CLUB'])), None)
        name_col = next((c for c in df.columns if any(x in c for x in ['PLAYER', 'NAVN', 'NAME'])), None)

        if not team_col or not name_col:
            st.warning("Data struktur ikke genkendt. Tilgængelige kolonner: " + ", ".join(df.columns[:10]))
            return

        hold_liste = sorted([str(x) for x in df[team_col].unique() if pd.notnull(x)])
        valgt_hold = st.selectbox("VÆLG HOLD", options=hold_liste)

        if valgt_hold:
            df_hold = df[df[team_col] == valgt_hold].copy()

            # 3. IDENTIFICER METRICS (Her fejlede den sandsynligvis før)
            # Vi kigger efter specifikke fysiske nøgleord
            potential_metrics = {
                "Distance": ["DISTANCE", "TOT_DIST", "DIST_P90", "METER"],
                "Sprints": ["SPRINT", "HI_RUN", "HSR", "HIGH_INTENSITY"],
                "Speed": ["SPEED", "MAX_V", "VMAX", "TOP_SPEED"],
                "Accels": ["ACCEL", "DECEL", "ACC_DEC", "EXPLOSIVE"]
            }

            metrics = {}
            for label, keys in potential_metrics.items():
                metrics[label] = next((c for c in df_hold.columns if any(k in c for k in keys)), None)

            # Tving numerisk data
            for col in df_hold.columns:
                if col not in [name_col, team_col, 'IMAGEDATAURL']:
                    df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0.0)

            # Sorter efter Distance eller den første fundne metric
            sort_by = metrics["Distance"] if metrics["Distance"] else df_hold.select_dtypes('number').columns[0]
            top_5 = df_hold.sort_values(sort_by, ascending=False).head(5)

            # 4. GRID VISNING
            cols = st.columns(5)
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    full_name = str(row[name_col])
                    efternavn = full_name.split()[-1].upper() if " " in full_name else full_name.upper()
                    
                    # Billede-match
                    img_url = None
                    if not df_meta.empty and name_col in df_meta.columns:
                        match = df_meta[df_meta[name_col] == full_name]
                        if not match.empty:
                            img_url = match.iloc[0].get('IMAGEDATAURL') or match.iloc[0].get('IMAGEDATAURL_PLAYER')

                    # Visuel Output
                    st.image(img_url if img_url else "https://via.placeholder.com/150/f4f4f4/cccccc?text=NO+IMAGE", use_container_width=True)
                    st.markdown(f"<div class='player-header'>{efternavn}</div>", unsafe_allow_html=True)
                    st.caption(f"Full: {full_name}")

                    for label, c_name in metrics.items():
                        val, pct = 0.0, 0
                        if c_name:
                            val = float(row[c_name])
                            max_val = df_hold[c_name].max()
                            pct = min(int((val / max_val) * 100), 100) if max_val > 0 else 0
                            val_str = f"{val:.1f}"
                        else:
                            val_str = "N/A"

                        st.markdown(f"""
                            <div class="stat-box">
                                <div class="stat-label">{label}</div>
                                <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;"></div></div>
                                <div class="val-text">{val_str}</div>
                            </div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Kritisk fejl: {e}")
