def classify_take_on(event_row):
    """Klassificerer en Opta Take On baseret på dens qualifiers."""
    if event_row.get('event_typeid') != 3 and event_row.get('EVENT_TYPEID') != 3:
        return "Ikke en dribling"

    qualifiers = event_row.get('qual_list', [])
    if not qualifiers:
        qual_str = event_row.get('qualifiers', '')
        qualifiers = [str(q).strip() for q in str(qual_str).split(',')] if qual_str else []

    if "339" in qualifiers:
        return "Vundet frispark i dribling"
    if "211" in qualifiers:
        return "Mislykket (Overrun)"
    if "465" in qualifiers:
        return "Fremadrettet dribling mod mål (Take on Overtake)"
    if "464" in qualifiers:
        return "Dribling i tomt rum / sidelæns (Take on Space)"
    if "467" in qualifiers:
        return "Stoppet i 1v1 defensiv duel"

    outcome = event_row.get('outcome', event_row.get('OUTCOME', 0))
    if str(outcome) == '1':
        return "Succesfuld dribling (Generel)"
    else:
        return "Mislykket dribling (Generel)"
