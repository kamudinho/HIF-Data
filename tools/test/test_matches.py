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

        # 2. FORBERED NAVNE OG MÅL (Robust version)
        df['HOME_TEAM'] = df['CONTESTANTHOME_NAME'].astype(str) if 'CONTESTANTHOME_NAME' in df.columns else "Hjemme"
        df['AWAY_TEAM'] = df['CONTESTANTAWAY_NAME'].astype(str) if 'CONTESTANTAWAY_NAME' in df.columns else "Ude"
        
        # Her henter vi kolonnerne sikkert. Hvis de ikke findes, laver vi en tom kolonne med 0.
        h_col = df['TOTAL_HOME_SCORE'] if 'TOTAL_HOME_SCORE' in df.columns else pd.Series(0, index=df.index)
        a_col = df['TOTAL_AWAY_SCORE'] if 'TOTAL_AWAY_SCORE' in df.columns else pd.Series(0, index=df.index)
        
        # Nu kan vi sikkert bruge fillna og to_numeric
        df['H_GOALS'] = pd.to_numeric(h_col, errors='coerce').fillna(0).astype(int)
        df['A_GOALS'] = pd.to_numeric(a_col, errors='coerce').fillna(0).astype(int)
        
        df['KAMP_NAVN'] = df['HOME_TEAM'] + " - " + df['AWAY_TEAM']

        # 3. DROPDOWN LISTE
        liga_hold = sorted(list(set(df['HOME_TEAM'].unique()) | set(df['AWAY_TEAM'].unique())))
        hvi_index = next((i + 1 for i, h in enumerate(liga_hold) if "Hvidovre" in str(h)), 0)

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
