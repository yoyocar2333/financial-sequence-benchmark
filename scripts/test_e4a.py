"""Meaningful PIT boundary tests, independent of the real news population."""
import unittest
import numpy as np
import pandas as pd
from e4a_core import cutoff_utc, strict_availability, map_available, date_only_projection, eligible_record_at, observed_count


class PITTests(unittest.TestCase):
    def record(self, **kw):
        r = dict(published_utc='2025-03-07T21:00:00Z',version_seen_utc='2025-03-07T21:00:01Z',
            historical_text_revision_verified=True,text_sha256='a'*64,availability_evidence='archived feed version')
        r.update(kw); return r

    def test_dst_and_next_open(self):
        dates = pd.to_datetime(['2025-03-07','2025-03-10'])
        self.assertEqual(list(cutoff_utc(dates).hour),[22,21])

    def test_deadline_equality_and_late_arrival(self):
        dates = pd.to_datetime(['2025-03-07','2025-03-10'])
        self.assertEqual(map_available(pd.Timestamp('2025-03-07T22:00:00Z'),dates),dates[0])
        self.assertEqual(map_available(pd.Timestamp('2025-03-07T22:00:00.001Z'),dates),dates[1])

    def test_timezone_required(self):
        self.assertIsNone(strict_availability(self.record(published_utc='2025-03-07 13:00'))[0])
        self.assertIsNone(strict_availability(self.record(published_utc='2025-03-07'))[0])

    def test_backfill_does_not_certify_history(self):
        self.assertIsNone(strict_availability(self.record(version_seen_utc='',retrieved_utc='2026-10-26T00:00:00Z'))[0])

    def test_exact_version_needed(self):
        self.assertIsNone(strict_availability(self.record(historical_text_revision_verified=False))[0])
        self.assertIsNone(strict_availability(self.record(availability_evidence=''))[0])

    def test_embargo_and_update(self):
        r=self.record(embargo_until_utc='2025-03-10T12:00:00Z',version_published_utc='2025-03-10T13:00:00Z')
        self.assertEqual(strict_availability(r)[0],pd.Timestamp('2025-03-10T13:00:00Z'))

    def test_future_news_cannot_enter_features(self):
        r=self.record(version_seen_utc='2025-03-10T21:01:00Z')
        self.assertFalse(eligible_record_at(r,'2025-03-10T21:00:00Z')[0])

    def test_holiday_date_only(self):
        dates=pd.to_datetime(['2025-07-03','2025-07-07','2025-07-08'])
        self.assertEqual(date_only_projection('2025-07-03',dates),dates[1])
        self.assertEqual(date_only_projection('2025-07-04',dates),dates[1])
        self.assertIsNone(date_only_projection('2025-07-08',dates))

    def test_unknown_is_not_no_news(self):
        news=pd.DataFrame({'ticker':['AAPL'],'information_date':['2025-03-10']})
        self.assertTrue(np.isnan(observed_count(news,'TSLA','2025-03-10',False)))
        self.assertEqual(observed_count(news,'TSLA','2025-03-10',True),0)


if __name__=='__main__': unittest.main(verbosity=2)
