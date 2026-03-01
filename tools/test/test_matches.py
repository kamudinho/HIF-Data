import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(df):
    st.subheader("KAMPOVERSIGT")

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("Ingen data fundet.")
        return

    try:
        df = df.copy()
        df.columns = [c.upper() for c in df.columns]

        # 1. LIGA-FILTER (ID 328)
        if 'COMPETITION_WYID' in df.columns:
            df = df[df['COMPETITION_WYID'] == 328].copy()
        elif 'COMPETITION_ID' in df.columns:
             df = df[df['COMPETITION_ID'] == 328].copy()

        if df.empty:
            st.info("Ingen kampe fundet for NordicBet Liga (ID 328).")
            return

        # 2. KLARGØR NAVNE FØR FILTER
        if 'MATCHLABEL' in df.columns:
            df['KAMP_NAVN'] = df['MATCHLABEL'].astype(str)
        elif 'CONTESTANTHOME_NAME' in df.columns:
            df['KAMP_NAVN'] = df['CONTESTANTHOME_NAME'].astype(str) + " - " + df['CONTESTANTAWAY_NAME'].astype(str)
        else:
            df['KAMP_NAVN'] = "Ukendt Kamp"

        # 3. DYNAMISK HOLD-LISTE
        if 'CONTESTANTHOME_NAME' in df.columns:
            hjemme = df['CONTESTANTHOME_NAME'].dropna().unique()
            ude = df['CONTESTANTAWAY_NAME'].dropna().unique()
            liga_hold = sorted(list(set(hjemme) | set(ude)))
        else:
            labels = df['KAMP_NAVN'].str.split(' - ').str[0].unique()
            liga_hold = sorted([x for x in labels if x and str(x) != 'nan'])

        hvi_index = 0
        for i, h in enumerate(liga_hold):
            if "Hvidovre" in str(h):
                hvi_index = i + 1
                break

        valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + liga_hold, index=hvi_index)

        # 4. UDFØR HOLD-FILTRERING (Her skaber vi f_df)
        if valgt_hold != "Alle hold":
            mask = (df['KAMP_NAVN'].str.contains(valgt_hold, case=False, na=False))
            f_df = df[mask].copy()
        else:
            f_df = df.copy()

        # 5. BEREGN RESULTAT OG DATO PÅ DEN FILTREREDE DATA (f_df)
        # Vi henter værdier fra f_df nu!
        h_score = f_df.get('TOTAL_HOME_SCORE', f_df.get('HOME_GOALS', 0))
        a_score = f_df.get('TOTAL_AWAY_SCORE', f_df.get('AWAY_GOALS', 0))
        
        f_df['MÅL'] = h_score.astype(str) + " - " + a_score.astype(str)
        f_df['MÅL'] = f_df['MÅL'].replace("nan - nan", "-")

        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE'] if c in f_df.columns), None)
        if dato_col:
            f_df['DATO_STR'] = f_df[dato_col].astype(str).str[:10]
        else:
            f_df['DATO_STR'] = "-"

        # 6. VISNING
        final_df = f_df[['DATO_STR', 'KAMP_NAVN', 'MÅL']].copy()
        final_df.columns = ['Dato', 'Kamp', 'Mål']

        hoejde = min((len(final_df) * 35) + 45, 800)

        st.dataframe(
            final_df,
            use_container_width=True,
            hide_index=True,
            height=hoejde
        )

    except Exception as e:
        st.error(f"Der skete en fejl i tabel-genereringen: {e}")

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
