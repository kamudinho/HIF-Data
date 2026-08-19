import streamlit as st
import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import requests
from PIL import Image
from io import BytesIO
from mplsoccer import Pitch, VerticalPitch
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib import colors
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

HIF_RED = '#cc0000'
HIF_NAVN = "Hvidovre"  # Nøglen i TEAMS-dictet - Hvidovre IF skal altid kunne slås op herfra
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "2mb332vncy4450vu14paj8844"
PLAYER_FILE = 'data/players/1div_overskrivning.csv'

@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def universal_decode(text):
    if not isinstance(text, str): return text
    try: return text.encode('latin1').decode('utf-8')
    except: return text

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()

    sql = (
        "WITH BaseEvents AS ("
        "    SELECT "
        "        e.EVENT_OPTAUUID, e.MATCH_OPTAUUID, e.EVENT_EVENTID,"
        "        e.EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,"
        "        e.EVENT_TYPEID,"
        "        TRIM(e.PLAYER_OPTAUUID) AS PLAYER_UUID,"
        "        e.PLAYER_NAME,"
        "        e.EVENT_X, e.EVENT_Y,"
        "        LEAD(TRIM(e.PLAYER_OPTAUUID), 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_UUID,"
        "        LEAD(e.PLAYER_NAME, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_NAME,"
        "        LEAD(e.EVENT_CONTESTANT_OPTAUUID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_TEAM,"
        "        LEAD(e.EVENT_TYPEID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_TYPE,"
        "        LEAD(e.EVENT_TYPEID, 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P2_TYPE,"
        "        LEAD(e.EVENT_TYPEID, 3) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P3_TYPE"
        "    FROM " + DB + ".OPTA_EVENTS e"
        "    WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '" + LIGA_UUID + "'"
        "),"
        "Quals AS ("
        "    SELECT "
        "        EVENT_OPTAUUID,"
        "        MAX(CASE WHEN QUALIFIER_QID = 107 THEN 'Indkast'"
        "                 WHEN QUALIFIER_QID = 6 THEN 'Hjørnespark'"
        "                 WHEN QUALIFIER_QID = 5 THEN 'Frispark' END) AS TYPE_NAVN,"
        "        MAX(CASE WHEN QUALIFIER_QID = 140 THEN QUALIFIER_VALUE END) AS ENDX,"
        "        MAX(CASE WHEN QUALIFIER_QID = 141 THEN QUALIFIER_VALUE END) AS ENDY,"
        "        MAX(CASE WHEN QUALIFIER_QID = 223 THEN 'Indadskruet'"
        "                 WHEN QUALIFIER_QID = 224 THEN 'Udadskruet'"
        "                 WHEN QUALIFIER_QID = 225 THEN 'Lige' END) AS SPARK_TYPE,"
        "        MAX(CASE WHEN QUALIFIER_QID = 152 THEN 'Direkte'"
        "                 WHEN QUALIFIER_QID = 241 THEN 'Indirekte' END) AS FRISPARK_TYPE,"
        "        MAX(CASE WHEN QUALIFIER_QID = 155 THEN 'Chipped' END) AS LEVERING_TYPE"
        "    FROM " + DB + ".OPTA_QUALIFIERS"
        "    WHERE QUALIFIER_QID IN (5, 6, 107, 140, 141, 152, 155, 223, 224, 225, 241)"
        "    GROUP BY EVENT_OPTAUUID"
        ") "
        "SELECT b.*, q.TYPE_NAVN, q.ENDX, q.ENDY, q.SPARK_TYPE, q.FRISPARK_TYPE, q.LEVERING_TYPE "
        "FROM BaseEvents b "
        "JOIN Quals q ON b.EVENT_OPTAUUID = q.EVENT_OPTAUUID "
        "WHERE q.TYPE_NAVN IS NOT NULL"
    )

    try:
        df = conn.query(sql)
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [c.upper() for c in df.columns]
        df['PLAYER_NAME'] = df['PLAYER_NAME'].apply(universal_decode)
        df['P1_NAME'] = df['P1_NAME'].apply(universal_decode)

        try:
            df_lookup = pd.read_csv(PLAYER_FILE, encoding='utf-8-sig')
            df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
            df_lookup['NAVN'] = df_lookup['NAVN'].apply(universal_decode)
            name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
        except: name_map = {}

        df['TAGER_NAVN'] = df.apply(lambda x: name_map.get(str(x['PLAYER_UUID']).strip(), x['PLAYER_NAME']), axis=1)

        def find_target(row):
            if row['P1_TEAM'] == row['TEAM_UUID'] and row['P1_UUID'] != row['PLAYER_UUID']:
                return name_map.get(str(row['P1_UUID']).strip(), row['P1_NAME'])
            return None

        df['MODTAGER'] = df.apply(find_target, axis=1)
        shot_types = [13, 14, 15, 16]
        df['ER_AFSLUTNING'] = df.apply(lambda x: 1 if x['P1_TYPE'] in shot_types or x['P2_TYPE'] in shot_types or x['P3_TYPE'] in shot_types else 0, axis=1)

        def get_udfoerelse(row):
            if row['TYPE_NAVN'] == 'Hjørnespark':
                return row['SPARK_TYPE'] if pd.notna(row['SPARK_TYPE']) else 'Standard / Ukendt'
            elif row['TYPE_NAVN'] == 'Frispark':
                return row['FRISPARK_TYPE'] if pd.notna(row['FRISPARK_TYPE']) else 'Åbent / Indlæg'
            elif row['TYPE_NAVN'] == 'Indkast':
                return row['LEVERING_TYPE'] if pd.notna(row['LEVERING_TYPE']) else 'Alm. aflevering'
            return 'Ukendt'

        df['UDFOERELSE'] = df.apply(get_udfoerelse, axis=1)
        return df
    except Exception as e:
        st.error(f"SQL-fejl: {e}")
        return pd.DataFrame()

def get_summary_stats(df_subset, group_col):
    if df_subset.empty:
        return pd.DataFrame()

    total_actions = len(df_subset)
    df_subset = df_subset.copy()
    df_subset['ER_SUCCES'] = df_subset['MODTAGER'].notna().astype(int)
    df_subset['ER_AFSLUTNING'] = pd.to_numeric(df_subset.get('ER_AFSLUTNING', 0), errors='coerce').fillna(0).astype(int)

    agg = df_subset.groupby(group_col).agg(
        Antal=(group_col, 'count'),
        Succes_Sum=('ER_SUCCES', 'sum'),
        Afslutning_Sum=('ER_AFSLUTNING', 'sum')
    ).reset_index()

    agg['Succes %'] = agg.apply(
        lambda row: int(round((row['Succes_Sum'] / row['Antal']) * 100)) if row['Antal'] > 0 else 0, axis=1
    )

    agg['Med afslutning'] = agg['Afslutning_Sum']

    agg['Andel'] = agg.apply(
        lambda row: f"{round((row['Antal'] / total_actions) * 100, 1)}%" if total_actions > 0 else "0%", axis=1
    )

    agg = agg.sort_values(by='Antal', ascending=False)

    if group_col == 'KLUB_NAVN':
        agg = agg[['KLUB_NAVN', 'Antal', 'Succes %', 'Med afslutning', 'Andel']]
        agg.columns = ['Hold', 'Antal', 'Succes %', 'Med afslutning', 'Andel']
    else:
        agg = agg[['TAGER_NAVN', 'Antal', 'Succes %', 'Med afslutning', 'Andel']]
        agg.columns = ['Spiller', 'Antal', 'Succes %', 'Med afslutning', 'Andel']

    return agg

# =========================================================================
# Hjælpefunktioner: opsummering, logoer, modtagerzoner og PDF-eksport
# =========================================================================

def get_zone(y):
    """Oversætter en ENDY-koordinat til en simpel zonebetegnelse."""
    try:
        y = float(y)
    except (TypeError, ValueError):
        return "Ukendt"
    if y < 33: return "Venstre"
    if y > 66: return "Højre"
    return "Center"

def opsummering_linjer(df_subset, navn):
    """
    Genererer en liste af letlæselige, coach-venlige sætninger ud fra et
    datasæt af standardsituationer - én sætning pr. dødboldtype der har data.
    Rent regelbaseret - bruger value_counts på tallene i datasættet.
    """
    if df_subset is None or df_subset.empty:
        return [f"Der er ingen registrerede standardsituationer for {navn} i det valgte data."]

    linjer = []
    for sp_type in ["Hjørnespark", "Frispark", "Indkast"]:
        df_t = df_subset[df_subset['TYPE_NAVN'] == sp_type].copy()
        if df_t.empty:
            continue

        antal = len(df_t)
        succes_pct = int(round((df_t['MODTAGER'].notna().sum() / antal) * 100)) if antal else 0
        afslutninger = int(pd.to_numeric(df_t.get('ER_AFSLUTNING', 0), errors='coerce').fillna(0).sum())

        taker_counts = df_t['TAGER_NAVN'].value_counts()
        top_taker = taker_counts.idxmax() if not taker_counts.empty else None
        top_taker_n = int(taker_counts.max()) if top_taker else 0

        df_mod = df_t[df_t['MODTAGER'].notna()]
        mod_counts = df_mod['MODTAGER'].value_counts()
        top_target = mod_counts.idxmax() if not mod_counts.empty else None

        df_t['ZONE'] = df_t['ENDY'].apply(get_zone)
        zone_counts = df_t['ZONE'].value_counts()
        top_zone = zone_counts.idxmax() if not zone_counts.empty else None

        udf_counts = df_t['UDFOERELSE'].value_counts()
        top_udf = udf_counts.idxmax() if not udf_counts.empty else None

        dele = []
        if top_udf:
            dele.append(f"primær udførelse er *{str(top_udf).lower()}*")
        if top_taker:
            dele.append(f"hyppigste tager er **{top_taker}** ({top_taker_n} stk.)")
        if top_target:
            dele.append(f"hyppigste modtager er **{top_target}**")
        if top_zone == "Center":
            dele.append("mest benyttede zone er **centralt**")
        elif top_zone:
            dele.append(f"mest benyttede zone er **{top_zone.lower()} side**")

        saetning = f"**{sp_type}** ({antal} stk., {succes_pct}% succes, {afslutninger} med afslutning): " + ", ".join(dele) + "."
        linjer.append(saetning)

    if not linjer:
        return [f"Der er ingen registrerede standardsituationer for {navn} i det valgte data."]
    return linjer

def get_top3_dict(df_subset):
    """Returnerer {sp_type: [(spiller, antal), ...]} - top 3 tagere pr. dødboldtype."""
    resultat = {}
    for sp_type in ["Hjørnespark", "Frispark", "Indkast"]:
        sub = df_subset[df_subset['TYPE_NAVN'] == sp_type]
        resultat[sp_type] = list(sub['TAGER_NAVN'].value_counts().head(3).items()) if not sub.empty else []
    return resultat

def get_defensive_events(df_all, team_navn, uuid_to_name):
    """
    Finder modstanderes dødbolde imod et givent hold.
    Datasættet logger kun events for det hold, der UDFØRER dødbolden, så
    vi finder først alle kampe holdet selv optræder i (som udførende af
    mindst én dødbold), og tager derefter alt i de kampe, som IKKE er
    udført af holdet selv - det er modstanderens angreb.

    OBS: hvis en kamp findes, hvor holdet slet ingen dødbolde selv tog,
    vil den kamp ikke fanges her (sjældent, men muligt).
    """
    name_to_uuid = {v: k for k, v in uuid_to_name.items()}
    team_uuid = name_to_uuid.get(team_navn)
    if not team_uuid or df_all.empty:
        return pd.DataFrame()

    kampe_med_hold = df_all[df_all['TEAM_UUID'].str.upper() == team_uuid.upper()]['MATCH_OPTAUUID'].unique()
    df_kampe = df_all[df_all['MATCH_OPTAUUID'].isin(kampe_med_hold)]
    df_defensiv = df_kampe[df_kampe['TEAM_UUID'].str.upper() != team_uuid.upper()].copy()
    return df_defensiv

def render_header_logos(team_a_navn, team_b_navn=None):
    """Viser logo-header i Streamlit. Hvis to hold gives, vises de side om side med et 'VS' imellem."""
    info_a = TEAMS.get(team_a_navn, {})
    logo_a = get_logo_img(info_a.get('opta_uuid'))

    if team_b_navn and team_b_navn != team_a_navn:
        c1, c2, c3 = st.columns([1, 0.4, 1])
        with c1:
            if logo_a: st.image(logo_a, width=70)
            st.caption(team_a_navn)
        with c2:
            st.markdown("<div style='text-align:center; padding-top:22px; font-weight:bold; color:#999;'>VS</div>", unsafe_allow_html=True)
        with c3:
            info_b = TEAMS.get(team_b_navn, {})
            logo_b = get_logo_img(info_b.get('opta_uuid'))
            if logo_b: st.image(logo_b, width=70)
            st.caption(team_b_navn)
    else:
        if logo_a: st.image(logo_a, width=70)
        st.caption(team_a_navn)

def build_corner_zone_figs(df_subset, titel_prefix=""):
    """
    Bygger to matplotlib-figurer med modtagerzoner for hjørnespark - én for
    spark taget fra venstre side, én for spark taget fra højre side.
    Returnerer {"Venstre side": (fig_eller_None, antal), "Højre side": (fig_eller_None, antal)}.
    Figurerne st.pyplot'es IKKE her, så de kan genbruges både i Streamlit-visningen og i PDF-eksporten.
    """
    df_corners = df_subset[df_subset['TYPE_NAVN'] == 'Hjørnespark'].copy()
    for c in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']:
        df_corners[c] = pd.to_numeric(df_corners[c], errors='coerce')
    df_corners = df_corners.dropna(subset=['ENDX', 'ENDY'])

    resultat = {}
    for side_navn, side_df in [
        ("Venstre side", df_corners[df_corners['EVENT_Y'] > 50]),
        ("Højre side", df_corners[df_corners['EVENT_Y'] <= 50]),
    ]:
        if side_df.empty:
            resultat[side_navn] = (None, 0)
            continue
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='white', line_color='#333333', linewidth=1.2)
        fig, ax = pitch.draw(figsize=(5, 5))
        pitch.hexbin(side_df['ENDX'], side_df['ENDY'], ax=ax, edgecolors='#ffffff', gridsize=(7, 7), cmap='Reds', alpha=0.8)
        titel = f"{titel_prefix}{side_navn} ({len(side_df)} hjørnespark)".strip()
        ax.text(50, 102, titel, fontsize=7, fontweight='bold', color='#333333', ha='center')
        resultat[side_navn] = (fig, len(side_df))
    return resultat

# --- PDF-eksport ---

def md_to_html(text):
    """Konverterer simpel markdown (**fed**, *kursiv*) til ReportLab's markup, så opsummeringen kan genbruges i PDF'en."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    return text

def pil_to_rlimage(pil_img, width_mm=22):
    buf = BytesIO()
    pil_img.convert("RGB").save(buf, format='PNG')
    buf.seek(0)
    ratio = (pil_img.height / pil_img.width) if pil_img.width else 1
    return RLImage(buf, width=width_mm * mm, height=width_mm * ratio * mm)

def fig_to_rlimage(fig, width_mm=80):
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    return RLImage(buf, width=width_mm * mm, height=width_mm * mm)

def generate_modstanderrapport_pdf(hif_navn, modstander_navn, opsummering, top3_data, corner_figs):
    """Bygger en komplet PDF-rapport: logoer, opsummering, top 3-tagere og modtagerzoner (venstre/højre)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15 * mm, bottomMargin=15 * mm, leftMargin=18 * mm, rightMargin=18 * mm)
    styles = getSampleStyleSheet()
    story = []

    hif_logo = get_logo_img(TEAMS.get(hif_navn, {}).get('opta_uuid'))
    mod_logo = get_logo_img(TEAMS.get(modstander_navn, {}).get('opta_uuid'))

    logo_row = [
        pil_to_rlimage(hif_logo, 22) if hif_logo else Paragraph(hif_navn, styles['Normal']),
        Paragraph("<para align='center'><b>VS</b></para>", styles['Normal']),
        pil_to_rlimage(mod_logo, 22) if mod_logo else Paragraph(modstander_navn, styles['Normal']),
    ]
    logo_table = Table([logo_row], colWidths=[45 * mm, 25 * mm, 45 * mm])
    logo_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    story.append(logo_table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph(f"Modstanderrapport: {modstander_navn}", styles['Title']))
    story.append(Paragraph(f"{hif_navn} forbereder sig mod {modstander_navn}", styles['Normal']))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Opsummering", styles['Heading2']))
    for linje in opsummering:
        story.append(Paragraph("• " + md_to_html(linje), styles['Normal']))
        story.append(Spacer(1, 2 * mm))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Top 3-tagere pr. type", styles['Heading2']))
    table_data = [["Type", "Spiller", "Antal"]]
    for sp_type, rows in top3_data.items():
        if not rows:
            table_data.append([sp_type, "-", "-"])
        else:
            for i, (navn, antal) in enumerate(rows):
                table_data.append([sp_type if i == 0 else "", navn, str(antal)])
    t = Table(table_data, colWidths=[32 * mm, 90 * mm, 20 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Modtagerzoner ved hjørnespark", styles['Heading2']))
    fig_v, _ = corner_figs.get("Venstre side", (None, 0))
    fig_h, _ = corner_figs.get("Højre side", (None, 0))
    if fig_v is not None or fig_h is not None:
        img_row = [
            fig_to_rlimage(fig_v, 78) if fig_v is not None else Paragraph("Ingen data", styles['Normal']),
            fig_to_rlimage(fig_h, 78) if fig_h is not None else Paragraph("Ingen data", styles['Normal']),
        ]
        img_table = Table([img_row], colWidths=[85 * mm, 85 * mm])
        img_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        story.append(img_table)
    else:
        story.append(Paragraph("Ingen hjørnespark-data tilgængelig.", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer

def render_setpiece_analysis(df_team, sp_type, t_sel):
    t_info = next((info for name, info in TEAMS.items() if name == t_sel), None)
    hold_logo = get_logo_img(t_info.get('opta_uuid') if t_info else None)

    f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.2, 1])
    with f1:
        p_list = ["Alle spillere"] + sorted(df_team[df_team['TYPE_NAVN'] == sp_type]['TAGER_NAVN'].unique().tolist())
        p_sel = st.selectbox(f"Spiller ({sp_type})", p_list, key=f"sb_p_{sp_type}")
    with f2:
        side_sel = st.selectbox(f"Side ({sp_type})", ["Begge sider", "Venstre side", "Højre side"], key=f"sb_side_{sp_type}")
    with f3:
        kun_afslutning = st.selectbox(f"Filter ({sp_type})", ["Alle", "Kun med afslutning"], key=f"sb_shot_{sp_type}")
    with f4:
        vis_mode = st.selectbox(f"Visning ({sp_type})", ["Zoner + Pile", "Kun Zoner", "Kun Pile"], key=f"sb_m_{sp_type}")

    mask = (df_team['TYPE_NAVN'] == sp_type)
    if p_sel != "Alle spillere": mask &= (df_team['TAGER_NAVN'] == p_sel)

    df_plot = df_team[mask].copy()
    df_plot = df_plot[~((df_plot['EVENT_X'] == 0) & (df_plot['EVENT_Y'] == 0))]

    for c in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']:
        df_plot[c] = pd.to_numeric(df_plot[c], errors='coerce')

    if side_sel == "Venstre side":
        df_plot = df_plot[df_plot['EVENT_Y'] > 50]
    elif side_sel == "Højre side":
        df_plot = df_plot[df_plot['EVENT_Y'] <= 50]

    if kun_afslutning == "Kun med afslutning":
        df_plot = df_plot[df_plot['ER_AFSLUTNING'] == 1]

    total = len(df_plot)
    succes = int(df_plot['MODTAGER'].notna().sum())
    pct = round((succes / total * 100), 0) if total > 0 else 0

    col_p, col_s = st.columns([2.5, 1.5])

    with col_p:
        t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)

        if sp_type == "Hjørnespark":
            pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='white', line_color='#333333', linewidth=1.5)
            fig, ax = pitch.draw(figsize=(7, 7))

            ax.text(93.0, 56.0, f"{sp_type.upper()} ({side_sel.upper()})", fontsize=7, fontweight='bold', color='#555555', va='center')
            spiller_tekst = f"Spiller: {p_sel}" if p_sel != "Alle spillere" else "Alle spillere"
            stats_line = f"{spiller_tekst} — {total} aktioner ({int(pct)}% succes)"
            ax.text(93.0, 53.0, stats_line, fontsize=7, color='#666666', va='center')

            if hold_logo:
                ax.text(93.0, 58.0, t_sel.upper(), fontsize=8, fontweight='bold', color='#222222', va='center')
                ax_logo = ax.inset_axes([93.0, 56.0, 4.5, 4.5], transform=ax.transData)
                ax_logo.imshow(hold_logo)
                ax_logo.axis('off')
        else:
            pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#333333', linewidth=1.5)
            fig, ax = pitch.draw(figsize=(9, 6))
            if hold_logo:
                ax_logo = ax.inset_axes([3.0, 91.0, 6.0, 6.0], transform=ax.transData)
                ax_logo.imshow(hold_logo)
                ax_logo.axis('off')
                ax.text(11.0, 92.0, t_sel.upper(), fontsize=8, fontweight='bold', color='#222222', va='center')
            ax.text(3.0, 87.0, f"{sp_type.upper()} ({side_sel.upper()})", fontsize=7, fontweight='bold', color='#555555', va='center')
            spiller_tekst = f"Spiller: {p_sel}" if p_sel != "Alle spillere" else "Alle spillere"
            stats_line = f"{spiller_tekst} — {total} aktioner ({int(pct)}% succes)"
            ax.text(3.0, 84.0, stats_line, fontsize=7, color='#666666', va='center')

        x = df_plot['EVENT_X']
        y = df_plot['EVENT_Y']
        end_x = df_plot['ENDX']
        end_y = df_plot['ENDY']

        if not df_plot.dropna(subset=['ENDX', 'ENDY']).empty:
            if "Zoner" in vis_mode:
                pitch.hexbin(end_x, end_y, ax=ax, edgecolors='#ffffff', gridsize=(8, 8), cmap='Reds', alpha=0.65)
            if "Pile" in vis_mode:
                pitch.arrows(x, y, end_x, end_y, color=t_color, ax=ax, width=1.5, headwidth=3, headlength=3, alpha=0.5)
                pitch.scatter(x, y, ax=ax, color=t_color, s=25, alpha=0.7)

        st.pyplot(fig, clear_figure=True)

    with col_s:
        st.caption("**Top 5-servere**")
        df_server_base = df_team[df_team['TYPE_NAVN'] == sp_type].copy()
        total_team_actions = len(df_server_base)

        df_server_base['ER_SUCCES'] = df_server_base['MODTAGER'].notna().astype(int)
        df_server_base['ER_AFSLUTNING'] = pd.to_numeric(df_server_base.get('ER_AFSLUTNING', 0), errors='coerce').fillna(0).astype(int)

        server_agg = df_server_base.groupby('TAGER_NAVN').agg(
            Antal=('TAGER_NAVN', 'count'),
            Succes_Sum=('ER_SUCCES', 'sum'),
            Afslutning_Sum=('ER_AFSLUTNING', 'sum')
        ).reset_index()

        server_agg['Succes'] = server_agg.apply(
            lambda row: f"{int(round((row['Succes_Sum'] / row['Antal']) * 100))}%" if row['Antal'] > 0 else "0%", axis=1
        )

        server_agg['Andel'] = server_agg.apply(
            lambda row: f"{round((row['Antal'] / total_team_actions) * 100, 1)}%" if total_team_actions > 0 else "0%", axis=1
        )

        server_agg = server_agg.sort_values(by='Antal', ascending=False).head(5)
        server_agg = server_agg[['TAGER_NAVN', 'Antal', 'Succes', 'Afslutning_Sum', 'Andel']]
        server_agg.columns = ['Spiller', 'Antal', 'Succes', 'Afslutning', 'Andel']
        st.dataframe(server_agg, use_container_width=True, hide_index=True)

        st.caption("**Top 5-modtagere**")
        df_mod_base = df_team[(df_team['TYPE_NAVN'] == sp_type) & (df_team['MODTAGER'].notna())].copy()
        total_mod_team = len(df_mod_base)

        df_mod_base['ER_AFSLUTNING'] = pd.to_numeric(df_mod_base.get('ER_AFSLUTNING', 0), errors='coerce').fillna(0).astype(int)

        mod_agg = df_mod_base.groupby('MODTAGER').agg(
            Antal=('MODTAGER', 'count'),
            Afslutning_Sum=('ER_AFSLUTNING', 'sum')
        ).reset_index()

        mod_agg['Andel'] = mod_agg.apply(
            lambda row: f"{round((row['Antal'] / total_mod_team) * 100, 1)}%" if total_mod_team > 0 else "0%", axis=1
        )

        mod_agg = mod_agg.sort_values(by='Antal', ascending=False).head(5)
        mod_agg = mod_agg[['MODTAGER', 'Antal', 'Afslutning_Sum', 'Andel']]
        mod_agg.columns = ['Modtager', 'Antal', 'Afslutning', 'Andel']
        st.dataframe(mod_agg, use_container_width=True, hide_index=True)

def vis_side():
    df_all = load_setpiece_data()
    if df_all.empty: st.warning("Ingen data fundet."); return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    c_title, c_drop = st.columns([3, 1])
    with c_title:
        st.caption("### Standardsituationer")
    with c_drop:
        default_idx = teams.index("Hvidovre") if "Hvidovre" in teams else 0
        t_sel = st.selectbox("Vælg hold", teams, index=default_idx, key="main_team_selectbox", label_visibility="collapsed")

    df_team_selected = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    tabs = st.tabs([
        "Analyse", "Holdoversigt", "Spilleroversigt", "Hjørnespark", "Frispark", "Indkast",
        "Modstanderrapport", "Sammenligning", "Defensivt"
    ])
    col_cfg = {"Succes %": st.column_config.ProgressColumn("Succes %", format="%d%%", min_value=0, max_value=100)}

    with tabs[0]:
        st.caption(f"### Analyse af standardsituationer: {t_sel}")

        st.markdown("##### Opsummering")
        for linje in opsummering_linjer(df_team_selected, t_sel):
            st.markdown(f"- {linje}")
        st.markdown("---")

        col_text, col_stats = st.columns([1.2, 1.8])

        with col_text:
            st.markdown("##### Overordnet udførelse og fordeling")
            total_sp = len(df_team_selected)
            top_type = df_team_selected['TYPE_NAVN'].value_counts().idxmax() if total_sp else None
            intro = f"{t_sel} har {total_sp} registrerede standardsituationer i det valgte data"
            if top_type:
                intro += f", hvoraf **{top_type.lower()}** er den hyppigste type"
            intro += ". Herunder ses fordelingen mellem hjørnespark, frispark og indkast, hvordan de udføres, samt hvilke zoner der oftest rammes."
            st.markdown(intro)

            df_team_selected['ZONE'] = df_team_selected['ENDY'].apply(lambda y: "Venstre" if float(y or 0) < 33 else ("Højre" if float(y or 0) > 66 else "Center"))

            st.write("**Fordeling af udførelse / sparketype:**")
            udf_counts = df_team_selected['UDFOERELSE'].value_counts()
            for udf_type, count in udf_counts.items():
                st.write(f"- **{udf_type}**: {count} stk.")

            st.write("\n**Mest benyttede modtager-zoner:**")
            zone_counts = df_team_selected['ZONE'].value_counts()
            for zone, count in zone_counts.items():
                st.write(f"- **{zone} zone**: {count} aktioner")

        with col_stats:
            total_team_sets = len(df_team_selected)
            tot_hj = len(df_team_selected[df_team_selected['TYPE_NAVN'] == 'Hjørnespark'])
            tot_fr = len(df_team_selected[df_team_selected['TYPE_NAVN'] == 'Frispark'])
            tot_in = len(df_team_selected[df_team_selected['TYPE_NAVN'] == 'Indkast'])

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Samlede", total_team_sets)
            m2.metric("Hjørne", tot_hj)
            m3.metric("Frispark", tot_fr)
            m4.metric("Indkast", tot_in)

            st.markdown("---")
            st.caption("Aktioner fordelt på type og udførelse")
            if not df_team_selected.empty:
                exec_table = df_team_selected.groupby(['TYPE_NAVN', 'UDFOERELSE']).size().unstack(fill_value=0)
                st.dataframe(exec_table, use_container_width=True)
            else:
                st.info("Ingen data tilgængelig.")

    with tabs[1]:
        col_content, col_control = st.columns([3, 1])
        with col_control:
            c = st.segmented_control("k1", ["Hjørnespark", "Frispark", "Indkast"], default="Hjørnespark", key="r1", label_visibility="collapsed")
        with col_content:
            st.caption("### Holdoversigt")

        if c:
            st.dataframe(get_summary_stats(df_all[df_all['TYPE_NAVN'] == c], 'KLUB_NAVN'), use_container_width=True, hide_index=True, column_config=col_cfg)

    with tabs[2]:
        col_content, col_control = st.columns([3, 1])
        with col_control:
            c2 = st.segmented_control("k2", ["Hjørnespark", "Frispark", "Indkast"], default="Hjørnespark", key="r2", label_visibility="collapsed")
        with col_content:
            st.caption("### Tager-oversigt")

        if c2:
            st.dataframe(get_summary_stats(df_team_selected[df_team_selected['TYPE_NAVN'] == c2], 'TAGER_NAVN'), use_container_width=True, hide_index=True, column_config=col_cfg)

    for i, name in enumerate(["Hjørnespark", "Frispark", "Indkast"], 3):
        with tabs[i]:
            render_setpiece_analysis(df_team_selected, name, t_sel)

    # =====================================================================
    # Modstanderrapport - kamp-forberedelse med logoer, opsummering,
    # modtagerzoner og PDF-eksport
    # =====================================================================
    with tabs[6]:
        st.caption("### Modstander-scoutingrapport")
        andre_hold = [t for t in teams if t != HIF_NAVN] if HIF_NAVN in teams else [t for t in teams if t != t_sel]
        if not andre_hold:
            st.info("Der er ikke flere hold i datasættet at vælge som modstander.")
        else:
            modstander = st.selectbox("Vælg modstander", andre_hold, key="modstander_sel")
            df_mod_team = df_all[df_all['KLUB_NAVN'] == modstander].copy()

            render_header_logos(HIF_NAVN, modstander)
            st.markdown("---")

            st.markdown(f"#### Sådan spiller **{modstander}** deres standardsituationer")
            opsummering = opsummering_linjer(df_mod_team, modstander)
            for linje in opsummering:
                st.markdown(f"- {linje}")

            st.markdown("---")
            st.markdown("##### Top 3-tagere pr. type")
            top3_data = get_top3_dict(df_mod_team)
            r1, r2, r3 = st.columns(3)
            for col, sp_type in zip([r1, r2, r3], ["Hjørnespark", "Frispark", "Indkast"]):
                with col:
                    st.markdown(f"**{sp_type}**")
                    rows = top3_data.get(sp_type, [])
                    if rows:
                        for navn, antal in rows:
                            st.write(f"- {navn}: {antal} stk.")
                    else:
                        st.caption("Ingen data")

            st.markdown("---")
            st.markdown("##### Modtagerzoner ved hjørnespark")
            corner_figs = build_corner_zone_figs(df_mod_team)
            cz1, cz2 = st.columns(2)
            for col, side_navn in zip([cz1, cz2], ["Venstre side", "Højre side"]):
                with col:
                    fig, antal = corner_figs.get(side_navn, (None, 0))
                    st.markdown(f"**{side_navn}** ({antal} hjørnespark)")
                    if fig is not None:
                        st.pyplot(fig, clear_figure=False)
                    else:
                        st.caption("Ingen data")

            st.markdown("---")
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                rapport_tekst = f"# Modstanderrapport: {modstander}\n\n" + "\n".join([f"- {l}" for l in opsummering])
                st.download_button(
                    "Download som tekst",
                    data=rapport_tekst,
                    file_name=f"modstanderrapport_{modstander}.md",
                    mime="text/markdown",
                    key="download_modstanderrapport_md"
                )
            with col_dl2:
                pdf_buffer = generate_modstanderrapport_pdf(HIF_NAVN, modstander, opsummering, top3_data, corner_figs)
                st.download_button(
                    "Download PDF-rapport",
                    data=pdf_buffer,
                    file_name=f"modstanderrapport_{modstander}.pdf",
                    mime="application/pdf",
                    key="download_modstanderrapport_pdf"
                )

            # Ryd op i figurerne, nu hvor de er brugt både i Streamlit og PDF'en
            for fig, _ in corner_figs.values():
                if fig is not None:
                    plt.close(fig)

    # =====================================================================
    # Sammenligning
    # =====================================================================
    with tabs[7]:
        st.caption("### Sammenligning mellem to hold")
        c1, c2 = st.columns(2)
        with c1:
            team_a = st.selectbox("Hold A", teams, index=teams.index(t_sel) if t_sel in teams else 0, key="cmp_a")
        with c2:
            andre_b = [t for t in teams if t != team_a]
            team_b = st.selectbox("Hold B", andre_b, key="cmp_b") if andre_b else None

        if team_b:
            render_header_logos(team_a, team_b)
            st.markdown("---")

            df_a = df_all[df_all['KLUB_NAVN'] == team_a].copy()
            df_b = df_all[df_all['KLUB_NAVN'] == team_b].copy()

            for sp_type in ["Hjørnespark", "Frispark", "Indkast"]:
                st.markdown(f"#### {sp_type}")
                sub_a = df_a[df_a['TYPE_NAVN'] == sp_type]
                sub_b = df_b[df_b['TYPE_NAVN'] == sp_type]

                antal_a, antal_b = len(sub_a), len(sub_b)
                succes_a = int(round((sub_a['MODTAGER'].notna().sum() / antal_a) * 100)) if antal_a else 0
                succes_b = int(round((sub_b['MODTAGER'].notna().sum() / antal_b) * 100)) if antal_b else 0

                cc1, cc2 = st.columns(2)
                cc1.metric(f"{team_a}: Antal", antal_a)
                cc1.metric(f"{team_a}: Succes %", f"{succes_a}%")
                cc2.metric(f"{team_b}: Antal", antal_b)
                cc2.metric(f"{team_b}: Succes %", f"{succes_b}%")

                fig = go.Figure()
                fig.add_trace(go.Bar(name=team_a, x=["Antal", "Succes %"], y=[antal_a, succes_a], marker_color=HIF_RED))
                fig.add_trace(go.Bar(name=team_b, x=["Antal", "Succes %"], y=[antal_b, succes_b], marker_color="#333333"))
                fig.update_layout(barmode='group', height=280, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig, use_container_width=True, key=f"cmp_chart_{sp_type}")
        else:
            st.info("Der er ikke flere hold i datasættet at sammenligne med.")

    # =====================================================================
    # Defensiv analyse
    # =====================================================================
    with tabs[8]:
        st.caption("### Defensiv analyse - modstanderes dødbolde")
        def_team = st.selectbox("Analyser forsvar for", teams, index=teams.index(t_sel) if t_sel in teams else 0, key="def_team_sel")

        render_header_logos(HIF_NAVN, def_team if def_team != HIF_NAVN else None)
        st.markdown("---")

        df_defensiv = get_defensive_events(df_all, def_team, uuid_to_name)

        if df_defensiv.empty:
            st.info("Ingen modstander-data fundet for de kampe, holdet indgår i.")
        else:
            st.markdown(f"#### Sådan har modstandere angrebet **{def_team}** fra dødbolde")
            for linje in opsummering_linjer(df_defensiv, f"modstandere af {def_team}"):
                st.markdown(f"- {linje}")

            st.markdown("---")
            st.markdown("##### Modtagerzoner ved hjørnespark imod jer")
            def_corner_figs = build_corner_zone_figs(df_defensiv)
            dz1, dz2 = st.columns(2)
            for col, side_navn in zip([dz1, dz2], ["Venstre side", "Højre side"]):
                with col:
                    fig, antal = def_corner_figs.get(side_navn, (None, 0))
                    st.markdown(f"**{side_navn}** ({antal} hjørnespark)")
                    if fig is not None:
                        st.pyplot(fig, clear_figure=True)
                    else:
                        st.caption("Ingen data")

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Standardsituationer")
    st.markdown("<style>header {visibility: hidden;}</style>", unsafe_allow_html=True)
    vis_side()
