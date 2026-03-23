import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data.data_load import load_local_players 

# --- KONSTANTER & MAPPING ---
HIF_SSIID = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
COMP_UUID = "6ifaeunfdelecgticvxanikzu"
EXCLUDE_LIST = ["114516", "570705", "624707", "523647", "39664"] 

KLUB_NAVNE = {
    "HVI": "Hvidovre IF", "KIF": "Kolding IF", "MID": "Middelfart",
    "HIK": "Hobro IK", "LBK": "Lyngby BK", "B93": "B.93",
    "ARF": "Aarhus Fremad", "ACH": "Horsens", "HBK": "HB Køge",
    "EFB": "Esbjerg fB", "HIL": "Hillerød", "AAB": "AaB"
}

def get_opponent_name(description):
    """Udtrækker modstandernavn fra kampbeskrivelsen."""
    if not description or ' - ' not in description:
        return "Ukendt"
    teams = [t.strip() for t in description.split(' - ')]
    opp_code = teams[1] if teams[0] == 'HVI' else teams[0]
    return KLUB_NAVNE.get(opp_code, opp_code)

def vis_side(conn, name_map=None):
    # --- 1. HENT LOKAL SPILLER-MAPPING ---
    df_local = load_local_players()
    player_mapping = {}
    if df_local is not None and not df_local.empty:
        df_local.columns = [c.strip() for c in df_local.columns]
        if 'optaId' in df_local.columns and 'NAVN' in df_local.columns:
            # Sikrer at optaId er en ren streng uden decimaler (fx '12345' i stedet for '12345.0')
            df_local['optaId_clean'] = df_local['optaId'].apply(
                lambda x: str(int(float(x))) if pd.notnull(x) and str(x).replace('.','',1).isdigit() else str(x)
            )
            player_mapping = df_local.set_index('optaId_clean')['NAVN'].to_dict()

    # --- 2. HENT DATA ---
    @st.cache_data(ttl=600)
    def get_safe_data():
        today = datetime.now().strftime('%Y-%m-%d')
        query_meta = f"""
        SELECT "DATE", DESCRIPTION, MATCH_SSIID, HOME_SSIID, AWAY_SSIID
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA
        WHERE COMPETITION_OPTAUUID = '{COMP_UUID}' AND "DATE" >= '2025-07-01' AND "DATE" <= '{today}'
        ORDER BY "DATE" DESC
        """
        
        query_phys = f"""
        WITH hvidovre_ids AS (
            SELECT DISTINCT m.MATCH_SSIID, f.value:"optaId"::string AS opta_id
            FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_GAME_METADATA m,
            LATERAL FLATTEN(input => CASE WHEN m.HOME_SSIID = '{HIF_SSIID}' THEN m.HOME_PLAYERS ELSE m.AWAY_PLAYERS END) f
            WHERE m.HOME_SSIID = '{HIF_SSIID}' OR m.AWAY_SSIID = '{HIF_SSIID}'
        )
        SELECT p.*, 
               CASE WHEN h.opta_id IS NOT NULL THEN 'Hvidovre IF' ELSE 'Modstander' END AS "Hold"
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        LEFT JOIN hvidovre_ids h ON p.MATCH_SSIID = h.MATCH_SSIID AND p."optaId" = h.opta_id
        WHERE p.MATCH_DATE >= '2025-07-01'
        """
        return conn.query(query_meta), conn.query(query_phys)

    df_meta, df_phys = get_safe_data()
    if df_phys.empty:
        st.error("Ingen fysisk data fundet for denne saeson.")
        return

    # --- 3. DATABEHANDLING (ROBUST & MAP-FØRST VERSION) ---
    def parse_minutes(val):
        if pd.isna(val) or val == "": return 0.0
        try:
            v = str(val)
            if ':' in v:
                m, s = map(int, v.split(':'))
                return round(m + s/60, 2)
            return float(val)
        except: return 0.0

    df_phys['MINS_DECIMAL'] = df_phys['MINUTES'].apply(parse_minutes)
    df_phys['HI_RUN'] = df_phys['HIGH SPEED RUNNING'].fillna(0) + df_phys['SPRINTING'].fillna(0)
    
    # Robust rensning af optaId (løser float-fejlen)
    def clean_id(x):
        if pd.isna(x) or x == "": return "UKENDT"
        try:
            # Fjerner .0 hvis det er en float gemt som string
            return str(int(float(x)))
        except:
            return str(x).strip()

    df_phys['optaId_str'] = df_phys['optaId'].apply(clean_id)

    # Filtrer ekskluderede spillere ved hjælp af den nye streng-kolonne
    df_phys = df_phys[~df_phys['optaId_str'].isin(EXCLUDE_LIST)].copy()
    
    # --- NAVNE & KLUB-MAPPING ---
    # Vi henter din lokale map ind igen, men denne gang tager vi KLUBBEN med også
    def get_display_name_and_club(row):
        oid = row['optaId_str']
        raw_name = row['PLAYER_NAME']
        
        # 1. Tjek din lokale mapping (df_local) for NAVN og KLUB
        # Vi antager at df_local har kolonnerne 'optaId', 'NAVN', og f.eks. 'KLUB_MAP'
        # Hvis du ikke har en 'KLUB_MAP' kolonne i din Excel, skal du tilføje den.
        if oid in player_mapping:
            name = player_mapping[oid]
            # Her skal du bruge kolonnenavnet for klub fra din Excel (f.eks. 'KLUB_MAP')
            # For nu, antager jeg den hedder 'KLUB_MAP' og du gemmer klubkoder som 'LBK', 'ACH' osv.
            # Men vi skal tilføje en mapping fra kode til fuldt navn
            return name, oid # For nu, returnerer vi bare ID'et som fallback
            
        # 2. Hvis ingen mapping findes, brug de rå data fra Second Spectrum
        if pd.notnull(raw_name) and raw_name != "":
            return raw_name, "NULL"
        return f"Ukendt ({oid})", "NULL"

    # Vi opdaterer din local_players map til også at hente klub-koden
    # (Kræver du opdaterer load_local_players funktionen til at hente den kolonne)
    
    # FOR IMPLENENTERING UDEN AT OPDATERE EXCEL:
    # Vi må lave en "overrule_klub" funktion:
    # (Dette er en midlertidig løsning indtil Excel opdateres)
    def overrule_klub(row):
        p_name = row['DISPLAY_NAME']
        if p_name == 'Lauge Sandgrav': return 'Lyngby BK'
        if p_name == 'Ole Kolskogen': return 'Horsens'
        # ... tilføj flere her
        return row['Klub'] # Fallback til den rå klubregistrering
    
    df_phys['DISPLAY_NAME'] = df_phys.apply(
        lambda r: player_mapping.get(r['optaId_str'], r['PLAYER_NAME']), axis=1
    )
    # --- 4. TABS ---
    t1, t2, t3, t4 = st.tabs(["Hvidovre IF P90", "Udvikling", "Top 5", "Kampanalyse"])
    
    # --- TAB 1: P90 OVERSIGT FOR HVIDOVRE ---
    with t1:
        st.subheader("Saesongennemsnit pr. 90 minutter")
        df_hif = df_phys[df_phys['Hold'] == "Hvidovre IF"].copy()
        summary = df_hif.groupby('DISPLAY_NAME').agg({
            'MINS_DECIMAL': 'sum', 'DISTANCE': 'sum', 'HI_RUN': 'sum', 
            'DISTANCE_TIP': 'sum', 'DISTANCE_OTIP': 'sum', 'TOP_SPEED': 'max'
        }).reset_index()

        summary = summary[summary['MINS_DECIMAL'] > 15].copy()
        summary['KM/90'] = (summary['DISTANCE'] / summary['MINS_DECIMAL']) * 90 / 1000
        summary['HI m/90'] = (summary['HI_RUN'] / summary['MINS_DECIMAL']) * 90
        summary['TIP m/90'] = (summary['DISTANCE_TIP'] / summary['MINS_DECIMAL']) * 90
        summary['OTIP m/90'] = (summary['DISTANCE_OTIP'] / summary['MINS_DECIMAL']) * 90

        st.dataframe(
            summary.sort_values('KM/90', ascending=False),
            column_config={
                "DISPLAY_NAME": "Spiller",
                "KM/90": st.column_config.NumberColumn("KM/90", format="%.2f"),
                "HI m/90": st.column_config.NumberColumn("HI m/90", format="%d"),
                "TIP m/90": st.column_config.NumberColumn("TIP m/90", format="%d"),
                "OTIP m/90": st.column_config.NumberColumn("OTIP m/90", format="%d"),
                "TOP_SPEED": st.column_config.NumberColumn("Topfart", format="%.1f km/t")
            },
            column_order=("DISPLAY_NAME", "KM/90", "HI m/90", "TIP m/90", "OTIP m/90", "TOP_SPEED"),
            use_container_width=True, hide_index=True
        )

    # --- TAB 2: GRAFISK SAMMENLIGNING ---
    with t2:
        kat_map = {
            "KM/90": "Total Distance (KM/90)", 
            "HI m/90": "Høj Intensitetsloeb (m/90)", 
            "TIP m/90": "Offensivt loeb (TIP m/90)",
            "OTIP m/90": "Defensivt pres (OTIP m/90)",
            "TOP_SPEED": "Topfart (km/t)"
        }
        valg = st.selectbox("Vaely parameter", list(kat_map.keys()), format_func=lambda x: kat_map[x])
        
        plot_df = summary.sort_values(valg, ascending=False)
        fig = px.bar(plot_df, x='DISPLAY_NAME', y=valg, text_auto='.1f', color=valg, color_continuous_scale='reds')
        fig.update_layout(xaxis_title=None, yaxis_visible=False, plot_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 3: TOP 5 PRESTATIONER ---
    with t3:
        st.subheader("Saesonens højeste tal i enkeltkampe")
        c1, c2, c3 = st.columns(3)
        
        def get_top5(metric):
            df = df_phys.nlargest(5, metric)[['DISPLAY_NAME', 'MATCH_SSIID', 'Hold', metric]].copy()
            df = df.merge(df_meta[['MATCH_SSIID', 'DESCRIPTION']], on='MATCH_SSIID', how='left')
            df['Klub'] = df.apply(lambda r: 'Hvidovre IF' if r['Hold'] == 'Hvidovre IF' else get_opponent_name(r['DESCRIPTION']), axis=1)
            return df[['DISPLAY_NAME', 'Klub', metric]]

        with c1:
            st.write("Topfart (km/t)")
            st.dataframe(get_top5('TOP_SPEED'), use_container_width=True, hide_index=True)
        with c2:
            st.write("HI loeb (m)")
            st.dataframe(get_top5('HI_RUN'), use_container_width=True, hide_index=True)
        with c3:
            st.write("Distance med bold (TIP)")
            st.dataframe(get_top5('DISTANCE_TIP'), use_container_width=True, hide_index=True)

    # --- TAB 4: KAMPANALYSE (BEGGE HOLD) ---
    with t4:
        df_hif_matches = df_meta[(df_meta['HOME_SSIID'] == HIF_SSIID) | (df_meta['AWAY_SSIID'] == HIF_SSIID)].copy()
        df_hif_matches['LABEL'] = df_hif_matches['DATE'].astype(str) + " - " + df_hif_matches['DESCRIPTION']
        
        if not df_hif_matches.empty:
            valgt_kamp = st.selectbox("Vaely kamp", df_hif_matches['LABEL'].unique())
            kamp_info = df_hif_matches[df_hif_matches['LABEL'] == valgt_kamp].iloc[0]
            opp_name = get_opponent_name(kamp_info['DESCRIPTION'])
            
            df_m = df_phys[df_phys['MATCH_SSIID'] == kamp_info['MATCH_SSIID']].copy()
            df_m['KM'] = df_m['DISTANCE'] / 1000
            df_m['Klub'] = df_m['Hold'].apply(lambda x: 'Hvidovre IF' if x == 'Hvidovre IF' else opp_name)
            
            st.dataframe(
                df_m.sort_values(by=['Hold', 'DISTANCE'], ascending=[True, False]),
                column_config={
                    "DISPLAY_NAME": "Spiller",
                    "Klub": "Klub",
                    "MINUTES": "Min",
                    "KM": st.column_config.NumberColumn("KM", format="%.2f"),
                    "HI_RUN": "HI m",
                    "DISTANCE_TIP": "TIP (m)",
                    "DISTANCE_OTIP": "OTIP (m)",
                    "DISTANCE_BOP": "BOP (m)",
                    "TOP_SPEED": "Top"
                },
                column_order=("DISPLAY_NAME", "Klub", "MINUTES", "KM", "HI_RUN", "DISTANCE_TIP", "DISTANCE_OTIP", "DISTANCE_BOP", "TOP_SPEED"),
                use_container_width=True, hide_index=True, height=800
            )
