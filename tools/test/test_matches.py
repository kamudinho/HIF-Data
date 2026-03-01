import streamlit as st
import pandas as pd

def vis_side(df):
    st.markdown('<h3 style="color:#cc0000; margin-bottom:10px;">KAMPOVERSIGT</h3>', unsafe_allow_html=True)

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("Ingen data fundet.")
        return

    try:
        # Lav kopi og ensret kolonner
        df = df.copy()
        df.columns = [c.upper() for c in df.columns]

        # --- 1. STRIKT LIGA OG SÆSON FILTER ---
        # Vi tvinger df til KUN at være NordicBet Liga (328) for 2025/2026
        if 'COMPETITION_WYID' in df.columns:
            df = df[df['COMPETITION_WYID'] == 328].copy()
        
        # Sæson-filter: Vi bruger SEASONNAME som defineret i dine værdier
        if 'SEASONNAME' in df.columns:
            df = df[df['SEASONNAME'] == "2025/2026"].copy()
        elif 'SEASON_NAME' in df.columns:
            df = df[df['SEASON_NAME'] == "2025/2026"].copy()

        if df.empty:
            st.info("Ingen kampe fundet for NordicBet Liga 2025/2026.")
            return

        # 2. Dato-håndtering
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE', 'MATCH_DATE'] if c in df.columns), None)
        if dato_col:
            df[dato_col] = pd.to_datetime(df[dato_col])
            df = df.sort_values(dato_col, ascending=False)

        # 3. Klargør navne og mål
        if 'CONTESTANTHOME_NAME' in df.columns:
            df['HOME_TEAM'] = df['CONTESTANTHOME_NAME'].astype(str)
            df['AWAY_TEAM'] = df['CONTESTANTAWAY_NAME'].astype(str)
        else:
            df['HOME_TEAM'] = df['MATCHLABEL'].astype(str).str.split(' - ').str[0]
            df['AWAY_TEAM'] = df['MATCHLABEL'].astype(str).str.split(' - ').str[1]
        
        df['KAMP_NAVN'] = df['HOME_TEAM'] + " - " + df['AWAY_TEAM']
        df['H_GOALS'] = pd.to_numeric(df.get('TOTAL_HOME_SCORE', df.get('HOME_GOALS', 0)), errors='coerce').fillna(0).astype(int)
        df['A_GOALS'] = pd.to_numeric(df.get('TOTAL_AWAY_SCORE', df.get('AWAY_GOALS', 0)), errors='coerce').fillna(0).astype(int)

        # 4. DYNAMISK HOLD-LISTE (Kun fra den aktuelle sæson)
        liga_hold = sorted(list(set(df['HOME_TEAM'].unique()) | set(df['AWAY_TEAM'].unique())))
        hvi_index = next((i + 1 for i, h in enumerate(liga_hold) if "Hvidovre" in str(h)), 0)

        # --- 5. TOP BAR LAYOUT ---
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

            # f_df er allerede sorteret nyeste først fra dato_col ovenfor
            for _, r in f_df.iterrows():
                is_home = r['HOME_TEAM'] == valgt_hold
                h, a = r['H_GOALS'], r['A_GOALS']
                mf += h if is_home else a
                mm += a if is_home else h
                
                res, color = "U", "#6c757d"
                if h == a: u += 1
                elif (is_home and h > a) or (not is_home and a > h):
                    v += 1
                    res, color = "V", "#28a745"
                else:
                    t += 1
                    res, color = "T", "#dc3545"
                
                if len(form_items) < 5:
                    form_items.append(f'<span style="background-color:{color}; color:white; padding:2px 7px; border-radius:4px; margin-right:4px; font-size:12px; font-weight:bold;">{res}</span>')

            stats_html = f"<div style='padding-top:7px;'><span style='font-size:14px; color:#555;'><b>STATS:</b> {len(f_df)}K | {v}V-{u}U-{t}T | {mf}-{mm}</span></div>"
            form_html = f"<div style='padding-top:7px;'><span style='font-size:12px; color:#777; margin-right:8px;'>FORM:</span>{''.join(reversed(form_items))}</div>"
        else:
            f_df = df.copy()
            stats_html = f"<div style='padding-top:7px;'><span style='font-size:14px; color:#555;'>Viser alle {len(f_df)} kampe i 25/26</span></div>"

        with c2: st.markdown(stats_html, unsafe_allow_html=True)
        with c3: st.markdown(form_html, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)

        # --- 6. TABELVISNING ---
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
