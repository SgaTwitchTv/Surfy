from datetime import datetime, timedelta, timezone
import unittest

from greenwave.observation_completeness import point_completeness


def event(seconds, state, run='a', kind='STATE_START', classification='KEEP'):
    return dict(timestamp=(datetime(2026, 9, 26, tzinfo=timezone.utc)+timedelta(seconds=seconds)).isoformat(),
        record_sequence=int(seconds*10)+1, run_id=run, state=state, reviewed_type=kind,
        classification=classification, gps_freshness='FRESH')


class CompletenessTests(unittest.TestCase):
    def test_empty_and_seen_only_do_not_produce_phase_intervals(self):
        self.assertEqual(point_completeness([])['status'],'NO_DATA')
        report=point_completeness([event(0,'RED',kind='STATE_SEEN'),event(10,'GREEN',kind='STATE_SEEN')])
        self.assertEqual(report['start_count'],0)
        self.assertEqual(report['intervals'],[])
        self.assertFalse(report['model_validated'])

    def test_never_connects_different_runs_or_across_seen_color(self):
        report=point_completeness([event(0,'RED'),event(10,'GREEN',run='b')])
        self.assertEqual(report['intervals'],[])
        report=point_completeness([event(0,'RED'),event(5,'YELLOW',kind='STATE_SEEN'),event(10,'GREEN')])
        self.assertEqual(report['intervals'],[])
        self.assertEqual(report['recurrences'],[])

    def test_duplicate_does_not_shift_red_onset_and_green_red_is_not_green_duration(self):
        report=point_completeness([event(0,'RED'),event(.5,'RED',classification='RAPID_DUPLICATE'),
                                  event(10,'GREEN'),event(30,'RED')])
        self.assertEqual(report['intervals'][0]['seconds'],10)
        self.assertEqual(report['intervals'][1]['interpretation'],'TRANSITION_INTERVAL_ONLY')
        self.assertEqual(len(report['recurrences']),1)
        self.assertEqual(report['duplicate_count'],1)

    def test_repeated_phase_intervals_do_not_enable_live_or_prove_cycles(self):
        report=point_completeness([event(0,'GREEN'),event(20,'YELLOW'),event(22,'RED'),
            event(50,'GREEN'),event(70,'YELLOW'),event(72,'RED'),event(100,'GREEN')])
        self.assertEqual(report['status'],'REPEATED_INTERVALS')
        self.assertEqual(report['interval_counts']['GREEN_YELLOW'],2)
        self.assertEqual(report['intervals'][0]['interpretation'],'OBSERVED_GREEN_DURATION')
        self.assertFalse(report['model_validated'])
        self.assertTrue(all(e['interpretation']=='OBSERVED_RECURRENCE_NOT_PROVEN_SINGLE_CYCLE'
                            for e in report['recurrences']))

    def test_same_color_without_intervening_phase_is_not_cycle(self):
        report=point_completeness([event(0,'GREEN'),event(60,'GREEN')])
        self.assertEqual(report['recurrences'],[])
        self.assertEqual(report['intervals'],[])

    def test_unresolved_repeated_color_breaks_interval_evidence(self):
        report=point_completeness([event(0,'RED'),
            event(60,'RED',classification='REPEATED_STATE_REVIEW'),event(70,'GREEN')])
        self.assertEqual(report['intervals'],[])
        self.assertEqual(report['repeated_review_count'],1)
