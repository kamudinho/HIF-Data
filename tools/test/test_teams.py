import streamlit as st
import pandas as pd
from data.data_load import load_snowflake_query

def vis_side():
    # 1. Styling
    st.markdown("""
        <style>
            .stDataFrame {border: none;} 
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            /* Gør tabellen mere kompakt for at matche højden */
            [data-testid="stDataFrame"] td { padding: 2px 5px !important; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""<div class='custom-header'><h3>NORDICBET LIGA: LIGAOVERSIGT</h3></div>""", unsafe_allow_html=True)

    # 2. Data Loading fra Snowflake
    dp = st.session_state.get("data_package", {})
    comp_f = "(328)"  # NordicBet Liga
    seas_f = dp.get("season_filter")

    with st.spinner("Henter live data for 1. division..."):
        df = load_snowflake_query("team_stats_full", comp_f, seas_f)

    if df.empty:
        st.warning("Ingen holddata fundet for NordicBet Ligaen.")
        return

    # Automatisk valg af nyeste sæson (ingen dropdown nødvendig)
    nyeste_saeson = sorted(df['SEASONNAME'].unique().tolist())[-1]
    df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()

    # Vi viser alle hold, så df_filt er det samme som df_liga
    df_filt = df_liga.copy()

    tabs = st.tabs(["Offensivt", "Defensivt", "Stilling"])

    # --- OFFENSIVT ---
    with tabs[0]:
        avg_m = df_liga['GOALS'].mean()
        avg_x = df_liga['XGSHOT'].mean()
        avg_s = df_liga['SHOTS'].mean()

        st.write(f"**Gennemsnit for {nyeste_saeson}**") 
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1: st.caption("Ligagennemsnit")
        with c2: st.markdown(f"<p style='text-align:center;margin:0;'><b>{avg_m:.1f}</b></p>", unsafe_allow_html=True)
        with c3: st.markdown(f"<p style='text-align:center;margin:0;'><b>{avg_x:.2f}</b></p>", unsafe_allow_html=True)
        with c4: st.markdown(f"<p style='text-align:center;margin:0;'><b>{int(avg_s)}</b></p>", unsafe_allow_html=True)

        df_vis = df_filt.copy()
        df_vis['xG (Diff)'] = df_vis.apply(lambda r: f"{r['XGSHOT']:.2f} ({'+' if (r['GOALS']-r['XGSHOT']) > 0 else ''}{(r['GOALS']-r['XGSHOT']):.2f})", axis=1)
        df_vis['Mål'] = df_vis['GOALS'].astype(int)
        df_vis['Skud'] = df_vis['SHOTS'].astype(int)

        st.dataframe(
            df_vis[['TEAMNAME', 'Mål', 'xG (Diff)', 'Skud']].sort_values('Mål', ascending=False),
            use_container_width=True,
            hide_index=True,
            height=460,  
            column_config={
                "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                "Mål": st.column_config.NumberColumn("Mål", width="small"),
                "xG (Diff)": st.column_config.TextColumn("xG (Diff)", width="medium"),
                "Skud": st.column_config.NumberColumn("Shots", width="small")
            }
        )

    # --- DEFENSIVT ---
    with tabs[1]:
        avg_im = df_liga['CONCEDEDGOALS'].mean()
        avg_xim = df_liga['XGSHOTAGAINST'].mean()
        avg_p = df_liga['PPDA'].mean()

        st.write(f"**Gennemsnit for {nyeste_saeson}**")
        d1, d2, d3, d4 = st.columns([2, 1, 1, 1])
        with d1: st.caption("Ligagennemsnit")
        with d2: st.markdown(f"<p style='text-align:center;margin:0;'><b>{avg_im:.1f}</b></p>", unsafe_allow_html=True)
        with d3: st.markdown(f"<p style='text-align:center;margin:0;'><b>{avg_xim:.2f}</b></p>", unsafe_allow_html=True)
        with d4: st.markdown(f"<p style='text-align:center;margin:0;'><b>{avg_p:.2f}</b></p>", unsafe_allow_html=True)

        df_vis_def = df_filt.copy()
        df_vis_def['xG Imod (Diff)'] = df_vis_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({'+' if (r['XGSHOTAGAINST']-r['CONCEDEDGOALS']) > 0 else ''}{(r['XGSHOTAGAINST']-r['CONCEDEDGOALS']):.2f})", axis=1)
        df_vis_def['Mål Imod'] = df_vis_def['CONCEDEDGOALS'].astype(int)
        df_vis_def['PPDA_VAL'] = df_vis_def['PPDA'].round(2)

        st.dataframe(
            df_vis_def[['TEAMNAME', 'Mål Imod', 'xG Imod (Diff)', 'PPDA_VAL']].sort_values('Mål Imod', ascending=True),
            use_container_width=True,
            hide_index=True,
            height=460,  
            column_config={
                "TEAMNAME": "Hold",
                "Mål Imod": st.column_config.NumberColumn("Mål Imod"),
                "xG Imod (Diff)": st.column_config.TextColumn("xG Imod (Diff)"),
                "PPDA_VAL": st.column_config.NumberColumn("PPDA")
            }
        )

    # --- STILLING ---
    with tabs[2]:
        st.write(f"**Tabel: {nyeste_saeson}**")
        df_stilling = df_filt.sort_values(by='TOTALPOINTS', ascending=False)
        st.dataframe(
            df_stilling[['TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']], 
            use_container_width=True, 
            hide_index=True,
            height=500  # Lidt højere her da det er hovedtabellen
        )
