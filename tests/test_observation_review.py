from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from greenwave.observation_review import review_observations


class ObservationReviewTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 9, 26, tzinfo=timezone.utc)
        self.route = SimpleNamespace(route_id='r', geometry_hash='hash',
            stop_lines=[SimpleNamespace(stop_line_id='L1', s_m=100)])
        self.replay = SimpleNamespace(samples=[SimpleNamespace(sequence=1)],
            match_history=[dict(candidate_s_m=90, status='MATCHED', direction='FORWARD',
                                position_uncertainty_m=5)], detector=SimpleNamespace(events=[]))
        self.telemetry = dict(event='EXTERNAL_TELEMETRY', sequence=1, speed=4,
            accuracy_value=5, payload=dict(device_id='d', stream_id='s', sample_sequence=7))

    def observation(self, seconds, state, **extra):
        stamp = self.start + timedelta(seconds=seconds)
        return dict(event='ROUTE_OBSERVATION', sequence=10 + int(seconds), received_at=stamp,
            payload=dict(observation_id=str(seconds), timestamp=stamp.isoformat(), state=state,
                event_type='STATE_SEEN', route_id='r', geometry_hash='hash', stop_line_id='L1',
                sample_ref='d:s:7', gps_freshness='FRESH', **extra))

    def review(self, observations, attestation=None):
        return review_observations([self.telemetry] + observations, self.replay, self.route,
                                   attestation)['points'][0]

    def test_seen_states_are_not_automatically_promoted_to_transitions(self):
        point = self.review([self.observation(0, 'RED'), self.observation(10, 'GREEN')])
        self.assertEqual(point['intervals'], [])
        self.assertEqual(point['observations'][0]['reviewed_type'], 'STATE_SEEN')

    def test_duplicates_do_not_shift_transition_time_and_sample_join_is_exact(self):
        observations = [self.observation(0, 'RED'), self.observation(.5, 'RED'),
                        self.observation(6, 'RED'), self.observation(6.5, 'RED'),
                        self.observation(10, 'GREEN')]
        point = self.review(observations, {'transition_states': ['RED', 'GREEN']})
        self.assertEqual([o['classification'] for o in point['observations']],
            ['KEEP', 'RAPID_DUPLICATE', 'REPEATED_STATE_REVIEW', 'RAPID_DUPLICATE', 'KEEP'])
        self.assertEqual(point['intervals'][0]['seconds'], 10)
        self.assertEqual(point['observations'][0]['candidate_distance_to_line_m'], 10)
        self.assertEqual(point['observations'][0]['sample_record_sequence'], 1)
        self.assertEqual(observations[0]['payload']['event_type'], 'STATE_SEEN')

    def test_green_to_red_interval_does_not_claim_green_duration(self):
        point = self.review([self.observation(0, 'GREEN'), self.observation(10, 'RED')],
                            {'transition_states': ['RED', 'GREEN']})
        self.assertEqual(point['intervals'][0]['meaning'],
                         'OBSERVED_TRANSITION_INTERVAL_NOT_GREEN_DURATION')

    def test_other_geometry_and_missing_sample_are_not_attached_by_nearest_time(self):
        foreign = self.observation(0, 'RED'); foreign['payload']['geometry_hash'] = 'other'
        missing = self.observation(10, 'GREEN'); missing['payload']['sample_ref'] = 'missing'
        point = self.review([foreign, missing])
        self.assertEqual(len(point['observations']), 1)
        self.assertIsNone(point['observations'][0]['sample_record_sequence'])
        self.assertIsNone(point['observations'][0]['candidate_distance_to_line_m'])

    def test_uncertain_projection_is_explicitly_diagnostic(self):
        self.replay.match_history[0]['status'] = 'UNCERTAIN'
        event = self.review([self.observation(0, 'GREEN')])['observations'][0]
        self.assertEqual(event['candidate_distance_to_line_m'], 10)
        self.assertFalse(event['distance_is_accepted'])
