"""Tests for fixed income Excel import (BTG vs legado)."""
from datetime import date

from django.test import TestCase

from fixed_income.btg_excel_import import user_is_btg
from fixed_income import btg_excel_import as btg_mod


class BtgExcelImportUnitTests(TestCase):
    def test_user_is_btg_detects_btg_pactual(self):
        self.assertTrue(user_is_btg('BTG Pactual'))
        self.assertTrue(user_is_btg('btg'))

    def test_user_is_btg_false_for_xp(self):
        self.assertFalse(user_is_btg('XP Investimentos'))
        self.assertFalse(user_is_btg(''))

    def test_btg_asset_code_stable(self):
        self.assertEqual(
            btg_mod._btg_asset_code('LTN', date(2030, 1, 1)),
            'BTG_LTN_20300101',
        )
        self.assertEqual(
            btg_mod._btg_asset_code('NTNB-P', date(2028, 8, 15)),
            'BTG_NTNB_P_20280815',
        )
