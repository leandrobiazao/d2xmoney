"""
Capital gains (IRPF) reporting for Brazilian stocks (ações à vista) and BDRs.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Set, Tuple

from django.db.models import Q

from brokerage_notes.models import BrokerageNote, Operation
from configuration.models import InvestmentType
from portfolio_operations.services import PortfolioService
from stocks.models import Stock

MONTH_LABELS = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro',
}

EXEMPT_SALES_LIMIT = Decimal('20000.00')
TAX_RATE = Decimal('0.15')

AssetClass = str  # 'acoes' | 'bdr'


def _money(value: Decimal | float) -> float:
    return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def _empty_bucket() -> Dict[str, Any]:
    return {
        'total_sales': Decimal('0'),
        'gross_gain': Decimal('0'),
        'gross_loss': Decimal('0'),
        'sales_count': 0,
    }


def _parse_operation_date(date_str: str) -> Optional[date]:
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return date(year, month, day)
    except (ValueError, IndexError):
        pass
    return None


def _last_business_day_of_month(year: int, month: int) -> date:
    """Last weekday (Mon–Fri) of the given month."""
    last_day = monthrange(year, month)[1]
    current = date(year, month, last_day)
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current


def _darf_due_date(sale_year: int, sale_month: int) -> str:
    """DARF due: last business day of the month following the sale month."""
    if sale_month == 12:
        due_year, due_month = sale_year + 1, 1
    else:
        due_year, due_month = sale_year, sale_month + 1
    due = _last_business_day_of_month(due_year, due_month)
    return due.strftime('%d/%m/%Y')


def _compute_taxable_for_bucket(
    bucket: Dict[str, Any],
    loss_carryforward: Decimal,
    apply_exemption: bool,
) -> Tuple[Decimal, Decimal]:
    """Return (taxable_gain, updated_loss_carryforward)."""
    if bucket['sales_count'] == 0:
        return Decimal('0'), loss_carryforward

    net_result = bucket['gross_gain'] + bucket['gross_loss']
    is_exempt = apply_exemption and bucket['total_sales'] <= EXEMPT_SALES_LIMIT

    if is_exempt:
        if net_result < 0:
            loss_carryforward += abs(net_result)
        return Decimal('0'), loss_carryforward

    if net_result > 0:
        taxable = max(Decimal('0'), net_result - loss_carryforward)
        loss_carryforward = max(Decimal('0'), loss_carryforward - net_result)
        return taxable, loss_carryforward

    if net_result < 0:
        loss_carryforward += abs(net_result)
    return Decimal('0'), loss_carryforward


class CapitalGainsService:
    """Monthly capital gains report for ações à vista and BDRs."""

    @staticmethod
    def _get_investment_type(code: str, name_contains: str) -> Optional[InvestmentType]:
        inv_type = InvestmentType.objects.filter(code=code, is_active=True).first()
        if inv_type:
            return inv_type
        return InvestmentType.objects.filter(
            Q(code__icontains=code.split('_')[0]) | Q(name__icontains=name_contains),
            is_active=True,
        ).first()

    @staticmethod
    def get_acoes_reais_tickers() -> Set[str]:
        acoes_reais_type = CapitalGainsService._get_investment_type(
            'RENDA_VARIAVEL_REAIS', 'Renda Variável em Reais'
        )
        if not acoes_reais_type:
            return set()
        return {
            t.upper()
            for t in Stock.objects.filter(
                investment_type=acoes_reais_type, is_active=True
            ).values_list('ticker', flat=True)
        }

    @staticmethod
    def get_bdr_tickers() -> Set[str]:
        dolares_type = CapitalGainsService._get_investment_type(
            'RENDA_VARIAVEL_DOLARES', 'Renda Variável em Dólares'
        )
        if not dolares_type:
            return set()
        qs = Stock.objects.filter(investment_type=dolares_type, is_active=True)
        bdr_tickers = {
            t.upper()
            for t in qs.filter(
                Q(investment_subtype__code='BDRS') | Q(stock_class='BDR')
            ).values_list('ticker', flat=True)
        }
        return bdr_tickers

    @staticmethod
    def get_tax_report_tickers() -> Tuple[Set[str], Dict[str, AssetClass]]:
        acoes = CapitalGainsService.get_acoes_reais_tickers()
        bdrs = CapitalGainsService.get_bdr_tickers()
        ticker_class: Dict[str, AssetClass] = {t: 'acoes' for t in acoes}
        for t in bdrs:
            ticker_class[t] = 'bdr'
        return acoes | bdrs, ticker_class

    @staticmethod
    def _load_operations_as_dicts(user_id: str, allowed_tickers: Set[str]) -> List[Dict]:
        ops = Operation.objects.filter(
            note__user_id=str(user_id),
            titulo__in=allowed_tickers,
        ).select_related('note').order_by('data', 'ordem')

        result = []
        for op in ops:
            result.append({
                'id': op.id,
                'tipoOperacao': op.tipo_operacao,
                'tipoMercado': op.tipo_mercado or '',
                'ordem': op.ordem,
                'titulo': op.titulo,
                'quantidade': op.quantidade,
                'preco': float(op.preco),
                'valorOperacao': float(op.valor_operacao),
                'data': op.data,
                'clientId': user_id,
            })
        return result

    @staticmethod
    def _irrf_by_month(user_id: str, year: int) -> Dict[int, Decimal]:
        """Sum IRRF from notes that fall in each month of the year."""
        month_suffix = f'/{year}'
        notes = BrokerageNote.objects.filter(
            user_id=str(user_id),
            note_date__endswith=month_suffix,
        )
        irrf_by_month: Dict[int, Decimal] = {}
        for note in notes:
            op_date = _parse_operation_date(note.note_date)
            if not op_date or op_date.year != year:
                continue
            month = op_date.month
            irrf = note.irrf_operacoes or Decimal('0')
            irrf_by_month[month] = irrf_by_month.get(month, Decimal('0')) + irrf
        return irrf_by_month

    @staticmethod
    def compute_capital_gains_report(user_id: str, year: int) -> Dict[str, Any]:
        allowed_tickers, ticker_class = CapitalGainsService.get_tax_report_tickers()
        if not allowed_tickers:
            return {
                'year': year,
                'months_with_sales_count': 0,
                'months': [],
                'year_summary': {
                    'total_taxable_gain': 0.0,
                    'total_tax_due': 0.0,
                    'total_irrf': 0.0,
                    'remaining_loss_carryforward': 0.0,
                },
                'position_at_year_end': [],
            }

        operations = CapitalGainsService._load_operations_as_dicts(user_id, allowed_tickers)

        monthly_sales: Dict[int, Dict[str, Dict[str, Any]]] = {}

        def on_sale(operation: Dict, realized_profit: float, operation_date: date) -> None:
            if operation_date.year != year:
                return
            ticker = operation.get('titulo', '').strip().upper()
            asset_class = ticker_class.get(ticker, 'acoes')
            month = operation_date.month
            if month not in monthly_sales:
                monthly_sales[month] = {'acoes': _empty_bucket(), 'bdr': _empty_bucket()}

            bucket = monthly_sales[month][asset_class]
            sale_value = Decimal(str(abs(operation.get('valorOperacao', 0))))
            profit = Decimal(str(realized_profit))
            bucket['total_sales'] += sale_value
            bucket['sales_count'] += 1
            if profit >= 0:
                bucket['gross_gain'] += profit
            else:
                bucket['gross_loss'] += profit

        cutoff = date(year, 12, 31)
        summaries = PortfolioService.replay_operations(
            operations=operations,
            user_id=user_id,
            cutoff_date=cutoff,
            on_sale_callback=on_sale,
            allowed_tickers=allowed_tickers,
        )

        irrf_by_month = CapitalGainsService._irrf_by_month(user_id, year)

        loss_cf_acoes = Decimal('0')
        loss_cf_bdr = Decimal('0')
        months_out: List[Dict[str, Any]] = []
        year_taxable = Decimal('0')
        year_tax_due = Decimal('0')
        year_irrf = Decimal('0')

        for month in range(1, 13):
            if month not in monthly_sales:
                continue

            data = monthly_sales[month]
            acoes = data['acoes']
            bdr = data['bdr']

            if acoes['sales_count'] + bdr['sales_count'] == 0:
                continue

            loss_carryforward_in = loss_cf_acoes + loss_cf_bdr

            acoes_taxable, loss_cf_acoes = _compute_taxable_for_bucket(
                acoes, loss_cf_acoes, apply_exemption=True
            )
            bdr_taxable, loss_cf_bdr = _compute_taxable_for_bucket(
                bdr, loss_cf_bdr, apply_exemption=False
            )

            taxable_gain = acoes_taxable + bdr_taxable
            tax_due = (taxable_gain * TAX_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            loss_carryforward_out = loss_cf_acoes + loss_cf_bdr

            total_sales = acoes['total_sales'] + bdr['total_sales']
            gross_gain = acoes['gross_gain'] + bdr['gross_gain']
            gross_loss = acoes['gross_loss'] + bdr['gross_loss']
            net_result = gross_gain + gross_loss
            sales_count = acoes['sales_count'] + bdr['sales_count']

            acoes_exempt = (
                acoes['sales_count'] == 0
                or acoes['total_sales'] <= EXEMPT_SALES_LIMIT
            )
            # Month is "exempt" only when no IR is due (ações isentas e BDR sem base tributável)
            is_exempt = tax_due == 0

            irrf = irrf_by_month.get(month, Decimal('0'))
            darf_amount = max(Decimal('0'), tax_due - irrf)

            year_taxable += taxable_gain
            year_tax_due += tax_due
            year_irrf += irrf

            months_out.append({
                'month': month,
                'label': f'{MONTH_LABELS[month]}/{year}',
                'total_sales': _money(total_sales),
                'acoes_sales': _money(acoes['total_sales']),
                'bdr_sales': _money(bdr['total_sales']),
                'is_exempt': is_exempt,
                'acoes_exempt': acoes_exempt,
                'gross_gain': _money(gross_gain),
                'gross_loss': _money(gross_loss),
                'net_result': _money(net_result),
                'loss_carryforward_in': _money(loss_carryforward_in),
                'loss_carryforward_out': _money(loss_carryforward_out),
                'taxable_gain': _money(taxable_gain),
                'tax_rate': float(TAX_RATE),
                'tax_due': _money(tax_due),
                'irrf_withheld': _money(irrf),
                'darf_amount': _money(darf_amount),
                'darf_due_date': _darf_due_date(year, month),
                'sales_count': sales_count,
            })

        position_at_year_end = []
        for ticker, summary in sorted(summaries.items()):
            qty = summary.get('quantidade', 0)
            if qty <= 0:
                continue
            asset_class = ticker_class.get(ticker.upper(), 'acoes')
            position_at_year_end.append({
                'ticker': ticker,
                'asset_class': asset_class,
                'asset_class_label': 'BDR' if asset_class == 'bdr' else 'Ação',
                'quantidade': int(qty),
                'preco_medio': round(float(summary.get('precoMedio', 0)), 2),
                'valor_total_investido': round(float(summary.get('valorTotalInvestido', 0)), 2),
            })

        return {
            'year': year,
            'months_with_sales_count': len(months_out),
            'months': months_out,
            'year_summary': {
                'total_taxable_gain': _money(year_taxable),
                'total_tax_due': _money(year_tax_due),
                'total_irrf': _money(year_irrf),
                'remaining_loss_carryforward': _money(loss_cf_acoes + loss_cf_bdr),
            },
            'position_at_year_end': position_at_year_end,
        }
