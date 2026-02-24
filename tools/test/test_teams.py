import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.data_load import load_snowflake_query, get_data_package, get_team_color, fmt_val

def vis_side():
    # 1. CSS Styling for centrering og design
    st.markdown("""
        <style>
            .stDataFrame {border: none;} 
            button[data-baseweb='tab'][aria-selected='true'] {color: #cc0000 !important; border-bottom-color: #cc0000 !important;}
            [data-testid="stDataFrame"] td { padding: 2px 5px !important; }
            .stat-header { 
                font-weight: bold; 
                font-size: 16px; 
                text-align: center; 
                color: #cc0000;
                margin-bottom: 5px;
            }
            .label-header { font-size: 14px; color: #666; padding-top: 10px; }
            .custom-header h3 { color: #333; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='custom-header'><h3>NORDICBET LIGA: LIGAOVERSIGT & ANALYSE</h3></div>", unsafe_allow_html=True)

    # 2. Data Loading via Data Package
    if "data_package" not in st.session_state:
        st.session_state["data_package"] = get_data_package()
    
    dp = st.session_state["data_package"]
    comp_f = "(328)" 
    seas_f = dp.get("season_filter")

    with st.spinner("Henter ligadata..."):
        df = load_snowflake_query("team_stats_full", comp_f, seas_f)

    if df is None or df.empty:
        st.warning("Ingen data fundet.")
        return

    nyeste_saeson = sorted(df['SEASONNAME'].unique().tolist())[-1]
    df_liga = df[df['SEASONNAME'] == nyeste_saeson].copy()

    tabs = st.tabs(["Offensivt", "Defensivt", "Stilling", "Head-to-Head"])

    # --- TABS 0: OFFENSIVT ---
    with tabs[0]:
        avg_m, avg_x, avg_s = df_liga['GOALS'].mean(), df_liga['XGSHOT'].mean(), df_liga['SHOTS'].mean()
        
        # Centreret gennemsnit over kolonnerne [Logo, Navn, Mål, xG, Skud]
        c_logo, c_navn, c_m, c_x, c_s = st.columns([0.5, 2, 1, 1, 1])
        with c_navn: st.markdown(f"<div class='label-header'>Gns. {nyeste_saeson}</div>", unsafe_allow_html=True)
        with c_m: st.markdown(f"<div class='stat-header'>{avg_m:.1f}</div>", unsafe_allow_html=True)
        with c_x: st.markdown(f"<div class='stat-header'>{avg_x:.2f}</div>", unsafe_allow_html=True)
        with c_s: st.markdown(f"<div class='stat-header'>{int(avg_s)}</div>", unsafe_allow_html=True)

        df_off = df_liga.copy()
        df_off['xG (Diff)'] = df_off.apply(lambda r: f"{r['XGSHOT']:.2f} ({(r['GOALS']-r['XGSHOT']):+.2f})", axis=1)

        st.dataframe(
            df_off[['IMAGEDATAURL', 'TEAMNAME', 'GOALS', 'xG (Diff)', 'SHOTS']].sort_values('GOALS', ascending=False),
            use_container_width=True, hide_index=True, height=480,
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                "GOALS": st.column_config.NumberColumn("Mål", width="small"),
                "xG (Diff)": st.column_config.TextColumn("xG (Diff)", width="small"),
                "SHOTS": st.column_config.NumberColumn("Skud", width="small")
            }
        )

    # --- TABS 1: DEFENSIVT ---
    with tabs[1]:
        avg_im, avg_xim, avg_p = df_liga['CONCEDEDGOALS'].mean(), df_liga['XGSHOTAGAINST'].mean(), df_liga['PPDA'].mean()
        
        d_logo, d_navn, d_im, d_xim, d_p = st.columns([0.5, 2, 1, 1, 1])
        with d_navn: st.markdown(f"<div class='label-header'>Gns. {nyeste_saeson}</div>", unsafe_allow_html=True)
        with d_im: st.markdown(f"<div class='stat-header'>{avg_im:.1f}</div>", unsafe_allow_html=True)
        with d_xim: st.markdown(f"<div class='stat-header'>{avg_xim:.2f}</div>", unsafe_allow_html=True)
        with d_p: st.markdown(f"<div class='stat-header'>{avg_p:.2f}</div>", unsafe_allow_html=True)

        df_def = df_liga.copy()
        df_def['xGA (Diff)'] = df_def.apply(lambda r: f"{r['XGSHOTAGAINST']:.2f} ({(r['XGSHOTAGAINST']-r['CONCEDEDGOALS']):+.2f})", axis=1)

        st.dataframe(
            df_def[['IMAGEDATAURL', 'TEAMNAME', 'CONCEDEDGOALS', 'xGA (Diff)', 'PPDA']].sort_values('CONCEDEDGOALS', ascending=True),
            use_container_width=True, hide_index=True, height=480,
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TEAMNAME": st.column_config.TextColumn("Hold", width="medium"),
                "CONCEDEDGOALS": st.column_config.NumberColumn("Mål Imod", width="small"),
                "xGA (Diff)": st.column_config.TextColumn("xGA (Diff)", width="small"),
                "PPDA": st.column_config.NumberColumn("PPDA", width="small")
            }
        )

    # --- TABS 2: STILLING ---
    with tabs[2]:
        st.dataframe(
            df_liga[['IMAGEDATAURL', 'TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']].sort_values('TOTALPOINTS', ascending=False), 
            use_container_width=True, hide_index=True, height=520,
            column_config={
                "IMAGEDATAURL": st.column_config.ImageColumn("", width="small"),
                "TEAMNAME": "Hold", "TOTALPOINTS": "Point", "MATCHES": "K", "TOTALWINS": "V", "TOTALDRAWS": "U", "TOTALLOSSES": "T"
            }
        )

    # --- TABS 3: HEAD-TO-HEAD ---
    with tabs[3]:
        hold_navne = sorted(df_liga['TEAMNAME'].unique().tolist())
        hif_name = "Hvidovre"
        
        c_pop, c_t1, c_t2 = st.columns([0.6, 1, 1])
        
        with c_t1:
            default_idx = next((i for i, n in enumerate(hold_navne) if hif_name in n), 0)
            team1 = st.selectbox("Vælg Hold 1", hold_navne, index=default_idx)
        
        with c_t2:
            # Vi fjerner team1 fra listen over mulige modstandere for at undgå fejl
            modstander_liste = [h for h in hold_navne if h != team1]
            team2 = st.selectbox("Vælg Hold 2", modstander_liste, index=0)

        t1_stats = df_liga[df_liga['TEAMNAME'] == team1].iloc[0]
        t2_stats = df_liga[df_liga['TEAMNAME'] == team2].iloc[0]

        metrics = ['GOALS', 'XGSHOT', 'CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']
        labels = ['Mål', 'xG', 'Mål Imod', 'xG Imod', 'PPDA']

        with c_pop:
            st.write(" ")
            st.write(" ")
            with st.popover("🔢 Sammenlign data"):
                st.markdown(f"**Sammenlign data: {team1} vs {team2}**")
                
                # Opbyg data til tabellen
                data = {"Metrik": labels, team1: [], team2: []}
                styles = []

                for m in metrics:
                    v1, v2 = float(t1_stats[m]), float(t2_stats[m])
                    is_def = m in ['CONCEDEDGOALS', 'XGSHOTAGAINST', 'PPDA']
                    
                    t1_better = v1 < v2 if is_def else v1 > v2
                    t2_better = v2 < v1 if is_def else v2 > v1
                    
                    data[team1].append(fmt_val(v1))
                    data[team2].append(fmt_val(v2))
                    
                    # Gem styling-instruktion for denne række
                    styles.append({
                        team1: "background-color: #d4edda; color: black;" if t1_better else "",
                        team2: "background-color: #d4edda; color: black;" if t2_better else ""
                    })
                
                # Opret DataFrame og nulstil index for at undgå "non-unique index" fejl
                compare_df = pd.DataFrame(data).reset_index(drop=True)

                # Robust styling funktion
                def apply_row_style(row):
                    idx = row.name
                    row_styles = [""] * len(row) # Standard ingen stil for 'Metrik'
                    row_styles[1] = styles[idx][team1]
                    row_styles[2] = styles[idx][team2]
                    return row_styles

                st.dataframe(
                    compare_df.style.apply(apply_row_style, axis=1),
                    hide_index=True, 
                    use_container_width=True
                )
