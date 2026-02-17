import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch

def draw_pitch_plotly(fig):
    """Tilføjer en fodboldbane-baggrund til en Plotly figur"""
    fig.add_shape(type="rect", x0=0, y0=0, x1=100, y1=100, line_color="white", fillcolor="#224422", layer="below")
    fig.add_shape(type="line", x0=50, y0=0, x1=50, y1=100, line_color="white")
    fig.add_shape(type="circle", x0=41, y0=41, x1=59, y1=59, line_color="white")
    fig.add_shape(type="rect", x0=0, y0=20, x1=16.5, y1=80, line_color="white")
    fig.add_shape(type="rect", x0=83.5, y0=20, x1=100, y1=80, line_color="white")
    return fig

@st.cache_data(show_spinner="Genererer heatmap...")
def render_mpl_heatmap(df_events, team_id):
    """Genererer heatmap vha. mplsoccer og seaborn"""
    # Filtrer kun pass-data for det valgte hold
    df_p = df_events[(df_events['TEAM_WYID'] == team_id) & 
                     (df_events['PRIMARYTYPE'].str.lower().str.contains('pass', na=False))].copy()
    
    if df_p.empty:
        return None

    pitch = VerticalPitch(pitch_type='wyscout', line_color='#1a1a1a', linewidth=1, pitch_color='white')
    fig, ax = pitch.draw(figsize=(6, 8))
    
    sns.kdeplot(
        x=df_p['LOCATIONY'], y=df_p['LOCATIONX'],
        ax=ax, fill=True, thresh=0.05, levels=15,
        cmap='YlOrRd', alpha=0.7, zorder=1, clip=((0, 100), (0, 100))
    )
    return fig

def vis_side(df_team_matches, hold_map, df_events):
    # --- CSS for det "mørke" Scout look ---
    st.markdown("""
        <style>
        .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; border-bottom: 3px solid #df003b; }
        </style>
    """, unsafe_allow_html=True)

    if df_team_matches is None or df_team_matches.empty:
        st.error("Ingen kampdata fundet.")
        return

    # 1. Valg af modstander
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    col_h1, col_h2 = st.columns([2, 1])
    with col_h1:
        valgt_navn = st.selectbox("Vælg modstander:", options=sorted(navne_dict.keys()))
    
    valgt_id = navne_dict[valgt_navn]
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    df_f['DATE'] = pd.to_datetime(df_f['DATE'])
    df_f = df_f.sort_values('DATE', ascending=False)

    # --- 2. STATS PANEL ---
    st.markdown(f"### {valgt_navn.upper()} Profil")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Gns. xG", round(df_f['XG'].mean(), 2))
    m2.metric("Skud", int(df_f['SHOTS'].mean()) if 'SHOTS' in df_f else "N/A")
    m3.metric("Possession", f"{round(df_f['POSSESSIONPERCENT'].mean(), 1)}%")
    m4.metric("Mål", round(df_f['GOALS'].mean(), 1))
    
    seneste_3_xg = df_f['XG'].head(3).mean()
    m5.metric("Trend (xG)", f"{round(seneste_3_xg, 2)}", delta=round(seneste_3_xg - df_f['XG'].mean(), 2))

    st.markdown("---")

    # --- 3. TO-DELT LAYOUT ---
    left_col, right_col = st.columns([1.5, 1])

    with left_col:
        # Brug Tabs til at skifte mellem den visuelle oversigt og det rå heatmap
        tab_taktik, tab_heatmap = st.tabs(["Taktisk Oversigt", "Positionelt Heatmap"])
        
        with tab_taktik:
            mode = st.radio("Vis på banen:", ["Afslutningsstyrke", "Pres/Intensitet"], horizontal=True)
            fig_pitch = go.Figure()
            draw_pitch_plotly(fig_pitch)

            if mode == "Afslutningsstyrke":
                fig_pitch.add_annotation(x=85, y=50, text=f"xG: {round(df_f['XG'].mean(), 2)}", showarrow=False, font=dict(color="white", size=20))
                fig_pitch.add_annotation(x=85, y=30, text=f"Skud: {int(df_f['SHOTS'].mean() if 'SHOTS' in df_f else 0)}", showarrow=False, font=dict(color="rgba(255,255,255,0.6)"))
            else:
                pos = df_f['POSSESSIONPERCENT'].mean()
                fig_pitch.add_trace(go.Contour(z=[[0, 0, 0], [0, pos/10, pos/5], [0, 0, 0]], x=[20, 50, 80], y=[20, 50, 80], colorscale='YlOrRd', opacity=0.4, showscale=False))
                fig_pitch.add_annotation(x=50, y=50, text="Dominans-zone", showarrow=False, font=dict(color="white"))

            fig_pitch.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(range=[0, 100], visible=False), yaxis=dict(range=[0, 100], visible=False), height=500, plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pitch, use_container_width=True)

        with tab_heatmap:
            if df_events is not None:
                fig_heat = render_mpl_heatmap(df_events, valgt_id)
                if fig_heat:
                    st.pyplot(fig_heat)
                else:
                    st.warning("Ingen afleveringsdata fundet for dette hold i event-datasættet.")

    with right_col:
        st.subheader("Seneste Kampe")
        mini_df = df_f[['DATE', 'MATCHLABEL', 'XG', 'GOALS']].head(5).copy()
        mini_df['DATE'] = mini_df['DATE'].dt.strftime('%d/%m')
        st.table(mini_df)
        
        st.write("Skud-præcision")
        acc = (df_f['GOALS'].sum() / df_f['SHOTS'].sum() * 100) if 'SHOTS' in df_f and df_f['SHOTS'].sum() > 0 else 0
        st.progress(min(acc/30, 1.0), text=f"{round(acc,1)}% conversion rate")

    st.info(f"**Scout Note:** {valgt_navn} har en gennemsnitlig possession på {round(df_f['POSSESSIONPERCENT'].mean(), 1)}%. Analysér heatmap for at se foretrukne opspilszoner.")
