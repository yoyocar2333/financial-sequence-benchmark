"""Synthetic contract tests; never a substitute for historical source/manual QA."""
import unittest
from e8a_core import clock_level, strict_eligibility, proxy_session, feature_ready, instant

class PITContract(unittest.TestCase):
    def row(self, **changes):
        r = {'publication_date': '2025-01-06', 'published_at': '2025-01-06T15:00:00Z',
             'precision': 'publisher_time_claim', 'retrieved_at': '2026-11-08T00:00:00Z'}
        r.update(changes); return r

    def certified(self, **changes):
        r = self.row(verified_public_version_at='2025-01-06T15:00:00Z',
                     version_evidence_verified=True, use_permission_verified=True,
                     deleted_or_withdrawn=False)
        r.update(changes); return r

    def test_publisher_claim_does_not_prove_PIT(self):
        self.assertEqual(clock_level(self.row()), 'L2_PUBLISHER_TIME_CLAIM')
        self.assertFalse(strict_eligibility(self.row(), '2025-01-06T22:00:00Z')[0])

    def test_retrieval_not_historical_capture(self):
        r = self.row(version_evidence_verified=True)
        self.assertFalse(strict_eligibility(r, '2025-01-06T22:00:00Z')[0])

    def test_CSV_true_string_not_verified_evidence(self):
        self.assertEqual(clock_level(self.certified(version_evidence_verified='True')), 'L2_PUBLISHER_TIME_CLAIM')

    def test_midnight_precision_is_date_like(self):
        self.assertEqual(clock_level(self.row(published_at='2025-01-06T00:00:00Z', precision='midnight_unverified')), 'L1_DATE_PROXY')

    def test_naive_time_not_assumed_UTC(self):
        self.assertIsNone(instant('2025-01-06T12:00:00'))

    def test_invalid_date_unusable(self):
        self.assertEqual(clock_level({'publication_date': '2025-90-31'}), 'L0_UNUSABLE_TIME')

    def test_source_qualification_with_synthetic_evidence(self):
        self.assertTrue(strict_eligibility(self.certified(), '2025-01-06T22:00:00Z')[0])
        self.assertEqual(clock_level(self.certified()), 'L3_SOURCE_VERSION_VERIFIED')

    def test_vendor_arrival_separate_from_source(self):
        self.assertFalse(strict_eligibility(self.certified(), '2025-01-06T22:00:00Z', 'arrival')[0])

    def test_after_cutoff_arrival_rejected(self):
        r = self.certified(verified_arrival_at='2025-01-07T10:00:00Z')
        self.assertTrue(strict_eligibility(r, '2025-01-06T22:00:00Z', 'source')[0])
        self.assertFalse(strict_eligibility(r, '2025-01-06T22:00:00Z', 'arrival')[0])

    def test_later_version_not_backdated_to_article_creation(self):
        r = self.certified(verified_public_version_at='2025-01-08T12:00:00Z')
        self.assertFalse(strict_eligibility(r, '2025-01-06T22:00:00Z')[0])

    def test_historical_capture_is_conservative_bound(self):
        r = self.certified(verified_public_version_at='', verified_capture_at='2025-01-07T10:00:00Z')
        self.assertFalse(strict_eligibility(r, '2025-01-06T22:00:00Z')[0])
        self.assertTrue(strict_eligibility(r, '2025-01-07T22:00:00Z')[0])

    def test_unknown_use_rights_not_qualified(self):
        self.assertFalse(strict_eligibility(self.certified(use_permission_verified=False), '2025-01-06T22:00:00Z')[0])

    def test_deletion_compliance_not_ignored(self):
        self.assertFalse(strict_eligibility(self.certified(deleted_or_withdrawn=True), '2025-01-06T22:00:00Z')[0])

    def test_date_only_next_observed_session(self):
        r = self.row(published_at='', precision='date_only')
        self.assertEqual(proxy_session(r, ['2025-01-06', '2025-01-07']), '2025-01-07')

    def test_weekend_to_next_observed_session(self):
        r = self.row(publication_date='2025-01-04', published_at='', precision='date_only')
        self.assertEqual(proxy_session(r, ['2025-01-03', '2025-01-06']), '2025-01-06')

    def test_holiday_uses_observed_calendar(self):
        r = self.row(publication_date='2025-01-08', published_at='', precision='date_only')
        self.assertEqual(proxy_session(r, ['2025-01-08', '2025-01-10']), '2025-01-10')

    def test_winter_17ET_is22UTC(self):
        r = self.row(published_at='2025-01-06T22:00:00Z')
        self.assertEqual(proxy_session(r, ['2025-01-06', '2025-01-07']), '2025-01-06')

    def test_after_17ET_deferred(self):
        r = self.row(published_at='2025-01-06T22:00:01Z')
        self.assertEqual(proxy_session(r, ['2025-01-06', '2025-01-07']), '2025-01-07')

    def test_summer_DST_boundary(self):
        r = self.row(publication_date='2025-07-07', published_at='2025-07-07T21:00:01Z')
        self.assertEqual(proxy_session(r, ['2025-07-07', '2025-07-08']), '2025-07-08')

    def test_delay_preserves_session_count(self):
        r = self.row(published_at='', precision='date_only')
        self.assertEqual(proxy_session(r, ['2025-01-06', '2025-01-07', '2025-01-08'], 1), '2025-01-08')

    def test_end_of_calendar_not_imputed(self):
        self.assertIsNone(proxy_session(self.row(published_at='', precision='date_only'), ['2025-01-06']))

    def test_full_calendar_independent_of_purged_evaluation_dates(self):
        r = self.row(publication_date='2023-12-20', published_at='', precision='date_only')
        full_calendar = ['2023-12-20', '2023-12-21', '2024-01-02']
        purged_evaluation = ['2023-12-20', '2024-01-02']
        self.assertEqual(proxy_session(r, full_calendar), '2023-12-21')
        self.assertNotEqual(proxy_session(r, full_calendar), proxy_session(r, purged_evaluation))

    def test_future_inference_not_deployed_feature(self):
        self.assertFalse(feature_ready('2025-01-06T15:00:00Z', '2019-01-01T00:00:00Z', '2026-10-26T00:00:00Z', '2025-01-06T22:00:00Z'))

    def test_future_model_release_not_deployed_feature(self):
        self.assertFalse(feature_ready('2025-01-06T15:00:00Z', '2026-01-01T00:00:00Z', '2025-01-06T18:00:00Z', '2025-01-06T22:00:00Z'))

    def test_observed_feature_clock_all_ready(self):
        self.assertTrue(feature_ready('2025-01-06T15:00:00Z', '2019-01-01T00:00:00Z', '2025-01-06T18:00:00Z', '2025-01-06T22:00:00Z'))

if __name__ == '__main__':
    unittest.main(verbosity=2)
