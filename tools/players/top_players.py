import streamlit as st
import pandas as pd
import data.HIF_load as hif_load

def vis_side():
    # CSS til at matche dit billede (Sort overskrift-bar og røde stats)
    st.markdown("""
        <style>
        .player-header { background-color: black; color: white; text-align: center; font-weight: bold; padding: 5px; margin-bottom: 10px; border-radius: 2px; }
        .stat-box { margin-bottom: 8px; }
        .bar-bg { background-color: #eee; height: 6px; width: 100%; border-radius: 3px; }
        .bar-fill { background-color: #df003b; height: 6px; border-radius: 3px; }
        .val-text { font-size: 10px; font-weight: bold; text-align: right; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center; color: #1f1f1f;'>EXPLOSIVE PHYSICAL PROFILES</h2>", unsafe_allow_html=True)
    
    try:
        # 1. HENT DATA VIA DIN PAKKE
        dp = hif_load.get_scouting_package()
        
        # Prøv at finde spiller-data i pakken
        df = dp.get("players", pd.DataFrame())
        if df.empty:
            df = dp.get("advanced_stats", pd.DataFrame())
            
        df_meta = dp.get("sql_players", pd.DataFrame())

        if df.empty:
            st.error("Kunne ikke hente data fra hif_load.get_scouting_package().")
            return

        # Normaliser kolonner til STORE
        df.columns = [c.upper() for c in df.columns]

        # 2. FIND DINE FILTRE (Hvidovre-app værdier)
        # Vi filtrerer på de værdier, du oplyste i starten
        if 'SEASONNAME' in df.columns:
            df = df[df['SEASONNAME'] == "2025/2026"]
        
        team_col = next((c for c in df.columns if 'TEAM' in c or 'HOLD' in c), None)
        if not team_col:
            st.error("Kunne ikke finde hold-kolonnen.")
            return

        hold_liste = sorted([str(x) for x in df[team_col].unique() if pd.notnull(x)])
        valgt_hold = st.selectbox("VÆLG HOLD", options=hold_liste)

        if valgt_hold:
            # Filtrer til det valgte hold
            df_hold = df[df[team_col] == valgt_hold].copy()

            # 3. RENS ALT DATA (Vigtigt!)
            # Tving alle kolonner undtagen navne til at være tal
            for col in df_hold.columns:
                if col not in ['PLAYER_NAME', team_col, 'IMAGEDATAURL']:
                    df_hold[col] = pd.to_numeric(df_hold[col], errors='coerce').fillna(0.0)

            # Find Top 5 spillere baseret på summen af deres stats (aktivitet)
            num_cols = df_hold.select_dtypes(include=['number']).columns
            df_hold['SCORE'] = df_hold[num_cols].sum(axis=1)
            top_5 = df_hold.sort_values('SCORE', ascending=False).head(5)

            # 4. DEFINER METRICS (Matcher dit billede)
            # Vi leder efter de fysiske stats i dine data
            metrics = {
                "Distance": next((c for c in df_hold.columns if 'DIST' in c), None),
                "Sprints": next((c for c in df_hold.columns if 'SPRINT' in c), None),
                "Speed": next((c for c in df_hold.columns if 'SPEED' in c or 'VMAX' in c), None),
                "Accels": next((c for c in df_hold.columns if 'ACC' in c), None)
            }

            # 5. GRID VISNING
            cols = st.columns(5)
            for i, (idx, row) in enumerate(top_5.iterrows()):
                with cols[i]:
                    name = str(row.get('PLAYER_NAME', 'Ukendt'))
                    efternavn = name.split()[-1].upper() if " " in name else name.upper()
                    
                    # Hent billede fra meta-data hvis muligt
                    img_url = None
                    if not df_meta.empty:
                        m = df_meta[df_meta['PLAYER_NAME'] == name] if 'PLAYER_NAME' in df_meta.columns else pd.DataFrame()
                        if not m.empty:
                            img_url = m.iloc[0].get('IMAGEDATAURL') or m.iloc[0].get('ImageDataURL')

                    st.image(img_url if img_url else "https://via.placeholder.com/150", use_container_width=True)
                    st.markdown(f"<div class='player-header'>{efternavn}</div>", unsafe_allow_html=True)

                    for label, c_name in metrics.items():
                        val, pct = 0.0, 0
                        if c_name:
                            val = float(row[c_name])
                            max_val = df_hold[c_name].max()
                            pct = min(int((val / max_val) * 100), 100) if max_val > 0 else 0

                        st.markdown(f"""
                            <div class="stat-box">
                                <div style='font-size:9px; color:#666;'>{label}</div>
                                <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;"></div></div>
                                <div class="val-text">{val:.1f}</div>
                            </div>
                        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Fejl: {e}")
