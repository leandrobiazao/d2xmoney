"""
Capital gains (IRPF) reporting for ações, FIIs, ETFs, and BDRs.
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

AssetClass = str  # 'acoes' | 'fii' | 'etf' | 'bdr'

ASSET_CLASS_LABELS = {
    'acoes': 'Ação',
    'fii': 'FII',
    'etf': 'ETF',
    'bdr': 'BDR',
}


def _money(value: Decimal | float) -> float:
    return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def _empty_bucket() -> Dict[str, Any]:
    return {
        'total_sales': Decimal('0'),
        'gross_gain': Decimal('0'),
        'gross_loss': Decimal('0'),
        'sales_count': 0,
    }


def _empty_carryforward_report() -> Dict[str, Any]:
    return {
        'months_with_sales_count': 0,
        'months': [],
        'year_summary': {
            'total_taxable_gain': 0.0,
            'total_tax_due': 0.0,
            'total_irrf': 0.0,
            'remaining_loss_carryforward': 0.0,
        },
    }


def _empty_etf_bdr_report() -> Dict[str, Any]:
    return {
        'months_with_sales_count': 0,
        'months': [],
        'year_summary': {
            'total_taxable_gain': 0.0,
            'total_tax_due': 0.0,
            'total_irrf': 0.0,
        },
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


def _compute_tax_no_carryforward(bucket: Dict[str, Any]) -> Decimal:
    """ETF/BDR: 15% on positive monthly net; losses are not carried forward."""
    if bucket['sales_count'] == 0:
        return Decimal('0')
    net_result = bucket['gross_gain'] + bucket['gross_loss']
    return max(Decimal('0'), net_result)


def _allocate_irrf_proportional(
    total_irrf: Decimal,
    tax_dues: Dict[str, Decimal],
) -> Dict[str, Decimal]:
    """Split note IRRF across report sections proportional to tax due."""
    keys = list(tax_dues.keys())
    if total_irrf <= 0:
        return {k: Decimal('0') for k in keys}

    total_tax = sum(tax_dues.values())
    if total_tax <= 0:
        return {k: Decimal('0') for k in keys}

    positive_keys = [k for k in keys if tax_dues[k] > 0]
    result: Dict[str, Decimal] = {k: Decimal('0') for k in keys}
    allocated = Decimal('0')
    for i, key in enumerate(positive_keys):
        if i == len(positive_keys) - 1:
            result[key] = total_irrf - allocated
        else:
            share = (total_irrf * tax_dues[key] / total_tax).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            result[key] = share
            allocated += share
    return result


class CapitalGainsService:
    """Monthly capital gains report for ações, FIIs, ETFs, and BDRs."""

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
    def get_etf_tickers() -> Set[str]:
        return {
            t.upper()
            for t in Stock.objects.filter(is_active=True).filter(
                Q(stock_class='ETF') | Q(investment_subtype__code='ETF_RENDA_FIXA')
            ).values_list('ticker', flat=True)
        }

    @staticmethod
    def get_fii_tickers() -> Set[str]:
        etf_tickers = CapitalGainsService.get_etf_tickers()
        fiis_type = CapitalGainsService._get_investment_type('FIIS', 'Fundos Imobiliários')
        qs = Stock.objects.filter(is_active=True)
        if fiis_type:
            qs = qs.filter(Q(investment_type=fiis_type) | Q(stock_class='FII'))
        else:
            qs = qs.filter(stock_class='FII')
        return {
            t.upper()
            for t in qs.values_list('ticker', flat=True)
            if t.upper() not in etf_tickers
        }

    @staticmethod
    def get_acoes_reais_tickers() -> Set[str]:
        acoes_reais_type = CapitalGainsService._get_investment_type(
            'RENDA_VARIAVEL_REAIS', 'Renda Variável em Reais'
        )
        if not acoes_reais_type:
            return set()
        etf_tickers = CapitalGainsService.get_etf_tickers()
        fii_tickers = CapitalGainsService.get_fii_tickers()
        excluded = etf_tickers | fii_tickers
        return {
            t.upper()
            for t in Stock.objects.filter(
                investment_type=acoes_reais_type, is_active=True
            ).exclude(stock_class='ETF').values_list('ticker', flat=True)
            if t.upper() not in excluded
        }

    @staticmethod
    def get_bdr_tickers() -> Set[str]:
        dolares_type = CapitalGainsService._get_investment_type(
            'RENDA_VARIAVEL_DOLARES', 'Renda Variável em Dólares'
        )
        if not dolares_type:
            return set()
        qs = Stock.objects.filter(investment_type=dolares_type, is_active=True)
        return {
            t.upper()
            for t in qs.filter(
                Q(investment_subtype__code='BDRS') | Q(stock_class='BDR')
            ).values_list('ticker', flat=True)
        }

    @staticmethod
    def get_tax_report_tickers() -> Tuple[Set[str], Dict[str, AssetClass]]:
        bdrs = CapitalGainsService.get_bdr_tickers()
        etfs = CapitalGainsService.get_etf_tickers()
        fiis = CapitalGainsService.get_fii_tickers()
        acoes = CapitalGainsService.get_acoes_reais_tickers()

        ticker_class: Dict[str, AssetClass] = {}
        for t in acoes:
            ticker_class[t] = 'acoes'
        for t in fiis:
            ticker_class[t] = 'fii'
        for t in etfs:
            ticker_class[t] = 'etf'
        for t in bdrs:
            ticker_class[t] = 'bdr'

        all_tickers = acoes | fiis | etfs | bdrs
        return all_tickers, ticker_class

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
    def _prelim_tax_by_month(
        monthly_data: Dict[int, Dict[str, Any]],
        apply_exemption: bool,
    ) -> Dict[int, Decimal]:
        loss_cf = Decimal('0')
        tax_by_month: Dict[int, Decimal] = {}
        for month in range(1, 13):
            if month not in monthly_data:
                continue
            bucket = monthly_data[month]
            if bucket['sales_count'] == 0:
                continue
            taxable, loss_cf = _compute_taxable_for_bucket(
                bucket, loss_cf, apply_exemption=apply_exemption
            )
            tax_by_month[month] = (taxable * TAX_RATE).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        return tax_by_month

    @staticmethod
    def _build_carryforward_months(
        monthly_data: Dict[int, Dict[str, Any]],
        irrf_for_section_by_month: Dict[int, Decimal],
        year: int,
        apply_exemption: bool,
    ) -> Tuple[List[Dict[str, Any]], Decimal, Decimal, Decimal, Decimal]:
        loss_cf = Decimal('0')
        months_out: List[Dict[str, Any]] = []
        year_taxable = Decimal('0')
        year_tax_due = Decimal('0')
        year_irrf = Decimal('0')

        for month in range(1, 13):
            if month not in monthly_data:
                continue

            bucket = monthly_data[month]
            if bucket['sales_count'] == 0:
                continue

            loss_carryforward_in = loss_cf
            taxable_gain, loss_cf = _compute_taxable_for_bucket(
                bucket, loss_cf, apply_exemption=apply_exemption
            )
            tax_due = (taxable_gain * TAX_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            net_result = bucket['gross_gain'] + bucket['gross_loss']
            is_exempt = apply_exemption and (
                bucket['total_sales'] <= EXEMPT_SALES_LIMIT or tax_due == 0
            )
            if not apply_exemption:
                is_exempt = tax_due == 0

            irrf = irrf_for_section_by_month.get(month, Decimal('0'))
            darf_amount = max(Decimal('0'), tax_due - irrf)

            year_taxable += taxable_gain
            year_tax_due += tax_due
            year_irrf += irrf

            months_out.append({
                'month': month,
                'label': f'{MONTH_LABELS[month]}/{year}',
                'total_sales': _money(bucket['total_sales']),
                'is_exempt': is_exempt,
                'gross_gain': _money(bucket['gross_gain']),
                'gross_loss': _money(bucket['gross_loss']),
                'net_result': _money(net_result),
                'loss_carryforward_in': _money(loss_carryforward_in),
                'loss_carryforward_out': _money(loss_cf),
                'taxable_gain': _money(taxable_gain),
                'tax_rate': float(TAX_RATE),
                'tax_due': _money(tax_due),
                'irrf_withheld': _money(irrf),
                'darf_amount': _money(darf_amount),
                'darf_due_date': _darf_due_date(year, month),
                'sales_count': bucket['sales_count'],
            })

        return months_out, year_taxable, year_tax_due, year_irrf, loss_cf

    @staticmethod
    def _build_etf_bdr_months(
        monthly_data: Dict[int, Dict[str, Dict[str, Any]]],
        irrf_for_section_by_month: Dict[int, Decimal],
        year: int,
    ) -> Tuple[List[Dict[str, Any]], Decimal, Decimal, Decimal]:
        months_out: List[Dict[str, Any]] = []
        year_taxable = Decimal('0')
        year_tax_due = Decimal('0')
        year_irrf = Decimal('0')

        for month in range(1, 13):
            if month not in monthly_data:
                continue

            data = monthly_data[month]
            etf = data['etf']
            bdr = data['bdr']

            if etf['sales_count'] + bdr['sales_count'] == 0:
                continue

            etf_taxable = _compute_tax_no_carryforward(etf)
            bdr_taxable = _compute_tax_no_carryforward(bdr)
            taxable_gain = etf_taxable + bdr_taxable
            tax_due = (taxable_gain * TAX_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            total_sales = etf['total_sales'] + bdr['total_sales']
            gross_gain = etf['gross_gain'] + bdr['gross_gain']
            gross_loss = etf['gross_loss'] + bdr['gross_loss']
            net_result = gross_gain + gross_loss
            sales_count = etf['sales_count'] + bdr['sales_count']

            month_irrf_total = irrf_for_section_by_month.get(month, Decimal('0'))
            darf_amount = max(Decimal('0'), tax_due - month_irrf_total)

            year_taxable += taxable_gain
            year_tax_due += tax_due
            year_irrf += month_irrf_total

            months_out.append({
                'month': month,
                'label': f'{MONTH_LABELS[month]}/{year}',
                'total_sales': _money(total_sales),
                'etf_sales': _money(etf['total_sales']),
                'bdr_sales': _money(bdr['total_sales']),
                'gross_gain': _money(gross_gain),
                'gross_loss': _money(gross_loss),
                'net_result': _money(net_result),
                'taxable_gain': _money(taxable_gain),
                'tax_rate': float(TAX_RATE),
                'tax_due': _money(tax_due),
                'irrf_withheld': _money(month_irrf_total),
                'darf_amount': _money(darf_amount),
                'darf_due_date': _darf_due_date(year, month),
                'sales_count': sales_count,
            })

        return months_out, year_taxable, year_tax_due, year_irrf

    @staticmethod
    def compute_capital_gains_report(user_id: str, year: int) -> Dict[str, Any]:
        allowed_tickers, ticker_class = CapitalGainsService.get_tax_report_tickers()
        if not allowed_tickers:
            return {
                'year': year,
                'acoes': _empty_carryforward_report(),
                'fii': _empty_carryforward_report(),
                'etf_bdr': _empty_etf_bdr_report(),
                'position_at_year_end': [],
            }

        operations = CapitalGainsService._load_operations_as_dicts(user_id, allowed_tickers)

        monthly_acoes: Dict[int, Dict[str, Any]] = {}
        monthly_fii: Dict[int, Dict[str, Any]] = {}
        monthly_etf_bdr: Dict[int, Dict[str, Dict[str, Any]]] = {}

        def on_sale(operation: Dict, realized_profit: float, operation_date: date) -> None:
            if operation_date.year != year:
                return
            ticker = operation.get('titulo', '').strip().upper()
            asset_class = ticker_class.get(ticker, 'acoes')
            month = operation_date.month

            if asset_class == 'acoes':
                if month not in monthly_acoes:
                    monthly_acoes[month] = _empty_bucket()
                bucket = monthly_acoes[month]
            elif asset_class == 'fii':
                if month not in monthly_fii:
                    monthly_fii[month] = _empty_bucket()
                bucket = monthly_fii[month]
            else:
                if month not in monthly_etf_bdr:
                    monthly_etf_bdr[month] = {'etf': _empty_bucket(), 'bdr': _empty_bucket()}
                bucket = monthly_etf_bdr[month][asset_class]

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

        acoes_prelim = CapitalGainsService._prelim_tax_by_month(monthly_acoes, apply_exemption=True)
        fii_prelim = CapitalGainsService._prelim_tax_by_month(monthly_fii, apply_exemption=False)

        etf_bdr_prelim: Dict[int, Decimal] = {}
        for month, data in monthly_etf_bdr.items():
            etf_taxable = _compute_tax_no_carryforward(data['etf'])
            bdr_taxable = _compute_tax_no_carryforward(data['bdr'])
            combined = etf_taxable + bdr_taxable
            etf_bdr_prelim[month] = (combined * TAX_RATE).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

        all_months = set(monthly_acoes) | set(monthly_fii) | set(monthly_etf_bdr)
        irrf_acoes_by_month: Dict[int, Decimal] = {}
        irrf_fii_by_month: Dict[int, Decimal] = {}
        irrf_etf_bdr_by_month: Dict[int, Decimal] = {}
        for month in all_months:
            split = _allocate_irrf_proportional(
                irrf_by_month.get(month, Decimal('0')),
                {
                    'acoes': acoes_prelim.get(month, Decimal('0')),
                    'fii': fii_prelim.get(month, Decimal('0')),
                    'etf_bdr': etf_bdr_prelim.get(month, Decimal('0')),
                },
            )
            irrf_acoes_by_month[month] = split['acoes']
            irrf_fii_by_month[month] = split['fii']
            irrf_etf_bdr_by_month[month] = split['etf_bdr']

        acoes_months, ac_taxable, ac_tax_due, ac_irrf, loss_cf_acoes = (
            CapitalGainsService._build_carryforward_months(
                monthly_acoes, irrf_acoes_by_month, year, apply_exemption=True
            )
        )
        fii_months, fii_taxable, fii_tax_due, fii_irrf, loss_cf_fii = (
            CapitalGainsService._build_carryforward_months(
                monthly_fii, irrf_fii_by_month, year, apply_exemption=False
            )
        )
        etf_bdr_months, eb_taxable, eb_tax_due, eb_irrf = (
            CapitalGainsService._build_etf_bdr_months(
                monthly_etf_bdr, irrf_etf_bdr_by_month, year
            )
        )

        position_at_year_end = []
        for ticker, summary in sorted(summaries.items()):
            qty = summary.get('quantidade', 0)
            if qty <= 0:
                continue
            asset_class = ticker_class.get(ticker.upper(), 'acoes')
            position_at_year_end.append({
                'ticker': ticker,
                'asset_class': asset_class,
                'asset_class_label': ASSET_CLASS_LABELS.get(asset_class, 'Ação'),
                'quantidade': int(qty),
                'preco_medio': round(float(summary.get('precoMedio', 0)), 2),
                'valor_total_investido': round(float(summary.get('valorTotalInvestido', 0)), 2),
            })

        return {
            'year': year,
            'acoes': {
                'months_with_sales_count': len(acoes_months),
                'months': acoes_months,
                'year_summary': {
                    'total_taxable_gain': _money(ac_taxable),
                    'total_tax_due': _money(ac_tax_due),
                    'total_irrf': _money(ac_irrf),
                    'remaining_loss_carryforward': _money(loss_cf_acoes),
                },
            },
            'fii': {
                'months_with_sales_count': len(fii_months),
                'months': fii_months,
                'year_summary': {
                    'total_taxable_gain': _money(fii_taxable),
                    'total_tax_due': _money(fii_tax_due),
                    'total_irrf': _money(fii_irrf),
                    'remaining_loss_carryforward': _money(loss_cf_fii),
                },
            },
            'etf_bdr': {
                'months_with_sales_count': len(etf_bdr_months),
                'months': etf_bdr_months,
                'year_summary': {
                    'total_taxable_gain': _money(eb_taxable),
                    'total_tax_due': _money(eb_tax_due),
                    'total_irrf': _money(eb_irrf),
                },
            },
            'position_at_year_end': position_at_year_end,
        }
