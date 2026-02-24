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

        # Rens data
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(super_clean)

        # Numerisk konvertering
        cols_to_fix = ['GOALS', 'XGSHOT', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'SHOTS', 'PPDA']
        for c in cols_to_fix:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        # Samlet xG kolonne (Tekst)
        df['xG (Diff)'] = df.apply(lambda r: f"{r['XGSHOT']:.2f} ({'+' if (r['GOALS']-r['XGSHOT']) > 0 else ''}{(r['GOALS']-r['XGSHOT']):.2f})", axis=1)
        df['xG Imod (Diff)'] = df.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({'+' if (r['XGSHOTAGAINST']-r['CONCEDEDGOALS']) > 0 else ''}{(r['XGSHOTAGAINST']-r['CONCEDEDGOALS']):.2f})", axis=1)

        # --- FILTRE ---
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
            # Beregn gennemsnit
            avg_mål_liga = df_liga['GOALS'].mean()
            avg_xg_liga = df_liga['XGSHOT'].mean()
            
            # Header række til gennemsnit
            st.write("---")
            m1, m2, m3, m4 = st.columns([3, 1, 2, 1])
            with m1: st.caption(f"Gns. {valgt_liga}")
            with m2: st.write(f"**{avg_mål_liga:.1f}**")
            with m3: st.write(f"**{avg_xg_liga:.2f}**")
            
            if valgt_hold != "Alle":
                h_mål = df_filt['GOALS'].iloc[0]
                h_xg = df_filt['XGSHOT'].iloc[0]
                m1, m2, m3, m4 = st.columns([3, 1, 2, 1])
                with m1: st.caption(f"Hold: {valgt_hold}")
                with m2: st.write(f"**{h_mål}**")
                with m3: st.write(f"**{h_xg:.2f}**")
            
            calc_height = (len(df_filt) + 1) * 35 + 45
            st.dataframe(
                df_filt[['TEAMNAME', 'GOALS', 'xG (Diff)', 'SHOTS']],
                use_container_width=True,
                hide_index=True,
                height=calc_height,
                column_config={
                    "TEAMNAME": st.column_config.TextColumn("Hold"),
                    "GOALS": st.column_config.NumberColumn("Mål", alignment="center"),
                    "xG (Diff)": st.column_config.TextColumn("xG (Diff)", width="medium", alignment="center"),
                    "SHOTS": st.column_config.NumberColumn("Skud", alignment="center")
                }
            )

        with tabs[1]: # DEFENSIVT
            avg_imod_liga = df_liga['CONCEDEDGOALS'].mean()
            avg_xg_imod_liga = df_liga['XGSHOTAGAINST'].mean()

            st.write("---")
            d1, d2, d3, d4 = st.columns([3, 1, 2, 1])
            with d1: st.caption(f"Gns. {valgt_liga}")
            with d2: st.write(f"**{avg_imod_liga:.1f}**")
            with d3: st.write(f"**{avg_xg_imod_liga:.2f}**")

            if valgt_hold != "Alle":
                h_imod = df_filt['CONCEDEDGOALS'].iloc[0]
                h_xg_imod = df_filt['XGSHOTAGAINST'].iloc[0]
                d1, d2, d3, d4 = st.columns([3, 1, 2, 1])
                with d1: st.caption(f"Hold: {valgt_hold}")
                with d2: st.write(f"**{h_imod}**")
                with d3: st.write(f"**{h_xg_imod:.2f}**")

            st.dataframe(
                df_filt[['TEAMNAME', 'GOALS', 'xG (Diff)', 'SHOTS']],
                use_container_width=True,
                hide_index=True,
                height=calc_height,
                column_config={
                    "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                    # Vi bruger TextColumn her for at tvinge centreringen igennem
                    "GOALS": st.column_config.TextColumn("Mål", alignment="center"),
                    "xG (Diff)": st.column_config.TextColumn("xG (Diff)", alignment="center", width="medium"),
                    "SHOTS": st.column_config.TextColumn("Skud", alignment="center")
                }
            )

        with tabs[2]: # STILLING
            st.dataframe(
                df_filt[['TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']], 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "TEAMNAME": "Hold",
                    "MATCHES": st.column_config.NumberColumn("K", alignment="center"),
                    "TOTALWINS": st.column_config.NumberColumn("V", alignment="center"),
                    "TOTALDRAWS": st.column_config.NumberColumn("U", alignment="center"),
                    "TOTALLOSSES": st.column_config.NumberColumn("T", alignment="center"),
                    "TOTALPOINTS": st.column_config.NumberColumn("Point", alignment="center")
                }
            )
    else:
        st.error("Filen mangler.")
