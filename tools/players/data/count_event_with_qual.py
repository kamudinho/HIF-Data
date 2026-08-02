# --- BEREGN TRUP-STATS INKL. DRIBLINGER OG DUELLER ---
    def count_event_with_qual(df_group, eid, qids):
        return df_group.apply(lambda r: har_qualifier(r['event_typeid'], r.get('qual_list', []), eid, qids), axis=1).sum()
    
    event_stats = df_all.groupby(['player_optauuid', 'visningsnavn']).apply(lambda x: pd.Series({
        'Aktioner': len(x),
        'Gule_kort': count_event_with_qual(x, 17, 31),
        'Roede_kort': count_event_with_qual(x, 17, 33),
        'Indskiftet': (x['event_typeid'] == 19).sum(),
        'Udskiftet': (x['event_typeid'] == 18).sum(),
        'Pasninger': x['Pasninger_Total'].sum(),
        'Pasninger_Succes': x['Pasninger_Succes'].sum(),
        'Stikninger': count_event_with_qual(x, 1, 4),
        'Indlæg': count_event_with_qual(x, 1, [2, 155]),
        'Afslutninger': x['event_typeid'].isin([13, 14, 15, 16]).sum(),
        'Erobringer': x['event_typeid'].isin([7, 8, 12, 49]).sum(),
        
        # --- NYE DRIBLING OG DUEL STATS ---
        'Driblinger': (x['event_typeid'] == 3).sum(),
        'Driblinger_Succes': x.apply(lambda r: 1 if str(r['event_typeid']) == "3" and "211" not in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        'Gennembrud_Overtake': x.apply(lambda r: 1 if str(r['event_typeid']) == "3" and "465" in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        'Rum_Driblinger_Space': x.apply(lambda r: 1 if str(r['event_typeid']) == "3" and "464" in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        'Offensive_Dueller': x.apply(lambda r: 1 if "286" in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        'Defensive_Dueller': x.apply(lambda r: 1 if "285" in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        'Defensive_1v1_Stoppet': x.apply(lambda r: 1 if "467" in [str(q).strip() for q in (r.get('qual_list', []) if isinstance(r.get('qual_list', []), list) else str(r.get('qual_list', '')).split(','))] else 0, axis=1).sum(),
        
        'Chancer_skabt': x.apply(lambda r: '210' in r.get('qual_list', []), axis=1).sum(),
        'Key_Passes': x.apply(lambda r: '210' in r.get('qual_list', []), axis=1).sum(),
        'Tacklinger': (x['event_typeid'] == 7).sum(),
        'Clearinger': (x['event_typeid'] == 12).sum(),
        'Blokeringer': (x['event_typeid'] == 55).sum(),
        'Interceptioner': (x['event_typeid'] == 5).sum(),
        'Frispark_imod': (x['event_typeid'] == 4).sum()
    })).reset_index()
    
    event_stats = event_stats.drop_duplicates(subset=['player_optauuid']).set_index('player_optauuid')
    
    if df_expected is not None and not df_expected.empty:
        match_stats = df_expected.groupby('player_optauuid').agg({
            'match_id': 'nunique',
            'minutes': 'sum',
            'xg': 'sum',
            'xa': 'sum'
        }).rename(columns={'match_id': 'Kampe', 'minutes': 'Minutter', 'xg': 'xG', 'xa': 'xA'})
        truppen_stats_raw = event_stats.join(match_stats, how='left').fillna(0)
    else:
        truppen_stats_raw = event_stats.copy()
        truppen_stats_raw['Kampe'] = 0
        truppen_stats_raw['Minutter'] = 0
        truppen_stats_raw['xG'] = 0.0
        truppen_stats_raw['xA'] = 0.0
    
    if df_db_stats is not None and not df_db_stats.empty:
        db_stats_clean = df_db_stats.drop_duplicates(subset=['player_optauuid']).set_index('player_optauuid')
        truppen_stats_raw['Mål'] = db_stats_clean['goals']
        truppen_stats_raw['Assists'] = db_stats_clean['assists']
    else:
        truppen_stats_raw['Mål'] = 0
        truppen_stats_raw['Assists'] = 0
    
    truppen_stats_raw['Mål'] = truppen_stats_raw['Mål'].fillna(0).astype(int)
    truppen_stats_raw['Assists'] = truppen_stats_raw['Assists'].fillna(0).astype(int)
    truppen_stats = truppen_stats_raw.copy()
    
    # --- BEREGN PASNINGSPROCENT DIREKTE PÅ TRUPPEN_STATS ---
    truppen_stats['Pasningsprocent'] = (
        (truppen_stats['Pasninger_Succes'] / truppen_stats['Pasninger']) * 100
    ).where(truppen_stats['Pasninger'] > 0, 0).round(1)
    
    truppen_stats['Pasningsprocent_Str'] = truppen_stats['Pasningsprocent'].astype(str) + "%"
