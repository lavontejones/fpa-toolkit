import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from fpa import variance, forecast, load_actuals, build_report, money

class FinanceTests(unittest.TestCase):
    def test_variance_sign_and_zero(self):
        self.assertEqual(variance(110,100,'revenue')['favorable_variance'],10)
        self.assertEqual(variance(110,100,'expense')['favorable_variance'],-10)
        self.assertIsNone(variance(10,0,'revenue')['variance_pct'])
    def test_rounding_and_nonfinite(self):
        self.assertEqual(money('1.005'),Decimal('1.01'))
        with self.assertRaises(ValueError): money('NaN')
    def test_forecast_reconciles(self):
        rows=forecast(100,100,.4,50,.1,2)
        self.assertEqual(rows[0]['closing_cash'],110)
        self.assertEqual(rows[1]['revenue'],110)
        self.assertEqual(rows[1]['closing_cash'],126)
    def test_funding_gap_is_visible(self):
        self.assertEqual(forecast(0,10,.5,20,0,1)[0]['closing_cash'],-15)
    def test_invalid_assumptions(self):
        for rate,growth,months in [(1.1,0,12),(.4,-1,12),(.4,0,0)]:
            with self.assertRaises(ValueError): forecast(100,100,rate,10,growth,months)
    def test_duplicate_actuals_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'x.csv';p.write_text('month,account,kind,budget,actual\n2026-01,Revenue,revenue,1,2\n2026-01,Revenue,revenue,1,2\n')
            with self.assertRaises(ValueError): load_actuals(p)
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            actuals,scenarios=build_report('samples/actuals.csv',tmp,'samples/assumptions.json')
            self.assertEqual(len(actuals),12)
            self.assertEqual(len(scenarios['base']),12)
            self.assertTrue((Path(tmp)/'report.html').is_file())
            self.assertIn('Synthetic', (Path(tmp)/'report.html').read_text())
if __name__=='__main__': unittest.main()
