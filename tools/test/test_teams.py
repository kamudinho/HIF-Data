import streamlit as st
import pandas as pd
import os

def super_clean(text):
    if not isinstance(text, str): return text
    rep = {
        "ƒç": "č", "ƒá": "ć", "≈°": "š", "≈æ": "ž", "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å", "√Å": "Á", "√©": "é", "√∂": "ö", "√º": "ü"
    }
    for wrong, right in rep.items(): text = text.replace(wrong, right)
    return text

def vis_side():
    st.markdown("<style>.stDataFrame {border: none;} button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}</style>", unsafe_allow_html=True)

    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">TEST: HOLDSTATISTIK</h3>
    </div>""", unsafe_allow_html=True)
    
    csv_path = "data/testdata/teams.csv"
    
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
        except:
            df = pd.read_csv(csv_path, encoding='latin-1')

        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(super_clean)

        cols_to_fix = ['GOALS', 'XGSHOT', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'SHOTS', 'PPDA']
        for c in cols_to_fix:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        # Filtre
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            ligaer = ["Alle"] + sorted([str(x) for x in df['SEASONNAME'].unique() if pd.notna(x)])
            valgt_liga = st.selectbox("Sæson / Liga", ligaer)
        
        df_liga = df.copy()
        if valgt_liga != "Alle": 
            df_liga = df_liga[df_liga['SEASONNAME'] == valgt_liga]

        with col_f2:
            hold_liste = ["Alle"] + sorted(df_liga['TEAMNAME'].unique().tolist())
            valgt_hold = st.selectbox("Vælg specifikt hold", hold_liste)

        df_filt = df_liga.copy()
        if valgt_hold != "Alle":
            df_filt = df_filt[df_filt['TEAMNAME'] == valgt_hold]

        tabs = st.tabs(["Offensivt", "Defensivt", "Stilling"])

        with tabs[0]: # OFFENSIVT
            # --- GENNEMSNIT ---
            avg_m = df_liga['GOALS'].mean()
            avg_x = df_liga['XGSHOT'].mean()
            
            m1, m2, m3, m4 = st.columns([2, 1, 1, 1])
            with m1: st.caption(f"Gns. {valgt_liga}")
            with m2: st.markdown(f"<div style='text-align:center'><b>{avg_m:.1f}</b></div>", unsafe_allow_html=True)
            with m3: st.markdown(f"<div style='text-align:center'><b>{avg_x:.2f}</b></div>", unsafe_allow_html=True)
            
            if valgt_hold != "Alle":
                h_m = df_filt['GOALS'].iloc[0]
                h_x = df_filt['XGSHOT'].iloc[0]
                m1, m2, m3, m4 = st.columns([2, 1, 1, 1])
                with m1: st.caption(f"Hold: {valgt_hold}")
                with m2: st.markdown(f"<div style='text-align:center'>{h_m}</div>", unsafe_allow_html=True)
                with m3: st.markdown(f"<div style='text-align:center'>{h_x:.2f}</div>", unsafe_allow_html=True)

            # --- TABEL ---
            df_vis = df_filt.copy()
            # Opretter xG (Diff)
            df_vis['xG (Diff)'] = df_vis.apply(lambda r: f"{r['XGSHOT']:.2f} ({'+' if (r['GOALS']-r['XGSHOT']) > 0 else ''}{(r['GOALS']-r['XGSHOT']):.2f})", axis=1)
            
            # Konverterer tal til tekst for at tvinge centrering uden fejl
            df_vis['GOALS_TXT'] = df_vis['GOALS'].astype(int).astype(str)
            df_vis['SHOTS_TXT'] = df_vis['SHOTS'].astype(int).astype(str)

            st.dataframe(
                df_vis[['TEAMNAME', 'GOALS_TXT', 'xG (Diff)', 'SHOTS_TXT']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "TEAMNAME": st.column_config.TextColumn("Hold"),
                    "GOALS_TXT": st.column_config.TextColumn("Mål", width="small"),
                    "xG (Diff)": st.column_config.TextColumn("xG (Diff)", width="medium"),
                    "SHOTS_TXT": st.column_config.TextColumn("Shots", width="small")
                }
            )

        with tabs[1]: # DEFENSIVT
            avg_im = df_liga['CONCEDEDGOALS'].mean()
            avg_xim = df_liga['XGSHOTAGAINST'].mean()

            d1, d2, d3, d4 = st.columns([2, 1, 1, 1])
            with d1: st.caption(f"Gns. {valgt_liga}")
            with d2: st.markdown(f"<div style='text-align:center'><b>{avg_im:.1f}</b></div>", unsafe_allow_html=True)
            with d3: st.markdown(f"<div style='text-align:center'><b>{avg_xim:.2f}</b></div>", unsafe_allow_html=True)

            df_vis_def = df_filt.copy()
            df_vis_def['xG Imod (Diff)'] = df_vis_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({'+' if (r['XGSHOTAGAINST']-r['CONCEDEDGOALS']) > 0 else ''}{(r['XGSHOTAGAINST']-r['CONCEDEDGOALS']):.2f})", axis=1)
            df_vis_def['IMOD_TXT'] = df_vis_def['CONCEDEDGOALS'].astype(int).astype(str)
            df_vis_def['PPDA_TXT'] = df_vis_def['PPDA'].round(2).astype(str)

            st.dataframe(
                df_vis_def[['TEAMNAME', 'IMOD_TXT', 'xG Imod (Diff)', 'PPDA_TXT']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "TEAMNAME": "Hold",
                    "IMOD_TXT": st.column_config.TextColumn("Mål Imod"),
                    "xG Imod (Diff)": st.column_config.TextColumn("xG Imod (Diff)"),
                    "PPDA_TXT": st.column_config.TextColumn("PPDA")
                }
            )

        with tabs[2]: # STILLING
            st.dataframe(df_filt[['TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']], use_container_width=True, hide_index=True)
    else:
        st.error("Filen mangler.")
