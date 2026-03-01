import streamlit as st
import pandas as pd

def vis_side(df):
    st.markdown('<h3 style="color:#cc0000; margin-bottom:10px;">KAMPOVERSIGT</h3>', unsafe_allow_html=True)

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("Ingen data fundet.")
        return

    try:
        df = df.copy()
        df.columns = [c.upper() for c in df.columns]

        # 1. LIGA-FILTER (ID 328)
        if 'COMPETITION_WYID' in df.columns:
            df = df[df['COMPETITION_WYID'] == 328].copy()
        
        # Sorter efter dato så vi får de rigtige "seneste 5"
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            df = df.sort_values(dato_col, ascending=False)

        # 2. FORBERED NAVNE OG MÅL (Opta-specifik sikring)
        # Vi leder efter de korrekte navne-kolonner fra dit Opta-feed
        h_name_col = next((c for c in ['CONTESTANTHOME_NAME', 'HOME_TEAM_NAME', 'HOME_TEAM'] if c in df.columns), None)
        a_name_col = next((c for c in ['CONTESTANTAWAY_NAME', 'AWAY_TEAM_NAME', 'AWAY_TEAM'] if c in df.columns), None)

        # Vi tvinger navnene ind - hvis de mangler, bruger vi 'Ukendt' så vi kan se det fejler
        df['HOME_TEAM'] = df[h_name_col].astype(str) if h_name_col else "Ukendt H"
        df['AWAY_TEAM'] = df[a_name_col].astype(str) if a_name_col else "Ukendt U"
        
        # Mål-logik (Henter fra de rigtige Opta-felter)
        h_score_col = next((c for c in ['TOTAL_HOME_SCORE', 'HOME_SCORE', 'HOME_GOALS'] if c in df.columns), None)
        a_score_col = next((c for c in ['TOTAL_AWAY_SCORE', 'AWAY_SCORE', 'AWAY_GOALS'] if c in df.columns), None)

        df['H_GOALS'] = pd.to_numeric(df[h_score_col] if h_score_col else 0, errors='coerce').fillna(0).astype(int)
        df['A_GOALS'] = pd.to_numeric(df[a_score_col] if a_score_col else 0, errors='coerce').fillna(0).astype(int)
        
        # Vigtigt: Skab KAMP_NAVN her, så filteret i sektion 5 virker!
        df['KAMP_NAVN'] = df['HOME_TEAM'] + " - " + df['AWAY_TEAM']

        # 3. DYNAMISK HOLD-LISTE
        # Nu trækker vi listen fra de faktiske navne vi lige har fundet
        liga_hold = sorted([h for h in list(set(df['HOME_TEAM'].unique()) | set(df['AWAY_TEAM'].unique())) if "Ukendt" not in h])

        # --- 4. TOP BAR LAYOUT ---
        # Vi laver 3 kolonner: Dropdown, Stats, Form
        c1, c2, c3 = st.columns([1.5, 2.5, 2])

        with c1:
            valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + liga_hold, index=hvi_index, label_visibility="collapsed")

        stats_html = ""
        form_html = ""

        if valgt_hold != "Alle hold":
            f_df = df[(df['HOME_TEAM'] == valgt_hold) | (df['AWAY_TEAM'] == valgt_hold)].copy()
            # Sortér så nyeste kamp er først til form-beregning
            f_df = f_df.sort_values(dato_col, ascending=False)
            
            # Beregn Stats
            v, u, t, mf, mm = 0, 0, 0, 0, 0
            form_list = []

            for _, r in f_df.iterrows():
                is_home = r['HOME_TEAM'] == valgt_hold
                h, a = r['H_GOALS'], r['A_GOALS']
                mf += h if is_home else a
                mm += a if is_home else h
                
                # Resultat logik
                res = "U"
                color = "#6c757d" # Grå
                if h == a:
                    u += 1
                elif (is_home and h > a) or (not is_home and a > h):
                    v += 1
                    res, color = "V", "#28a745" # Grøn
                else:
                    t += 1
                    res, color = "T", "#dc3545" # Rød
                
                # Gem kun de seneste 5 til form-oversigten
                if len(form_list) < 5:
                    form_list.append(f'<span style="background-color:{color}; color:white; padding:2px 6px; border-radius:3px; margin-right:3px; font-size:12px; font-weight:bold;">{res}</span>')

            stats_html = f"<div style='padding-top:8px;'><span style='font-size:14px; color:#555;'><b>STATS:</b> {len(f_df)}K | {v}V-{u}U-{t}T | {mf}-{mm}</span></div>"
            form_html = f"<div style='padding-top:8px;'><span style='font-size:12px; color:#555; margin-right:5px;'>FORM:</span>{''.join(reversed(form_list))}</div>"
        else:
            f_df = df.copy()
            stats_html = "<div style='padding-top:8px;'><span style='font-size:14px; color:#555;'>Viser alle kampe</span></div>"

        with c2:
            st.markdown(stats_html, unsafe_allow_html=True)
        with c3:
            st.markdown(form_html, unsafe_allow_html=True)

        st.markdown("---")

        # --- 5. TABELVISNING ---
        f_df['MÅL'] = f_df['H_GOALS'].astype(str) + " - " + f_df['A_GOALS'].astype(str)
        f_df['DATO_STR'] = f_df[dato_col].dt.strftime('%d-%m-%Y')

        disp = f_df[['DATO_STR', 'KAMP_NAVN', 'MÅL']].copy()
        disp.columns = ['Dato', 'Kamp', 'Mål']
        
        st.dataframe(disp, use_container_width=True, hide_index=True, height=min((len(disp)*35)+45, 800))

    except Exception as e:
        st.error(f"Fejl: {e}")
