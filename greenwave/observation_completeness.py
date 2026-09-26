"""Evidence inventory, not a fitted phase model or a readiness score."""
from collections import Counter, defaultdict
from datetime import datetime


def point_completeness(observations):
    counts = Counter(event['classification'] for event in observations)
    kept = [event for event in observations if event['classification'] == 'KEEP']
    starts = [event for event in kept if event['reviewed_type'] == 'STATE_START']
    intervals, cycles = [], []
    by_run = defaultdict(list)
    for event in observations:
        if event['classification'] != 'RAPID_DUPLICATE':
            by_run[event['run_id']].append(event)
    for run_id, events in by_run.items():
        events.sort(key=lambda e: (datetime.fromisoformat(e['timestamp']), e['record_sequence']))
        previous, anchors = None, {}
        for event in events:
            if event['classification'] != 'KEEP' or event['reviewed_type'] != 'STATE_START':
                previous, anchors = None, {}
                continue
            if previous and previous['state'] == event['state']:
                # A repeated onset with no intervening phase is not a measured cycle.
                previous, anchors = event, {event['state']: event}
                continue
            stamp = datetime.fromisoformat(event['timestamp'])
            if previous:
                delta = (stamp - datetime.fromisoformat(previous['timestamp'])).total_seconds()
                if delta <= 0:
                    previous, anchors = None, {}
                    continue
                pair = previous['state'] + '_' + event['state']
                intervals.append(dict(run_id=run_id, transition=pair, seconds=delta,
                    start_record=previous['record_sequence'], end_record=event['record_sequence'],
                    interpretation={'RED_GREEN': 'RED_ONSET_TO_GREEN_ONSET',
                        'GREEN_YELLOW': 'OBSERVED_GREEN_DURATION',
                        'YELLOW_RED': 'OBSERVED_YELLOW_DURATION'}.get(pair, 'TRANSITION_INTERVAL_ONLY')))
            anchor = anchors.get(event['state'])
            if anchor:
                delta = (stamp - datetime.fromisoformat(anchor['timestamp'])).total_seconds()
                if delta > 0:
                    cycles.append(dict(run_id=run_id, state=event['state'], seconds=delta,
                        start_record=anchor['record_sequence'], end_record=event['record_sequence'],
                        interpretation='OBSERVED_RECURRENCE_NOT_PROVEN_SINGLE_CYCLE'))
            anchors[event['state']] = event
            previous = event
    interval_counts = Counter(item['transition'] for item in intervals)
    missing = []
    if not observations:
        missing.append('Brak obserwacji tego punktu.')
    if not starts:
        missing.append('Brak zaobserwowanych początków faz; sam kolor nie określa początku.')
    for pair, label in [('RED_GREEN', 'czerwone → zielone'), ('GREEN_YELLOW', 'zielone → żółte'),
                        ('YELLOW_RED', 'żółte → czerwone')]:
        if not interval_counts[pair]:
            missing.append('Brak pary zaobserwowanych zmian: ' + label + '.')
        elif interval_counts[pair] == 1:
            missing.append('Tylko jedna para ' + label + '; potrzebne powtórzenia.')
    if not cycles:
        missing.append('Brak ponownego początku tego samego koloru po innych fazach w jednym nagraniu.')
    if len(by_run) < 2:
        missing.append('Brak obserwacji do porównania z osobnego przejazdu.')
    if counts['REPEATED_STATE_REVIEW']:
        missing.append('Powtórzone kolory wymagają przeglądu; nie uznajemy ich za nowe cykle.')
    return dict(observation_count=len(observations), run_count=len({e['run_id'] for e in observations}),
        kept_count=len(kept), start_count=len(starts), seen_count=len(kept)-len(starts),
        duplicate_count=counts['RAPID_DUPLICATE'], repeated_review_count=counts['REPEATED_STATE_REVIEW'],
        color_counts=dict(Counter(e['state'] for e in observations)),
        start_color_counts=dict(Counter(e['state'] for e in starts)),
        freshness_counts=dict(Counter(e.get('gps_freshness') or 'UNKNOWN' for e in observations)),
        intervals=intervals, interval_counts=dict(interval_counts), recurrences=cycles,
        status='NO_DATA' if not observations else 'REPEATED_INTERVALS' if any(
            count >= 2 for count in interval_counts.values()) else 'PARTIAL_DATA',
        missing=missing, model_validated=False,
        note='Click timing includes reaction delay. Recurrence may include skipped cycles. No fitted cycle, yellow duration assumption or live readiness is inferred.')
