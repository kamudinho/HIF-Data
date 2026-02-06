import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import tkinter as tk
import numpy as np
import requests
from PIL import Image
import io
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
plt.rcParams['figure.facecolor'] = '#ffffff'


def hent_data():
    filnavn = 'HIF-data.xlsx'
    HIF_ID = 38331
    try:
        df_events = pd.read_excel(filnavn, sheet_name='Eventdata')
        df_events.columns = df_events.columns.str.strip().str.upper()
        df_shots = df_events[df_events['PRIMARYTYPE'].astype(str).str.contains('shot', case=False, na=False)].copy()
        df_kamp = pd.read_excel(filnavn, sheet_name='Kampdata')
        df_kamp.columns = df_kamp.columns.str.strip().str.upper()
        return df_shots, df_kamp.dropna(subset=['GOALS', 'SHOTS', 'TOUCHESINBOX', 'POSSESSIONPERCENT'])
    except Exception as e:
        print(f"Fejl: {e}");
        return None, None


df_all_shots, df_kampdata = hent_data()


def vis_komplet_rapport():
    if df_all_shots is None or df_kampdata is None: return

    HIF_ID = 38331
    HIF_RED, MOD_GRAY = '#df003b', '#555555'

    hif_rows = df_kampdata[df_kampdata['TEAM_WYID'] == HIF_ID]
    mod_rows = df_kampdata[df_kampdata['TEAM_WYID'] != HIF_ID]

    def get_avg(df, col):
        return df[col].mean() if not df.empty else 0.0

    h_stats = [get_avg(hif_rows, 'POSSESSIONPERCENT'), get_avg(hif_rows, 'SHOTS'), get_avg(hif_rows, 'GOALS'),
               get_avg(hif_rows, 'TOUCHESINBOX')]
    # Sikrer os at possession er en decimal (f.eks. 0.485)
    if h_stats[0] > 1: h_stats[0] /= 100

    m_stats = [1.0 - h_stats[0], get_avg(mod_rows, 'SHOTS'), get_avg(mod_rows, 'GOALS'),
               get_avg(mod_rows, 'TOUCHESINBOX')]

    fig = plt.figure(figsize=(18, 14))
    p_length, p_width = 140, 100
    pitch = VerticalPitch(pitch_type='custom', pitch_length=p_length, pitch_width=p_width,
                          half=True, goal_type='box', pitch_color='white',
                          line_color='#1a1a1a', linewidth=1.5)

    ax_left = fig.add_axes([0.01, 0.02, 0.48, 0.90])
    ax_right = fig.add_axes([0.51, 0.02, 0.48, 0.90])
    pitch.draw(ax=ax_left);
    pitch.draw(ax=ax_right)

    def tegn_skud(df, ax, is_hif):
        mask = df['TEAM_WYID'] == HIF_ID if is_hif else df['TEAM_WYID'] != HIF_ID
        temp = df[mask].copy()
        if not temp.empty:
            x = temp['LOCATIONX'] * (p_length / 100)
            y = temp['LOCATIONY'] * (p_width / 100)
            halfway = p_length / 2
            x_final = np.where(x < halfway, p_length - x, x)
            y_final = np.where(x < halfway, p_width - y, y)
            ax.scatter(y_final, x_final, s=40, edgecolors='#1a1a1a',
                       facecolors=HIF_RED if is_hif else MOD_GRAY, alpha=0.6, zorder=3, linewidth=0.5)

    tegn_skud(df_all_shots, ax_left, True)
    tegn_skud(df_all_shots, ax_right, False)

    def setup_header(x_pos, navn, logo_url, color, stats_list, logo_side="left"):
        plt.figtext(x_pos, 0.96, navn.upper(), fontsize=28, fontweight='bold', ha='center', color=color)
        stat_y = 0.92
        lbls = ["POSSESSION", "SKUD", "MÅL", "BERØRINGER I FELT"]
        offsets = [-0.16, -0.06, 0.04, 0.14]

        # HER ER RETTELSEN: {:.1f}% giver én decimal (f.eks. 49.5%)
        vals = [f"{stats_list[0] * 100:.1f}%", f"{stats_list[1]:.1f}", f"{stats_list[2]:.1f}", f"{stats_list[3]:.1f}"]

        for v, l, o in zip(vals, lbls, offsets):
            plt.figtext(x_pos + o, stat_y, v, fontsize=20, fontweight='bold', ha='center', color=color)
            plt.figtext(x_pos + o, stat_y - 0.02, l, fontsize=9, fontweight='bold', ha='center', color='gray')
        try:
            r = requests.get(logo_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            img = Image.open(io.BytesIO(r.content))
            logo_x = x_pos - 0.28 if logo_side == "left" else x_pos + 0.19
            logo_ax = fig.add_axes([logo_x, 0.90, 0.09, 0.09])
            logo_ax.imshow(img);
            logo_ax.axis('off')
        except:
            pass

    setup_header(0.26, "Hvidovre IF", "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png", HIF_RED, h_stats,
                 "left")
    setup_header(0.74, "Modstandere", "https://cdn5.wyscout.com/photos/team/public/ndteam_120x120.png", MOD_GRAY,
                 m_stats, "right")

    plt.show()


root = tk.Tk();
root.title("HIF Performance Rapport")
tk.Button(root, text="Generér Rapport", command=vis_komplet_rapport, bg="#df003b", font=('Arial', 11, 'bold')).pack(
    expand=True, pady=20)
root.mainloop()