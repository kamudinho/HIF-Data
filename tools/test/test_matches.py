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

        # 1. ULTRA-STRIKT LIGA-FILTER
        # Vi sikrer os at vi KUN arbejder med NordicBet Liga (328)
        if 'COMPETITION_WYID' in df.columns:
            df = df[df['COMPETITION_WYID'] == 328].copy()
        elif 'COMPETITION_ID' in df.columns:
            df = df[df['COMPETITION_ID'] == 328].copy()
        
        # Hvis listen stadig indeholder OB/Fredericia her, så tjekker vi for 'Ukendt' i navnene
        if df.empty:
            st.info("Ingen kampe fundet for NordicBet Liga (ID 328).")
            return

        # 2. KLARGØR NAVNE (Vi sikrer at vi ikke tager for meget med)
        h_name_col = next((c for c in ['CONTESTANTHOME_NAME', 'HOME_TEAM_NAME', 'HOME_NAME'] if c in df.columns), None)
        a_name_col = next((c for c in ['CONTESTANTAWAY_NAME', 'AWAY_TEAM_NAME', 'AWAY_NAME'] if c in df.columns), None)

        if h_name_col and a_name_col:
            df['HOME_TEAM'] = df[h_name_col].astype(str)
            df['AWAY_TEAM'] = df[a_name_col].astype(str)
            df['KAMP_NAVN'] = df['HOME_TEAM'] + " - " + df['AWAY_TEAM']
        else:
            # Fallback hvis kolonnenavne driller
            df['KAMP_NAVN'] = df['MATCHLABEL'].astype(str)
            df['HOME_TEAM'] = df['KAMP_NAVN'].str.split(' - ').str[0]
            df['AWAY_TEAM'] = df['KAMP_NAVN'].str.split(' - ').str[1]
        
        # Find dato-kolonne og sorter (vigtigt for FORM)
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE', 'MATCH_DATE'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            df = df.sort_values(dato_col, ascending=False)

        # 3. DYNAMISK HOLD-LISTE
        liga_hold = sorted(list(set(df['HOME_TEAM'].unique()) | set(df['AWAY_TEAM'].unique())))
        hvi_index = next((i + 1 for i, h in enumerate(liga_hold) if "Hvidovre" in str(h)), 0)

        # --- 4. TOP BAR LAYOUT (Tre kolonner) ---
        c1, c2, c3 = st.columns([1.5, 2.5, 2])

        with c1:
            valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + liga_hold, index=hvi_index, label_visibility="collapsed")

        stats_html = ""
        form_html = ""

        if valgt_hold != "Alle hold":
            f_df = df[(df['HOME_TEAM'] == valgt_hold) | (df['AWAY_TEAM'] == valgt_hold)].copy()
            
            # Beregn stats
            v, u, t, mf, mm = 0, 0, 0, 0, 0
            form_items = []

            for _, r in f_df.iterrows():
                is_home = r['HOME_TEAM'] == valgt_hold
                h, a = r['H_GOALS'], r['A_GOALS']
                
                # Mål
                mf += h if is_home else a
                mm += a if is_home else h
                
                # Resultat og farve til form
                res, color = "U", "#6c757d" # Grå
                if h == a:
                    u += 1
                elif (is_home and h > a) or (not is_home and a > h):
                    v += 1
                    res, color = "V", "#28a745" # Grøn
                else:
                    t += 1
                    res, color = "T", "#dc3545" # Rød
                
                # Vi gemmer de seneste 5 til form-barren
                if len(form_items) < 5:
                    form_items.append(f'<span style="background-color:{color}; color:white; padding:2px 7px; border-radius:4px; margin-right:4px; font-size:12px; font-weight:bold;">{res}</span>')

            stats_html = f"<div style='padding-top:7px;'><span style='font-size:14px; color:#555;'><b>STATS:</b> {len(f_df)}K | {v}V-{u}U-{t}T | {mf}-{mm}</span></div>"
            # Vi viser formen fra venstre mod højre (nyeste til højre)
            form_html = f"<div style='padding-top:7px;'><span style='font-size:12px; color:#777; margin-right:8px;'>FORM:</span>{''.join(reversed(form_items))}</div>"
        else:
            f_df = df.copy()
            stats_html = "<div style='padding-top:7px;'><span style='font-size:14px; color:#555;'>Viser alle kampe</span></div>"

        with c2:
            st.markdown(stats_html, unsafe_allow_html=True)
        with c3:
            st.markdown(form_html, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)

        # --- 5. TABELVISNING ---
        f_df['MÅL'] = f_df['H_GOALS'].astype(str) + " - " + f_df['A_GOALS'].astype(str)
        if dato_col:
            f_df['DATO_STR'] = f_df[dato_col].dt.strftime('%d-%m-%Y')
        else:
            f_df['DATO_STR'] = "-"

        disp = f_df[['DATO_STR', 'KAMP_NAVN', 'MÅL']].copy()
        disp.columns = ['Dato', 'Kamp', 'Mål']
        
        st.dataframe(disp, use_container_width=True, hide_index=True, height=min((len(disp)*35)+45, 800))

    except Exception as e:
        st.error(f"Fejl i visning: {e}")
