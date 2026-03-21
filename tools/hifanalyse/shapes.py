import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def tegn_bane(ax):
    # Tegn banens ramme (Opta bruger ofte 0-100 skala)
    ax.set_facecolor('#224422')
    plt.plot([0, 100, 100, 0, 0], [0, 0, 100, 100, 0], color="white", linewidth=2)
    plt.axvline(50, color="white", linewidth=2) # Midterlinje
    plt.plot(50, 50, 'o', color="white") # Midterprik
    circle = patches.Circle((50, 50), 9.15, color='white', fill=False, linewidth=2)
    ax.add_patch(circle)
    
    # Felter (Simple bokse til visualisering)
    plt.plot([0, 16.5, 16.5, 0], [25, 25, 75, 75], color="white") # Venstre felt
    plt.plot([100, 83.5, 83.5, 100], [25, 25, 75, 75], color="white") # Højre felt
    
    plt.xlim(-5, 105)
    plt.ylim(-5, 105)
    plt.axis('off')

def vis_side(analysis_package):
    st.title("⚽ Gennemsnitlige Positioner på Banen")
    
    df_shapes = analysis_package.get("remote_shapes", pd.DataFrame())
    if df_shapes.empty:
        st.warning("Ingen data fundet.")
        return

    # 1. Kamp-vælger
    kampe = df_shapes['MATCH_OPTAUUID'].unique()
    valgt_uuid = st.selectbox("Vælg kamp:", kampe)
    df_match = df_shapes[df_shapes['MATCH_OPTAUUID'] == valgt_uuid]

    # 2. Beregn gennemsnitlige positioner
    all_players = []
    for _, row in df_match.iterrows():
        raw_roles = row.get('SHAPE_ROLE')
        if not raw_roles: continue
        roles = json.loads(raw_roles) if isinstance(raw_roles, str) else raw_roles
        side = row.get('SHAPE_LABEL', 'Ukendt')
        for p in roles:
            p['Hold_Side'] = side
            all_players.append(p)

    if all_players:
        df_all = pd.DataFrame(all_players)
        df_all['X'] = pd.to_numeric(df_all['averageRolePositionX'])
        df_all['Y'] = pd.to_numeric(df_all['averageRolePositionY'])
        
        # Gruppering så vi får én prik per spiller
        df_avg = df_all.groupby(['Hold_Side', 'shirtNumber']).agg({
            'X': 'mean', 'Y': 'mean', 'roleDescription': 'first'
        }).reset_index()

        # 3. Visualisering på banen
        fig, ax = plt.subplots(figsize=(12, 8))
        tegn_bane(ax)

        hold_sider = df_avg['Hold_Side'].unique()
        farver = ['#e21a22', '#3498db'] # Rød og Blå

        for idx, side in enumerate(hold_sider[:2]):
            df_team = df_avg[df_avg['Hold_Side'] == side]
            
            # Vi spejler det ene hold så de står overfor hinanden
            # (Hvis X er 0-100, lader vi udeholdet angribe fra højre mod venstre)
            if idx == 1:
                df_team['X_plot'] = 100 - df_team['X']
                df_team['Y_plot'] = 100 - df_team['Y']
            else:
                df_team['X_plot'] = df_team['X']
                df_team['Y_plot'] = df_team['Y']

            # Tegn spillere
            ax.scatter(df_team['X_plot'], df_team['Y_plot'], s=400, color=farver[idx], edgecolors='white', zorder=5, label=side)
            
            # Tilføj numre på prikkerne
            for i, row in df_team.iterrows():
                ax.annotate(str(int(row['shirtNumber'])), (row['X_plot'], row['Y_plot']), 
                            color='white', weight='bold', ha='center', va='center', fontsize=10, zorder=6)

        plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2)
        st.pyplot(fig)

        # 4. Tabeller nedenunder
        st.divider()
        cols = st.columns(2)
        for idx, side in enumerate(hold_sider[:2]):
            with cols[idx]:
                st.write(f"**{side}**")
                st.dataframe(df_avg[df_avg['Hold_Side'] == side][['shirtNumber', 'X', 'Y']].round(1), use_container_width=True, hide_index=True)
    else:
        st.info("Kunne ikke tegne banen.")
