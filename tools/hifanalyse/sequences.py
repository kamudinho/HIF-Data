import pandas as pd

def process_sequences(df):
    if df is None or df.empty:
        return pd.DataFrame()

    # 1. Konvertér til tal med det samme
    df['EVENT_X'] = pd.to_numeric(df['EVENT_X'], errors='coerce')
    df['EVENT_Y'] = pd.to_numeric(df['EVENT_Y'], errors='coerce')

    # 2. FJERN rækker uden koordinater (Vigtigt for at goal_idx - 1 virker!)
    # Hvis en række mangler X/Y, vil den ødelægge din pil-tegning
    df = df.dropna(subset=['EVENT_X', 'EVENT_Y'])

    # 3. Sortér og nulstil index
    df = df.sort_values(['SEQUENCEID', 'EVENT_TIMESTAMP']).reset_index(drop=True)

    if 'PLAYER_NAME' in df.columns:
        df['PLAYER_NAME'] = df['PLAYER_NAME'].fillna('Ukendt').str.strip()

    return df
