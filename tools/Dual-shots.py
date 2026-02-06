import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import tkinter as tk
import numpy as np
import requests
from PIL import Image
import io
import ssl

# --- GLOBALE INDSTILLINGER ---
HIF_RED = '#df003b'
BG_WHITE = '#ffffff'
TEXT_DARK = '#1a1a1a'
TEXT_GRAY = '#6a6a6a'

ssl._create_default_https_context = ssl._create_unverified_context


def hent_data():
    filnavn = 'HIF-data.xlsx'
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


def lav_enkelt_rapport(is_hif):
    if df_kampdata is None: return
    HIF_ID = 38331

    if is_hif:
        rows = df_kampdata[df_kampdata['TEAM_WYID'] == HIF_ID]
        shot_mask = df_all_shots['TEAM_WYID'] == HIF_ID
        navn = "Hvidovre IF"
        logo_url = "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"
    else:
        rows = df_kampdata[df_kampdata['TEAM_WYID'] != HIF_ID]
        shot_mask = df_all_shots['TEAM_WYID'] != HIF_ID
        navn = "Modstandere"
        logo_url = "https://cdn5.wyscout.com/photos/team/public/ndteam_120x120.png"

    # Stats beregning
    hif_poss = df_kampdata[df_kampdata['TEAM_WYID'] == HIF_ID]['POSSESSIONPERCENT'].mean()
    if hif_poss > 1: hif_poss /= 100
    poss = hif_poss if is_hif else (1.0 - hif_poss)

    stats = [
        {"val": f"{rows['GOALS'].mean():.1f}", "lbl": "MÅL"},
        {"val": f"{poss * 100:.1f}%", "lbl": "POSSESSION"},
        {"val": f"{rows['SHOTS'].mean():.1f}", "lbl": "SKUD"},
        {"val": f"{rows['TOUCHESINBOX'].mean():.1f}", "lbl": "BERØRINGER I FELT"}
    ]

    # FIGUR SETUP
    fig = plt.figure(figsize=(18, 10), facecolor=BG_WHITE)
    p_length, p_width = 140, 100
    pitch = VerticalPitch(pitch_type='custom', pitch_length=p_length, pitch_width=p_width,
                          half=True, pitch_color='white', line_color='#1a1a1a',
                          linewidth=1.5, goal_type='box')

    ax_pitch = fig.add_axes([0.05, 0.05, 0.60, 0.82])
    pitch.draw(ax=ax_pitch)

    # Skud på banen
    temp_shots = df_all_shots[shot_mask].copy()
    if not temp_shots.empty:
        x_scaled = temp_shots['LOCATIONX'] * (p_length / 100)
        y_scaled = temp_shots['LOCATIONY'] * (p_width / 100)
        x_f = np.where(x_scaled < 70, p_length - x_scaled, x_scaled)
        y_f = np.where(x_scaled < 70, p_width - y_scaled, y_scaled)
        ax_pitch.scatter(y_f, x_f, s=120, facecolors=HIF_RED, edgecolors=TEXT_DARK,
                         alpha=0.7, linewidth=1, zorder=4)

    # HEADER (Logo og Navn flugter nu perfekt)
    plt.figtext(0.14, 0.93, navn.upper(), fontsize=38, fontweight='900', color=TEXT_DARK)
    plt.figtext(0.14, 0.895, f"{navn} | Performance Rapport", fontsize=18, color=TEXT_GRAY)

    try:
        r = requests.get(logo_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        img = Image.open(io.BytesIO(r.content))
        logo_ax = fig.add_axes([0.045, 0.88, 0.09, 0.09])
        logo_ax.imshow(img);
        logo_ax.axis('off')
    except:
        pass

    # --- STATS KOLONNE (Rød fed tekst, grå label under) ---
    x_pos_base = 0.78  # Placeret til højre for banen
    y_pos = 0.76

    for item in stats:
        # Det store røde tal
        plt.figtext(x_pos_base, y_pos, item["val"], color=HIF_RED,
                    fontsize=32, fontweight='900', ha='center', va='center')

        # Den grå tekst lige under
        plt.figtext(x_pos_base, y_pos - 0.035, item["lbl"], color=TEXT_GRAY,
                    fontsize=14, fontweight='800', ha='center', va='center')

        y_pos -= 0.18  # Vertikal afstand til næste stat

    plt.show()


def kør_begge():
    lav_enkelt_rapport(True)
    lav_enkelt_rapport(False)


root = tk.Tk();
root.title("HIF Performance");
root.geometry("300x120")
tk.Button(root, text="Generér Rapport", command=kør_begge, bg=HIF_RED, fg="white", font=('Arial', 11, 'bold')).pack(
    expand=True)
root.mainloop()