import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def tegn_fodboldbane(ax):
    # Opta bruger ofte en 0-100 skala for både X og Y
    bane_farve = "#224422" # Mørkegrøn
    linje_farve = "white"
    
    # Baggrund
    ax.set_facecolor(bane_farve)
    
    # Yderlinjer
    plt.plot([0, 0, 100, 100, 0], [0, 100, 100, 0, 0], color=linje_farve, linewidth=2)
    
    # Midterlinje og cirkel
    plt.axvline(50, color=linje_farve, linewidth=2)
    midter_cirkel = patches.Circle((50, 50), 9.15, color=linje_farve, fill=False, linewidth=2)
    ax.add_patch(midter_cirkel)
    plt.plot(50, 50, 'o', color=linje_farve)
    
    # Straffesparksfelter (Venstre)
    plt.plot([0, 16.5, 16.5, 0], [21.1, 21.1, 78.9, 78.9], color=linje_farve, linewidth=2)
    plt.plot([0, 5.5, 5.5, 0], [36.8, 36.8, 63.2, 63.2], color=linje_farve, linewidth=2)
    
    # Straffesparksfelter (Højre)
    plt.plot([100, 83.5, 83.5, 100], [21.1, 21.1, 78.9, 78.9], color=linje_farve, linewidth=2)
    plt.plot([100, 94.5, 94.5, 100], [36.8, 36.8, 63.2, 63.2], color=linje_farve, linewidth=2)
    
    # Indstillinger for aksen
    plt.xlim(-5, 105)
    plt.ylim(-5, 105)
    ax.axis('off')

def vis_side(analysis_package):
    st.title("⚽ Gennemsnitlige Positioner")
    
    df_shapes = analysis_package.get("remote_shapes", pd.DataFrame())
    if df_shapes.empty:
        st.warning("Ingen data fundet.")
        return

    kampe = df_shapes['MATCH_OPTAUUID'].unique()
    valgt_uuid = st.selectbox("Vælg kamp:", kampe)
    df_match = df_shapes[df_shapes['MATCH_OPTAUUID'] == valgt_uuid]

    # Udpak og beregn gennemsnit
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
        df_avg = pd.DataFrame(all_players)
        df_avg['X'] = pd.to_numeric(df_avg['averageRolePositionX'])
        df_avg['Y'] = pd.to_numeric(df_avg['averageRolePositionY'])
        
        # Gruppér for at få én prik per spiller
        df_plot = df_avg.groupby(['Hold_Side', 'shirtNumber']).agg({'X': 'mean', 'Y': 'mean'}).reset_index()

        # TEGN BANEN
        fig, ax = plt.subplots(figsize=(10, 7))
        tegn_fodboldbane(ax)

        # Plot holdene
        hold_sider = df_plot['Hold_Side'].unique()
        farver = {'Home': '#e21a22', 'Away': '#3498db'} # Tilpas evt. til dine labels

        for side in hold_sider:
            df_team = df_plot[df_plot['Hold_Side'] == side]
            color = farver.get(side, '#999999')
            
            # Scatter plot for spillerne
            ax.scatter(df_team['X'], df_team['Y'], s=450, color=color, edgecolors='white', linewidth=2, zorder=5)
            
            # Tilføj numre
            for _, row in df_team.iterrows():
                ax.annotate(str(int(row['shirtNumber'])), (row['X'], row['Y']), 
                            color='white', weight='bold', ha='center', va='center', zorder=6)

        st.pyplot(fig)
    else:
        st.info("Ingen spillerdata.")
