import unittest

from greenwave.positioning import ExternalPositionProvider


class ExternalPositionProviderTests(unittest.TestCase):
    def test_latest_phone_sample_preserves_gnss_and_imu_fields(self):
        provider = ExternalPositionProvider()
        provider.update(timestamp_seconds=12.5, latitude=52.2, longitude=20.9,
                        speed_mps=8.0, heading_deg=91.0, gps_accuracy_m=3.2,
                        acceleration_mps2=-0.4)
        sample = provider.sample()
        self.assertEqual(sample.source, 'EXTERNAL')
        self.assertEqual(sample.road_position_m, None)
        self.assertEqual(sample.latitude, 52.2)
        self.assertEqual(sample.speed_mps, 8.0)
        self.assertEqual(sample.raw_speed_mps, 8.0)
        self.assertEqual(sample.speed_source, 'DEVICE')
        self.assertEqual(sample.position_quality, 'GOOD')
        self.assertTrue(sample.usable_for_live)
        self.assertEqual(sample.acceleration_mps2, -0.4)

    def test_missing_device_speed_is_calculated_from_accurate_points(self):
        provider = ExternalPositionProvider()
        provider.update(timestamp_seconds=10, latitude=52.2, longitude=20.9,
                        speed_mps=None, gps_accuracy_m=4)
        sample = provider.update(timestamp_seconds=12, latitude=52.2,
                                 longitude=20.9003, speed_mps=None,
                                 gps_accuracy_m=4)
        self.assertIsNone(sample.raw_speed_mps)
        self.assertIsNotNone(sample.calculated_speed_mps)
        self.assertEqual(sample.speed_mps, sample.calculated_speed_mps)
        self.assertEqual(sample.speed_source, 'CALCULATED')
        self.assertGreater(sample.speed_mps, 5)
        self.assertLess(sample.speed_mps, 15)

    def test_poor_fix_is_visible_but_not_usable_for_live(self):
        provider = ExternalPositionProvider()
        sample = provider.update(timestamp_seconds=10, latitude=52.2,
                                 longitude=20.9, speed_mps=None,
                                 gps_accuracy_m=195)
        status = provider.status()
        self.assertEqual(sample.position_quality, 'UNUSABLE')
        self.assertFalse(sample.usable_for_live)
        self.assertIn('GPS_ACCURACY_TOO_LOW', sample.quality_reasons)
        self.assertEqual(status['quality_rejected_count'], 1)
        self.assertIn('195', status['diagnostic'])

    def test_stationary_filter_suppresses_low_device_speed_after_confirmation(self):
        provider = ExternalPositionProvider()
        sample = None
        for index in range(6):
            sample = provider.update(timestamp_seconds=10 + index,
                                     latitude=52.2, longitude=20.9,
                                     speed_mps=0.55, gps_accuracy_m=10)
        self.assertEqual(sample.raw_speed_mps, 0.55)
        self.assertEqual(sample.speed_mps, 0)
        self.assertEqual(sample.speed_source, 'STATIONARY_FILTER')
        self.assertIn('postój', provider.status()['diagnostic'])

    def test_stationary_filter_keeps_real_slow_movement(self):
        provider = ExternalPositionProvider()
        sample = None
        for index in range(6):
            sample = provider.update(timestamp_seconds=10 + index,
                                     latitude=52.2 + index * 0.000009,
                                     longitude=20.9, speed_mps=0.55,
                                     gps_accuracy_m=10)
        self.assertEqual(sample.speed_mps, 0.55)
        self.assertEqual(sample.speed_source, 'DEVICE')

    def test_invalid_sensor_values_are_rejected(self):
        provider = ExternalPositionProvider()
        with self.assertRaises(ValueError):
            provider.update(timestamp_seconds=1, speed_mps=-1)
        with self.assertRaises(ValueError):
            provider.update(timestamp_seconds=1, speed_mps=1, latitude=float('nan'))
        with self.assertRaises(ValueError):
            provider.update(timestamp_seconds=1, speed_mps=1, latitude=91, longitude=20)


if __name__ == '__main__':
    unittest.main()
