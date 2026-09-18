"""Deterministic metrics for immutable M5 raw runs."""
from collections import Counter
from datetime import datetime
import csv
import hashlib
import json
import math


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _ratio(part, whole):
    return part / whole if whole else None


def _haversine_m(first, second):
    radius_m = 6_371_008.8
    latitude_a, longitude_a = map(math.radians, first)
    latitude_b, longitude_b = map(math.radians, second)
    d_latitude = latitude_b - latitude_a
    d_longitude = longitude_b - longitude_a
    value = (math.sin(d_latitude / 2) ** 2 + math.cos(latitude_a) *
             math.cos(latitude_b) * math.sin(d_longitude / 2) ** 2)
    return 2 * radius_m * math.asin(min(1.0, math.sqrt(value)))


class RunAnalysis:
    def __init__(self, logger):
        self.logger = logger

    def _read(self, run_id):
        directory = self.logger._directory(run_id)
        if not (directory / 'complete.json').exists():
            raise ValueError('Analiza wymaga zakończonego nagrania')
        metadata = json.loads((directory / 'metadata.json').read_text(encoding='utf-8'))
        complete = json.loads((directory / 'complete.json').read_text(encoding='utf-8'))
        raw_path = directory / 'raw.csv'
        if complete.get('sha256', {}).get('raw.csv') != hashlib.sha256(raw_path.read_bytes()).hexdigest():
            raise ValueError('Hash raw.csv nie zgadza się z manifestem')
        rows = []
        with raw_path.open(encoding='utf-8', newline='') as stream:
            for row in csv.DictReader(stream):
                try:
                    row['model_seconds'] = float(row['model_seconds'])
                    row['sequence'] = int(row['sequence'])
                    row['received_at'] = datetime.fromisoformat(row['timestamp'])
                    row['position'] = float(row['current_corridor_position']) if row['current_corridor_position'] else None
                    row['speed'] = float(row['speed_mps']) if row['speed_mps'] else None
                    row['target'] = float(row['target_speed_mps']) if row['target_speed_mps'] else None
                    row['latitude_value'] = float(row['latitude']) if row['latitude'] else None
                    row['longitude_value'] = float(row['longitude']) if row['longitude'] else None
                    row['accuracy_value'] = float(row['gps_accuracy']) if row['gps_accuracy'] else None
                    row['payload'] = json.loads(row['payload_json'] or '{}')
                    if not isinstance(row['payload'], dict):
                        raise ValueError('payload_json must contain an object')
                except (ValueError, TypeError, json.JSONDecodeError) as error:
                    raise ValueError(f'Niepoprawny rekord: {error}') from error
                rows.append(row)
        if not rows or rows[0]['event'] != 'RUN_START':
            raise ValueError('Brak RUN_START')
        if any(second['sequence'] != first['sequence'] + 1 for first, second in zip(rows, rows[1:])):
            raise ValueError('Nieciągła kolejność rekordów')
        return metadata, complete, rows

    @staticmethod
    def _gps_quality(rows):
        samples = [row for row in rows if row['event'] == 'EXTERNAL_TELEMETRY']
        if not samples:
            return dict(
                status='NO_DATA', sample_count=0, duration_seconds=0,
                issues=['Nagranie nie zawiera próbek GPS z telefonu.'])

        receipt_intervals = [
            (current['received_at'] - previous['received_at']).total_seconds()
            for previous, current in zip(samples, samples[1:])]
        phone_times = [sample['payload'].get('phone_timestamp_seconds') for sample in samples]
        phone_times = [float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
                       for value in phone_times]
        phone_intervals_aligned = [
            current - previous if current is not None and previous is not None else None
            for previous, current in zip(phone_times, phone_times[1:])]
        phone_intervals = [interval for interval in phone_intervals_aligned if interval is not None]
        accuracies = [sample['accuracy_value'] for sample in samples if sample['accuracy_value'] is not None]
        final_speeds = [sample['speed'] for sample in samples]
        raw_speeds = [sample['payload'].get('raw_speed_mps') for sample in samples]
        calculated_speeds = [sample['payload'].get('calculated_speed_mps') for sample in samples]
        speed_sources = Counter(sample['payload'].get('speed_source') or 'UNKNOWN' for sample in samples)
        location_sources = Counter(sample.get('source') or 'UNKNOWN' for sample in samples)
        position_qualities = Counter(sample['payload'].get('position_quality') or 'UNKNOWN' for sample in samples)
        speed_accuracies = [sample['payload'].get('speed_accuracy_mps') for sample in samples]
        speed_accuracies = [float(value) for value in speed_accuracies
                            if isinstance(value, (int, float)) and not isinstance(value, bool)]
        reasons = Counter()
        for sample in samples:
            values = sample['payload'].get('quality_reasons') or []
            if isinstance(values, list):
                reasons.update(value for value in values if isinstance(value, str))

        usable_count = sum(sample['payload'].get('usable_for_live') is True for sample in samples)
        coordinates = [
            (sample['latitude_value'], sample['longitude_value'])
            if sample['latitude_value'] is not None and sample['longitude_value'] is not None else None
            for sample in samples]
        path_distance = sum(
            _haversine_m(previous, current)
            for previous, current in zip(coordinates, coordinates[1:])
            if previous is not None and current is not None)

        movement_transitions = 0
        movement_starts = 0
        stop_confirmations = 0
        stable_state = None
        for sample, speed in zip(samples, final_speeds):
            source = sample['payload'].get('speed_source')
            candidate = 'STOPPED' if source == 'STATIONARY_FILTER' or speed is not None and speed <= 0.3 else \
                        'MOVING' if speed is not None and speed >= 1.0 else None
            if candidate is None or candidate == stable_state:
                continue
            if stable_state is not None:
                movement_transitions += 1
                if candidate == 'MOVING':
                    movement_starts += 1
                else:
                    stop_confirmations += 1
            stable_state = candidate

        duration = (samples[-1]['received_at'] - samples[0]['received_at']).total_seconds()
        available_final = sum(speed is not None for speed in final_speeds)
        available_raw = sum(isinstance(speed, (int, float)) and not isinstance(speed, bool) for speed in raw_speeds)
        available_calculated = sum(isinstance(speed, (int, float)) and not isinstance(speed, bool)
                                   for speed in calculated_speeds)
        within_10 = sum(accuracy <= 10 for accuracy in accuracies)
        within_25 = sum(accuracy <= 25 for accuracy in accuracies)
        within_50 = sum(accuracy <= 50 for accuracy in accuracies)
        positive_intervals = [interval for interval in receipt_intervals if interval >= 0]
        positive_phone_intervals = [interval for interval in phone_intervals if interval >= 0]
        largest_gap = max(positive_intervals) if positive_intervals else None
        largest_phone_gap = max(positive_phone_intervals) if positive_phone_intervals else None
        transport_only_gaps = sum(
            receipt > 2 and phone is not None and phone <= 2
            for receipt, phone in zip(receipt_intervals, phone_intervals_aligned))
        issues = []
        if len(samples) < 30 or duration < 30:
            issues.append('Za mało danych: nagraj co najmniej 30 próbek i 30 sekund.')
        if largest_phone_gap is not None and largest_phone_gap > 5:
            issues.append(f'Telefon nie dostarczył nowej pozycji GPS przez {largest_phone_gap:.1f} s.')
        elif largest_gap is not None and largest_gap > 5:
            issues.append(f'Wykryto przerwę w odbiorze trwającą {largest_gap:.1f} s.')
        if _ratio(usable_count, len(samples)) < 0.9:
            issues.append('Mniej niż 90% próbek nadawało się do użycia na żywo.')
        if not accuracies or _ratio(within_50, len(samples)) < 0.9:
            issues.append('Mniej niż 90% próbek miało dokładność GPS do 50 m.')
        if _ratio(available_final, len(samples)) < 0.9:
            issues.append('Prędkość końcowa była dostępna w mniej niż 90% próbek.')

        status = 'READY' if not issues else 'INSUFFICIENT' if len(samples) < 30 or duration < 30 else 'DEGRADED'
        return dict(
            status=status,
            sample_count=len(samples),
            duration_seconds=duration,
            sample_rate_hz=(len(samples) - 1) / duration if duration > 0 else None,
            receipt_interval_median_seconds=_percentile(positive_intervals, 0.5),
            receipt_interval_p95_seconds=_percentile(positive_intervals, 0.95),
            largest_gap_seconds=largest_gap,
            gaps_over_2_seconds=sum(interval > 2 for interval in positive_intervals),
            phone_interval_median_seconds=_percentile(positive_phone_intervals, 0.5),
            phone_interval_p95_seconds=_percentile(positive_phone_intervals, 0.95),
            largest_phone_gap_seconds=largest_phone_gap,
            phone_gaps_over_2_seconds=sum(interval > 2 for interval in positive_phone_intervals),
            transport_only_gaps_over_2_seconds=transport_only_gaps,
            phone_timestamp_regressions=sum(interval <= 0 for interval in phone_intervals),
            usable_samples=usable_count,
            usable_ratio=_ratio(usable_count, len(samples)),
            accuracy=dict(
                samples=len(accuracies),
                minimum_m=min(accuracies) if accuracies else None,
                median_m=_percentile(accuracies, 0.5),
                p95_m=_percentile(accuracies, 0.95),
                maximum_m=max(accuracies) if accuracies else None,
                within_10m_ratio=_ratio(within_10, len(samples)),
                within_25m_ratio=_ratio(within_25, len(samples)),
                within_50m_ratio=_ratio(within_50, len(samples))),
            speed=dict(
                final_available_ratio=_ratio(available_final, len(samples)),
                raw_available_ratio=_ratio(available_raw, len(samples)),
                calculated_available_ratio=_ratio(available_calculated, len(samples)),
                source_counts=dict(speed_sources),
                maximum_final_mps=max((speed for speed in final_speeds if speed is not None), default=None)),
            location_source_counts=dict(location_sources),
            native_quality=dict(
                speed_accuracy_samples=len(speed_accuracies),
                speed_accuracy_median_mps=_percentile(speed_accuracies, 0.5),
                speed_accuracy_p95_mps=_percentile(speed_accuracies, 0.95),
                mock_samples=sum(sample['payload'].get('is_mock') is True for sample in samples)),
            position_quality_counts=dict(position_qualities),
            rejection_reason_counts=dict(reasons),
            raw_path_distance_m=path_distance,
            movement_transitions=movement_transitions,
            movement_starts=movement_starts,
            stop_confirmations=stop_confirmations,
            issues=issues)

    def analyze(self, run_id):
        metadata, complete, rows = self._read(run_id)
        telemetry = [row for row in rows if row['event'] == 'TELEMETRY' and
                     row['position'] is not None and row['speed'] is not None]
        positions = [row['position'] for row in telemetry]
        speeds = [row['speed'] for row in telemetry]
        total_time = rows[-1]['model_seconds'] - rows[0]['model_seconds'] if rows else 0
        distance = max(positions) - min(positions) if positions else None
        stops = stop_duration = brake_events = accel_events = energy = 0
        stop_start = previous_speed = None
        compliant = []
        for row in telemetry:
            speed, target = row['speed'], row['target']
            if previous_speed is not None:
                delta = speed - previous_speed
                if delta < -.01:
                    brake_events += 1
                    energy += abs(delta) * speed
                if delta > .01:
                    accel_events += 1
            if previous_speed is not None and speed <= .05 and previous_speed > .05 and stop_start is None:
                stops += 1
                stop_start = row['model_seconds']
            if speed > .05 and stop_start is not None:
                stop_duration += row['model_seconds'] - stop_start
                stop_start = None
            if target is not None:
                compliant.append(abs(speed - target) <= 1 / 3.6)
            previous_speed = speed
        if stop_start is not None:
            stop_duration += rows[-1]['model_seconds'] - stop_start
        passes = [row for row in rows if row['event'] == 'PASS_STOP_LINE']
        incidents = [row for row in rows if row['event'] == 'INCIDENT']
        recommendations = [row for row in rows if row['event'] == 'RECOMMENDATION']
        errors = []
        for passed in passes:
            for recommendation in reversed(recommendations):
                value = recommendation['payload'].get('recommendation', {})
                if (recommendation['model_seconds'] <= passed['model_seconds'] and
                        value.get('signal_id') == passed['signal_id'] and value.get('arrival_at') is not None):
                    errors.append(passed['model_seconds'] - float(value['arrival_at']))
                    break
        return dict(
            schema_version=1, run_id=run_id, corridor_id=metadata.get('corridor_id'),
            dataset=metadata.get('dataset'), status='COMPLETE', total_time=total_time,
            distance=distance, number_of_complete_stops=stops, stop_duration=stop_duration,
            brake_events=brake_events, estimated_braking_energy=energy,
            acceleration_events=accel_events,
            average_speed=distance / total_time if distance is not None and total_time > 0 else None,
            max_speed=max(speeds) if speeds else None,
            green_passes=sum(row['payload'].get('state') == 'GREEN' for row in passes),
            red_arrivals=len(incidents) + sum(row['payload'].get('state') == 'RED' for row in passes),
            prediction_error_mean=sum(errors) / len(errors) if errors else None,
            prediction_error_samples=len(errors),
            recommendation_compliance=sum(compliant) / len(compliant) if compliant else None,
            records=len(rows), event_counts=complete.get('counts', {}),
            timebase=metadata.get('timebase'), gps_quality=self._gps_quality(rows))

    def compare(self, baseline_id, greenwave_id):
        baseline = self.analyze(baseline_id)
        greenwave = self.analyze(greenwave_id)
        keys = ('total_time', 'distance', 'number_of_complete_stops', 'stop_duration',
                'brake_events', 'estimated_braking_energy', 'acceleration_events',
                'average_speed', 'max_speed', 'green_passes', 'red_arrivals',
                'prediction_error_mean', 'recommendation_compliance')
        delta = {key: (None if baseline.get(key) is None or greenwave.get(key) is None
                       else greenwave[key] - baseline[key]) for key in keys}
        gps_keys = ('sample_rate_hz', 'largest_gap_seconds', 'largest_phone_gap_seconds',
                    'gaps_over_2_seconds', 'phone_gaps_over_2_seconds', 'usable_ratio')
        baseline_gps, greenwave_gps = baseline['gps_quality'], greenwave['gps_quality']
        gps_delta = {key: (None if baseline_gps.get(key) is None or greenwave_gps.get(key) is None
                           else greenwave_gps[key] - baseline_gps[key]) for key in gps_keys}
        for key in ('median_m', 'p95_m'):
            first, second = baseline_gps.get('accuracy', {}).get(key), greenwave_gps.get('accuracy', {}).get(key)
            gps_delta[f'accuracy_{key}'] = None if first is None or second is None else second - first
        return dict(schema_version=1, baseline=baseline, greenwave=greenwave,
                    delta=delta,
                    gps_delta=gps_delta,
                    interpretation='Różnice opisują dwa zakończone logi; nie są dowodem przyczynowości.')
