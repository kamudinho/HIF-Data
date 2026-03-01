import streamlit as st
import pandas as pd

def vis_side(df):
    st.markdown('<h3 style="color:#cc0000; margin-bottom:0px;">KAMPOVERSIGT</h3>', unsafe_allow_html=True)

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("Ingen data fundet.")
        return

    try:
        df = df.copy()
        df.columns = [c.upper() for c in df.columns]

        # 1. LIGA-FILTER (ID 328 - NordicBet Liga)
        if 'COMPETITION_WYID' in df.columns:
            df = df[df['COMPETITION_WYID'] == 328].copy()
        elif 'COMPETITION_ID' in df.columns:
             df = df[df['COMPETITION_ID'] == 328].copy()

        # 2. KLARGØR NAVNE OG RESULTATER PÅ HELE SÆTTET
        if 'CONTESTANTHOME_NAME' in df.columns:
            df['KAMP_NAVN'] = df['CONTESTANTHOME_NAME'].astype(str) + " - " + df['CONTESTANTAWAY_NAME'].astype(str)
            df['HOME_TEAM'] = df['CONTESTANTHOME_NAME'].astype(str)
            df['AWAY_TEAM'] = df['CONTESTANTAWAY_NAME'].astype(str)
        else:
            df['KAMP_NAVN'] = df['MATCHLABEL'].astype(str).str.split(',').str[0]
            df['HOME_TEAM'] = df['KAMP_NAVN'].str.split(' - ').str[0]
            df['AWAY_TEAM'] = df['KAMP_NAVN'].str.split(' - ').str[1]

        # Hent mål
        df['H_GOALS'] = pd.to_numeric(df.get('TOTAL_HOME_SCORE', df.get('HOME_GOALS', 0)), errors='coerce').fillna(0).astype(int)
        df['A_GOALS'] = pd.to_numeric(df.get('TOTAL_AWAY_SCORE', df.get('AWAY_GOALS', 0)), errors='coerce').fillna(0).astype(int)

        # 3. DYNAMISK HOLD-LISTE
        liga_hold = sorted(list(set(df['HOME_TEAM'].unique()) | set(df['AWAY_TEAM'].unique())))
        hvi_index = next((i + 1 for i, h in enumerate(liga_hold) if "Hvidovre" in str(h)), 0)

        # --- 4. LAYOUT: MINDRE DROPDOWN ---
        col1, col2 = st.columns([1, 2])
        with col1:
            valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + liga_hold, index=hvi_index, label_visibility="collapsed")

        # --- 5. BEREGN STATS (Kun hvis et hold er valgt) ---
        if valgt_hold != "Alle hold":
            # Filter kampe for valgt hold
            f_df = df[(df['HOME_TEAM'] == valgt_hold) | (df['AWAY_TEAM'] == valgt_hold)].copy()
            
            # Beregn stats
            kampe = len(f_df)
            vundne = 0
            uafgjorte = 0
            tabte = 0
            mf = 0
            mm = 0
            
            for _, r in f_df.iterrows():
                is_home = r['HOME_TEAM'] == valgt_hold
                h_mål, a_mål = r['H_GOALS'], r['A_GOALS']
                
                # Mål for/imod
                mf += h_mål if is_home else a_mål
                mm += a_mål if is_home else h_mål
                
                # Resultat
                if h_mål == a_mål: uafgjorte += 1
                elif (is_home and h_mål > a_mål) or (not is_home and a_mål > h_mål): vundne += 1
                else: tabte += 1
            
            # Vis stats som diskret caption
            st.caption(f"**STATS:** {kampe} K | {vundne} V | {uafgjorte} U | {tabte} T | Mål: {mf}-{mm}")
        else:
            f_df = df.copy()
            st.caption("Viser alle kampe i NordicBet Liga")

        # --- 6. FORMATER TABEL ---
        f_df['MÅL'] = f_df['H_GOALS'].astype(str) + " - " + f_df['A_GOALS'].astype(str)
        
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE'] if c in f_df.columns), None)
        if dato_col:
            f_df['DATO_STR'] = pd.to_datetime(f_df[dato_col], errors='coerce').dt.strftime('%d-%m-%Y')
        else:
            f_df['DATO_STR'] = "-"

        # Visning
        disp = f_df[['DATO_STR', 'KAMP_NAVN', 'MÅL']].copy()
        disp.columns = ['Dato', 'Kamp', 'Mål']
        
        hoejde = min((len(disp) * 35) + 45, 800)
        st.dataframe(disp, use_container_width=True, hide_index=True, height=hoejde)

    except Exception as e:
        st.error(f"Fejl: {e}")
