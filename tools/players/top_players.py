import streamlit as st
import pandas as pd
import data.HIF_load as hif_load

def vis_side():
    # Opdateret CSS for at give plads til længere navne i bjælken
    st.markdown("""
        <style>
        .player-header { 
            background-color: black; 
            color: white; 
            text-align: center; 
            font-weight: bold; 
            padding: 8px 4px; 
            margin-bottom: 15px; 
            border-radius: 2px; 
            font-size: 12px; /* Lidt mindre skrift så fulde navne kan være der */
            text-transform: uppercase;
            min-height: 40px; /* Sikrer at bjælkerne er lige høje selvom navnet fylder 2 linjer */
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .stat-label { font-size: 10px; color: #666; text-transform: uppercase; }
        .bar-bg { background-color: #f0f0f0; height: 6px; width: 100%; border-radius: 3px; }
        .bar-fill { background-color: #df003b; height: 6px; border-radius: 3px; }
        .val-text { font-size: 11px; font-weight: bold; text-align: right; color: #1f1f1f; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center;'>PHYSICAL PERFORMANCE PROFILES</h2>", unsafe_allow_html=True)
    
    try:
        dp = hif_load.get_scouting_package()
        df = dp.get("physical", dp.get("advanced_stats", dp.get("players", pd.DataFrame())))
        df_meta = dp.get("sql_players", pd.DataFrame())

        if df.empty:
            st.error("Kunne ikke finde data.")
            return

        df.columns = [c.upper() for c in df.columns]

        id_col = next((c for c in df.columns if 'ID' in c), df.columns[0])
        team_col = next((c for c in df.columns if 'TEAM' in c or 'HOLD' in c), None)

        hold_liste = sorted([str(x) for x in df[team_col].unique() if pd.notnull(x)])
        valgt_hold = st.selectbox("VÆLG HOLD", options=hold_liste)

        if valgt_hold:
            df_hold = df[df[team_col] == valgt_hold].copy()

            # Mapping af metrics
            metrics_map = {
                "Distance": next((c for c in df_hold.columns if 'DIST' in c), None),
                "Sprints": next((c for c in df_hold.columns if 'SPRINT' in c), None),
                "Speed": next((c for c in df_hold.columns if 'SPEED' in c or 'VMAX' in c), None),
                "Accels": next((c for c in df_hold.columns if 'ACC' in c), None)
            }

            for m_col in filter(None, metrics_map.values()):
                df_hold[m_col] = pd.to_numeric(df_hold[m_col], errors='coerce').fillna(0.0)

            sort_key = metrics_map["Distance"] if metrics_map["Distance"] else df_hold.columns[-1]
            top_5 = df_hold.sort_values(sort_key, ascending=False).head(5)

            cols = st.columns(5)
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    player_id = str(row[id_col])
                    
                    # Hent fulde navn og billede fra meta
                    full_name = "UKENDT SPILLER"
                    img_url = None
                    if not df_meta.empty:
                        # Vi tjekker alle kolonner i meta for at finde ID'et
                        meta_match = df_meta[df_meta.astype(str).eq(player_id).any(axis=1)]
                        if not meta_match.empty:
                            full_name = meta_match.iloc[0].get('PLAYER_NAME', "UKENDT")
                            img_url = meta_match.iloc[0].get('IMAGEDATAURL')

                    # 1. Billede
                    st.image(img_url if img_url else "https://via.placeholder.com/150", use_container_width=True)
                    
                    # 2. Sort bjælke med FULD NAVN
                    st.markdown(f"<div class='player-header'>{full_name}</div>", unsafe_allow_html=True)

                    # 3. Stats
                    for label, col_name in metrics_map.items():
                        val, pct = 0.0, 0
                        if col_name:
                            val = float(row[col_name])
                            max_val = df_hold[col_name].max()
                            pct = min(int((val / max_val) * 100), 100) if max_val > 0 else 0
                            val_str = f"{val:.1f}"
                        else:
                            val_str = "N/A"

                        st.markdown(f"""
                            <div class="stat-label">{label}</div>
                            <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;"></div></div>
                            <div class="val-text">{val_str}</div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Fejl: {e}")
