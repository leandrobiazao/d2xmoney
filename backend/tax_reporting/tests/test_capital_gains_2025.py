"""
Tests for capital gains (IRPF) reporting — ações à vista.
"""
from decimal import Decimal

from django.test import TestCase

from brokerage_notes.models import BrokerageNote, Operation
from configuration.models import InvestmentType, InvestmentSubType
from portfolio_operations.models import CorporateEvent
from portfolio_operations.services import PortfolioService
from stocks.models import Stock
from tax_reporting.services import CapitalGainsService, EXEMPT_SALES_LIMIT
from users.models import User


def _op(op_id, tipo, ticker, qty, price, data, ordem=1):
    value = abs(qty) * price
    return {
        'id': op_id,
        'tipoOperacao': tipo,
        'tipoMercado': 'VISTA',
        'ordem': ordem,
        'titulo': ticker,
        'quantidade': qty if tipo == 'C' else -abs(qty),
        'preco': price,
        'valorOperacao': value,
        'data': data,
    }


class CapitalGainsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            name='Test IRPF User',
            cpf='111.222.333-44',
            account_provider='XP Investimentos',
            account_number='99999',
        )
        self.user_id = str(self.user.id)
        self.investment_type, _ = InvestmentType.objects.get_or_create(
            code='RENDA_VARIAVEL_REAIS',
            defaults={
                'name': 'Renda Variável em Reais',
                'is_active': True,
            },
        )
        self.stock = Stock.objects.create(
            ticker='PETR4',
            name='Petrobras PN',
            investment_type=self.investment_type,
            current_price=Decimal('30.00'),
            is_active=True,
        )
        self.stock2 = Stock.objects.create(
            ticker='VALE3',
            name='Vale ON',
            investment_type=self.investment_type,
            current_price=Decimal('60.00'),
            is_active=True,
        )

    def _persist_note(self, note_date, note_number, operations, irrf=None):
        note = BrokerageNote.objects.create(
            user_id=self.user_id,
            file_name=f'{note_number}.pdf',
            note_date=note_date,
            note_number=note_number,
            operations=operations,
            operations_count=len(operations),
            irrf_operacoes=Decimal(str(irrf)) if irrf else None,
        )
        for op in operations:
            Operation.objects.create(
                id=op['id'],
                note=note,
                tipo_operacao=op['tipoOperacao'],
                ordem=op['ordem'],
                titulo=op['titulo'],
                quantidade=op['quantidade'],
                preco=Decimal(str(op['preco'])),
                valor_operacao=Decimal(str(op['valorOperacao'])),
                data=op['data'],
                client_id=self.user_id,
            )
        return note

    def test_month_with_only_buys_not_in_report(self):
        self._persist_note(
            '15/03/2025', 'n1',
            [_op('op1', 'C', 'PETR4', 100, 10.0, '15/03/2025')],
        )
        report = CapitalGainsService.compute_capital_gains_report(self.user_id, 2025)
        self.assertEqual(report['months_with_sales_count'], 0)
        self.assertEqual(report['months'], [])

    def test_exempt_month_with_sale_appears(self):
        self._persist_note(
            '10/04/2025', 'n2',
            [
                _op('op1', 'C', 'PETR4', 100, 10.0, '01/04/2025'),
                _op('op2', 'V', 'PETR4', 50, 12.0, '10/04/2025', ordem=2),
            ],
        )
        report = CapitalGainsService.compute_capital_gains_report(self.user_id, 2025)
        self.assertEqual(len(report['months']), 1)
        month = report['months'][0]
        self.assertEqual(month['month'], 4)
        self.assertTrue(month['is_exempt'])
        self.assertEqual(month['gross_gain'], 100.0)  # (12-10)*50
        self.assertEqual(month['tax_due'], 0.0)

    def test_taxable_month(self):
        # Buy 1000 @ 10, sell 1000 @ 35 => 25000 sales, 25000 gain
        self._persist_note(
            '20/05/2025', 'n3',
            [
                _op('op1', 'C', 'PETR4', 1000, 10.0, '01/05/2025'),
                _op('op2', 'V', 'PETR4', 1000, 35.0, '20/05/2025', ordem=2),
            ],
        )
        report = CapitalGainsService.compute_capital_gains_report(self.user_id, 2025)
        month = report['months'][0]
        self.assertFalse(month['is_exempt'])
        self.assertEqual(month['total_sales'], 35000.0)
        self.assertEqual(month['taxable_gain'], 25000.0)
        self.assertEqual(month['tax_due'], 3750.0)

    def test_sparse_months_loss_compensation(self):
        # June: loss with sale (exempt)
        self._persist_note(
            '15/06/2025', 'n4',
            [
                _op('op1', 'C', 'PETR4', 100, 20.0, '01/06/2025'),
                _op('op2', 'V', 'PETR4', 100, 15.0, '15/06/2025', ordem=2),
            ],
        )
        # July/August: no sales
        # September: taxable gain
        self._persist_note(
            '10/09/2025', 'n5',
            [
                _op('op3', 'C', 'VALE3', 500, 50.0, '01/09/2025'),
                _op('op4', 'V', 'VALE3', 500, 60.0, '10/09/2025', ordem=2),
            ],
        )
        report = CapitalGainsService.compute_capital_gains_report(self.user_id, 2025)
        self.assertEqual(len(report['months']), 2)
        self.assertEqual(report['months'][0]['month'], 6)
        self.assertEqual(report['months'][0]['net_result'], -500.0)
        self.assertEqual(report['months'][1]['month'], 9)
        self.assertEqual(report['months'][1]['loss_carryforward_in'], 500.0)
        self.assertEqual(report['months'][1]['taxable_gain'], 4500.0)  # 5000 - 500
        self.assertEqual(report['months'][1]['tax_due'], 675.0)

    def test_year_without_sales_empty_months(self):
        self._persist_note(
            '01/06/2025', 'n6',
            [_op('op1', 'C', 'PETR4', 200, 10.0, '01/06/2025')],
        )
        report = CapitalGainsService.compute_capital_gains_report(self.user_id, 2025)
        self.assertEqual(report['months'], [])
        self.assertEqual(len(report['position_at_year_end']), 1)
        self.assertEqual(report['position_at_year_end'][0]['quantidade'], 200)

    def test_position_at_year_end(self):
        self._persist_note(
            '15/06/2025', 'n7',
            [
                _op('op1', 'C', 'PETR4', 100, 10.0, '01/06/2025'),
                _op('op2', 'V', 'PETR4', 40, 12.0, '10/06/2025', ordem=2),
                _op('op3', 'C', 'PETR4', 50, 11.0, '15/06/2025', ordem=3),
            ],
        )
        report = CapitalGainsService.compute_capital_gains_report(self.user_id, 2025)
        petr = next(p for p in report['position_at_year_end'] if p['ticker'] == 'PETR4')
        self.assertEqual(petr['quantidade'], 110)

    def test_replay_respects_cutoff(self):
        ops = [
            _op('op1', 'C', 'PETR4', 100, 10.0, '01/06/2025'),
            _op('op2', 'C', 'PETR4', 50, 12.0, '15/12/2025', ordem=2),
            _op('op3', 'C', 'PETR4', 25, 14.0, '10/01/2026', ordem=3),
        ]
        tickers = {'PETR4'}
        summary = PortfolioService.replay_operations(
            ops, self.user_id, cutoff_date=__import__('datetime').date(2025, 12, 31),
            allowed_tickers=tickers,
        )
        self.assertEqual(summary['PETR4']['quantidade'], 150)

    def test_exempt_limit_boundary(self):
        sales_value = float(EXEMPT_SALES_LIMIT)
        qty = 1000
        price = sales_value / qty
        self._persist_note(
            '20/08/2025', 'n8',
            [
                _op('op1', 'C', 'PETR4', qty, 10.0, '01/08/2025'),
                _op('op2', 'V', 'PETR4', qty, price, '20/08/2025', ordem=2),
            ],
        )
        report = CapitalGainsService.compute_capital_gains_report(self.user_id, 2025)
        self.assertTrue(report['months'][0]['is_exempt'])

    def test_irrf_subtracted_from_darf(self):
        self._persist_note(
            '20/05/2025', 'n9',
            [
                _op('op1', 'C', 'PETR4', 1000, 10.0, '01/05/2025'),
                _op('op2', 'V', 'PETR4', 1000, 35.0, '20/05/2025', ordem=2),
            ],
            irrf=100.0,
        )
        report = CapitalGainsService.compute_capital_gains_report(self.user_id, 2025)
        month = report['months'][0]
        self.assertEqual(month['irrf_withheld'], 100.0)
        self.assertEqual(month['darf_amount'], month['tax_due'] - 100.0)

    def test_bdr_taxed_at_15_percent_without_monthly_exemption(self):
        dolares_type, _ = InvestmentType.objects.get_or_create(
            code='RENDA_VARIAVEL_DOLARES',
            defaults={'name': 'Renda Variável em Dólares', 'is_active': True},
        )
        bdrs_subtype, _ = InvestmentSubType.objects.get_or_create(
            investment_type=dolares_type,
            code='BDRS',
            defaults={'name': 'BDRs', 'is_active': True},
        )
        Stock.objects.create(
            ticker='BERK34',
            name='Berkshire Hathaway BDR',
            investment_type=dolares_type,
            investment_subtype=bdrs_subtype,
            stock_class='BDR',
            current_price=Decimal('130.00'),
            is_active=True,
        )
        # Small sale under R$ 20k but BDR gain => still taxed
        self._persist_note(
            '10/07/2025', 'n10',
            [
                _op('op1', 'C', 'BERK34', 10, 100.0, '01/07/2025'),
                _op('op2', 'V', 'BERK34', 10, 120.0, '10/07/2025', ordem=2),
            ],
        )
        report = CapitalGainsService.compute_capital_gains_report(self.user_id, 2025)
        month = report['months'][0]
        self.assertEqual(month['bdr_sales'], 1200.0)
        self.assertFalse(month['is_exempt'])
        self.assertEqual(month['taxable_gain'], 200.0)
        self.assertEqual(month['tax_due'], 30.0)
        self.assertIn('BERK34', CapitalGainsService.get_bdr_tickers())
