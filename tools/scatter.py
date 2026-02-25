import streamlit as st
import plotly.express as px
import pandas as pd
from data.data_load import get_team_colors

# --- 2. FARVER & KONSTANTER ---
hif_rod = "#df003b"

def build_scatter_plot(df_plot, metric_type):
    colors_dict = get_team_colors()
    
    # Split metric_type (f.eks. "xG vs. MÅL FOR") til to labels
    if " vs. " in metric_type:
        x_label, y_label = metric_type.split(" vs. ")
    else:
        x_label, y_label = "X", "Y"

    fig = px.scatter(
        df_plot, 
        x='X_PER_GAME', 
        y='Y_PER_GAME',
        hover_name='TEAMNAME',
        text='TEAMNAME', 
        color='TEAMNAME',
        color_discrete_map=colors_dict,
        # Vi sender MATCHES med som custom_data så den kan bruges i hover
        custom_data=['MATCHES'],
        height=700,
        template="plotly_white",
        labels={
            "X_PER_GAME": x_label, 
            "Y_PER_GAME": y_label
        }
    )

    # Vender KUN y-aksen hvis det handler om mål/skud IMOD (da færre er bedre)
    if any(word in y_label for word in ["MOD", "IMOD", "CONCEDED"]):
        fig.update_yaxes(autorange="reversed")
    else:
        fig.update_yaxes(autorange=True)
    
    # TILPASNING AF HOVER-BOKS
    fig.update_traces(
        marker=dict(size=14, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')),
        textposition='top center',
        hovertemplate=(
            "<b>%{hovertext}</b><br>" + 
            f"{x_label}: %{{x:.2f}}<br>" + 
            f"{y_label}: %{{y:.2f}}<br>" + 
            "<extra></extra>" # Fjerner trace-navnet i siden
        )
    )

    # Gennemsnitslinjer
    avg_x = df_plot['X_PER_GAME'].mean()
    avg_y = df_plot['Y_PER_GAME'].mean()
    fig.add_hline(y=avg_y, line_dash="dot", line_color="grey", opacity=0.5)
    fig.add_vline(x=avg_x, line_dash="dot", line_color="grey", opacity=0.5)
    
    fig.update_layout(
        showlegend=False,
        xaxis_title=x_label,
        yaxis_title=y_label
    )
    return fig

def vis_side(df_scatter):
    if df_scatter is None or df_scatter.empty:
        st.warning("Ingen scatter-data tilgængelige.")
        return

    df_s = df_scatter.copy()
    df_s.columns = [c.upper() for c in df_s.columns]
    
    try:
        from data.season_show import SEASONNAME
        current_season = str(SEASONNAME).strip()
    except:
        current_season = "2025/2026"

    s_col = next((c for c in df_s.columns if 'SEASON' in c), None)
    if not s_col:
        st.error("Kunne ikke finde sæson-kolonne.")
        return

    df_current = df_s[df_s[s_col].astype(str).str.strip() == current_season].copy()

    # --- DEFINITION AF METRICS ---
    metric_options = {
        "MÅL FOR vs. MÅL IMOD": ("GOALS", "CONCEDEDGOALS"),
        "TOUCHES IN BOX vs. SKUD": ("TOUCHINBOX", "SHOTS"),
        "xG vs. MÅL FOR": ("XGSHOT", "GOALS"),
        "SKUD FOR vs. SKUD MOD": ("SHOTS", "SHOTSAGAINST")
    }

    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">SCATTERPLOTS</h3>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        leagues = sorted(df_current['COMPETITIONNAME'].unique()) if 'COMPETITIONNAME' in df_current.columns else []
        valgt_league = st.selectbox("Vælg Turnering", leagues)
    with c2:
        metric_type = st.selectbox("Vælg Analyse", list(metric_options.keys()))

    df_filtered = df_current[df_current['COMPETITIONNAME'] == valgt_league].copy()
    
    if not df_filtered.empty:
        x_raw, y_raw = metric_options[metric_type]
        
        for col in [x_raw, y_raw, 'MATCHES']:
            if col not in df_filtered.columns:
                df_filtered[col] = 0
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0)

        df_filtered['X_PER_GAME'] = df_filtered[x_raw] / df_filtered['MATCHES'].replace(0, 1)
        df_filtered['Y_PER_GAME'] = df_filtered[y_raw] / df_filtered['MATCHES'].replace(0, 1)

        fig = build_scatter_plot(df_filtered, metric_type)
        st.plotly_chart(fig, use_container_width=True)
