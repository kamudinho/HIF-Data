import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# Sikrere import af SEASONNAME
try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "2025/2026"

def vis_side(spillere, player_stats_sn):
    # --- 1. CSS INJECTION (Layout & Design) ---
    st.markdown("""
        <style>
            [data-testid="column"] {
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            }
            div[data-testid="stHorizontalBlock"] > div:last-child div[data-testid="stVerticalBlock"] {
                align-items: flex-end !important;
            }
            div[data-testid="stSegmentedControl"], div[data-testid="stPills"] {
                width: fit-content !important;
                margin-left: auto !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:25px; box-shadow: 0 2px 1px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem;">SPILLER STATISTIK</h3>
        </div>
    """, unsafe_allow_html=True)

    # --- 3. DATA CHECK & PROCESSERING ---
    if player_stats_sn is None or player_stats_sn.empty:
        st.warning("Ingen statistisk data fundet fra Snowflake.")
        return

    # Klargør dataframes
    s_info = spillere.copy()
    s_stats = player_stats_sn.copy()
    
    # Tving alle kolonnenavne til UPPERCASE
    s_info.columns = [str(c).upper().strip() for c in s_info.columns]
    s_stats.columns = [str(c).upper().strip() for c in s_stats.columns]

    # --- SIKKERHEDS-CHECK AF KOLONNER ---
    # Vi tjekker om 'NAVN' findes, ellers prøver vi at finde en kolonne der ligner
    if 'NAVN' not in s_info.columns:
        if 'SPILLER' in s_info.columns:
            s_info = s_info.rename(columns={'SPILLER': 'NAVN'})
        elif 'PLAYER' in s_info.columns:
            s_info = s_info.rename(columns={'PLAYER': 'NAVN'})
        else:
            st.error(f"Fejl: Kunne ikke finde en navne-kolonne i din CSV. Fundne kolonner: {list(s_info.columns)}")
            return

    # Vi tjekker om Opta ID findes
    ID_COL = 'PLAYER_OPTAUUID'
    if ID_COL not in s_info.columns:
        st.error(f"Fejl: Kolonnen '{ID_COL}' mangler i din players.csv. Fundne kolonner: {list(s_info.columns)}")
        return

    # Rens ID'er
    s_info[ID_COL] = s_info[ID_COL].astype(str).str.strip()
    s_stats[ID_COL] = s_stats[ID_COL].astype(str).str.strip()

    # --- MERGE ---
    try:
        df_hif = pd.merge(
            s_stats, 
            s_info[[ID_COL, 'NAVN']], 
            on=ID_COL, 
            how='inner'
        ).fillna(0)
    except KeyError as e:
        st.error(f"Merge-fejl: Kolonnen {e} blev ikke fundet.")
        st.write("CSV kolonner:", list(s_info.columns))
        st.write("Snowflake kolonner:", list(s_stats.columns))
        return

    if df_hif.empty:
        st.info("Ingen spillere matchet via PLAYER_OPTAUUID.")
        # Debug hjælp:
        with st.expander("Tjek ID-match her"):
            st.write("Første ID i CSV:", s_info[ID_COL].iloc[0] if not s_info.empty else "Ingen")
            st.write("Første ID i Snowflake:", s_stats[ID_COL].iloc[0] if not s_stats.empty else "Ingen")
        return

    # --- 4. UI KONTROLLER ---
    c1, c2 = st.columns([1, 1], gap="large")
    
    # Mapper UI til dine Snowflake-kolonner (som de er defineret i din SQL)
    kpi_map = {
        "Mål": "GOALS", 
        "Assists": "ASSISTS", 
        "xG": "XGSHOT", 
        "Skud": "SHOTS", 
        "Minutter": "MINUTESONFIELD",
        "Touch i feltet": "TOUCHINBOX",
        "Prog. Pasninger": "PROGRESSIVEPASSES"
    }
    
    kpi_med_pct = {
        "Afleveringer": ("PASSES", "SUCCESSFULPASSES"), 
        "Dueller": ("DUELS", "DUELSWON")
    }
    
    alle_kategorier = list(kpi_map.keys()) + list(kpi_med_pct.keys())
    tilgaengelige = [k for k in alle_kategorier if 
                    (k in kpi_map and kpi_map[k] in df_hif.columns) or 
                    (k in kpi_med_pct and kpi_med_pct[k][0] in df_hif.columns)]

    with c1:
        valgt_kat = st.pills("Vælg KPI", tilgaengelige, default=tilgaengelige[0], label_visibility="collapsed")
    with c2:
        visning = st.segmented_control("Visning", ["Total", "Pr. 90"], default="Total", label_visibility="collapsed")

    st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)

    # --- 5. BEREGNING AF GRAF-DATA ---
    df_final = df_hif.drop_duplicates()
    min_col = "MINUTESONFIELD"

    if valgt_kat in kpi_map:
        stat_col = kpi_map[valgt_kat]
        res = df_final.groupby('NAVN', as_index=False).agg({stat_col: 'sum', min_col: 'sum'})
        
        if visning == "Pr. 90" and valgt_kat != "Minutter":
            res['VAL'] = (res[stat_col] / res[min_col].replace(0, np.nan) * 90).fillna(0)
        else:
            res['VAL'] = res[stat_col]
        res['LABEL'] = res['VAL'].apply(lambda x: f"{x:.2f}" if (visning == "Pr. 90" or valgt_kat == "xG") else f"{int(x)}")
    else:
        tot_col, suc_col = kpi_med_pct[valgt_kat]
        res = df_final.groupby('NAVN', as_index=False).agg({tot_col: 'sum', suc_col: 'sum', min_col: 'sum'})
        
        pct = (res[suc_col] / res[tot_col].replace(0, np.nan) * 100).fillna(0)
        if visning == "Pr. 90":
            res['VAL'] = (res[tot_col] / res[min_col].replace(0, np.nan) * 90).fillna(0)
            res['LABEL'] = [f"{v:.2f} ({int(p)}%)" for v, p in zip(res['VAL'], pct)]
        else:
            res['VAL'] = res[tot_col]
            res['LABEL'] = [f"{int(v)} ({int(p)}%)" for v, p in zip(res['VAL'], pct)]

    # Filtrer spillere uden data og sortér
    df_plot = res[res['VAL'] > 0].sort_values('VAL', ascending=True)

    # --- 6. PLOTLY GRAF ---
    h = max(450, (len(df_plot) * 32) + 50)
    fig = px.bar(df_plot, x='VAL', y='NAVN', orientation='h', text='LABEL', 
                 labels={'VAL': valgt_kat, 'NAVN': ''})

    fig.update_traces(
        marker_color='#df003b' if visning == "Total" else '#333',
        textposition='outside',
        cliponaxis=False,
        textfont=dict(size=11, color='#444')
    )

    fig.update_layout(
        height=h, 
        margin=dict(l=0, r=80, t=10, b=40),
        xaxis=dict(
            title=dict(text=f"<b>{valgt_kat.upper()}</b> ({visning})", font=dict(size=12, color='#666')),
            showgrid=True, gridcolor='#f2f2f2', zeroline=False
        ),
        yaxis=dict(tickfont=dict(size=12, color='#222'), fixedrange=True),
        plot_bgcolor='white', 
        paper_bgcolor='white',
        bargap=0.2
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 7. TABELVISNING ---
    with st.expander("📊 Se datatabel", expanded=False):
        df_table = df_plot.sort_values('VAL', ascending=False).copy()
        df_table = df_table.rename(columns={
            'NAVN': 'Spiller',
            'VAL': f'{valgt_kat}',
            'MINUTESONFIELD': 'Minutter'
        })
        
        # Formatering af tabel-visning
        cols_to_show = ['Spiller', f'{valgt_kat}', 'Minutter']
        st.dataframe(
            df_table[cols_to_show], 
            use_container_width=True,
            hide_index=True
        )
