# coding: utf-8
from __future__ import unicode_literals

from decimal import Decimal

# import mock
import pytest
from prices import Amount, Price
from django_prices_openexchangerates import CurrencyConversion
from django_prices_openexchangerates.models import (
    ConversionRate, get_rates, CACHE_KEY, CACHE_TIME)
from django_prices_openexchangerates.templatetags import (
    prices_multicurrency as rates_prices,
    prices_multicurrency_i18n as rates_prices_i18n)
from django_prices_openexchangerates import (
    CurrencyConversion, exchange_currency)


RATES = {
    'EUR': Decimal(2),
    'GBP': Decimal(4),
    'BTC': Decimal(10)}


@pytest.fixture
def base_currency(db, settings):
    settings.OPENEXCHANGERATES_BASE_CURRENCY = 'BTC'


@pytest.fixture(autouse=True)
def conversion_rates(db):
    rates = []
    for currency, value in RATES.items():
        rate = ConversionRate.objects.create(
            to_currency=currency, rate=RATES[currency])
        rates.append(rate)
    return rates


def test_the_same_currency_uses_no_conversion():
    amount = Amount(10, currency='USD')
    converted = exchange_currency(amount, 'USD')
    assert converted == amount


def test_base_currency_to_another():
    converted = exchange_currency(Amount(10, currency='USD'), 'EUR')
    assert converted.currency == 'EUR'
    assert converted is not None


def test_convert_another_to_base_currency():
    base_amount = Amount(10, currency='EUR')
    converted_amount = exchange_currency(base_amount, 'USD')
    assert converted_amount.currency == 'USD'


def test_convert_two_non_base_currencies():
    base_amount = Amount(10, currency='EUR')
    converted_amount = exchange_currency(base_amount, 'GBP')
    assert converted_amount.currency == 'GBP'


def test_convert_price_uses_passed_dict():
    base_amount = Amount(10, currency='USD')

    def custom_get_rate(currency):
        data = {'GBP': Decimal(5)}
        return data[currency]

    converted_amount = exchange_currency(
        base_amount, 'GBP', get_rate=custom_get_rate)
    # self.assertFalse(mock_qs.called)
    assert converted_amount.currency == 'GBP'


def test_two_base_currencies_the_same_currency_uses_no_conversion():
    amount = Amount(10, currency='USD')
    converted = exchange_currency(amount, 'USD')
    assert converted == amount


def test_two_base_currencies_base_currency_to_another():
    converted = exchange_currency(Amount(10, currency='USD'), 'EUR')
    assert converted.currency == 'EUR'
    assert converted is not None


def test_two_base_currencies_convert_another_to_base_currency():
    base_amount = Amount(10, currency='EUR')
    converted_amount = exchange_currency(base_amount, 'USD')
    assert converted_amount.currency == 'USD'


def test_two_base_currencies_convert_two_non_base_currencies():
    base_amount = Amount(10, currency='EUR')
    converted_amount = exchange_currency(base_amount, 'GBP')
    assert converted_amount.currency == 'GBP'


def test_two_base_currencies_convert_price_uses_passed_dict():
    base_amount = Amount(10, currency='USD')

    def custom_get_rate(currency):
        data = {'GBP': Decimal(5)}
        return data[currency]

    converted_amount = exchange_currency(
        base_amount, 'GBP', get_rate=custom_get_rate)
    assert converted_amount.currency == 'GBP'


def test_two_base_currencies_convert_price_uses_db_when_dict_not_passed():
    base_amount = Amount(10, currency='USD')

    converted_amount = exchange_currency(
        base_amount, 'GBP')
    assert converted_amount.currency == 'GBP'


def test_repr():
    currency_base = 'USD'
    to_currency = 'EUR'
    modifier = CurrencyConversion(
        base_currency=currency_base, to_currency=to_currency,
        rate=Decimal('0.5'))
    expected = "CurrencyConversion(%r, %r, rate=Decimal('0.5'))" % (
        currency_base, to_currency)
    assert repr(modifier) == expected


def test_template_filter_amount_in_currency():
    amount = Amount(Decimal('1.23456789'), currency='USD')
    result = rates_prices.in_currency(amount=amount, currency='EUR')
    assert result == Amount(Decimal('2.47'), currency='EUR')


def test_template_filter_amount_in_currency_amount():
    amount = Amount(Decimal('1.23456789'), currency='USD')
    result = rates_prices.in_currency(amount=amount, currency='EUR')
    result = rates_prices.amount(result)
    assert result == '2.47 <span class="currency">EUR</span>'


def test_template_filter_amount_i18n_in_currency():
    amount = Amount(Decimal('1.23456789'), currency='USD')
    result = rates_prices_i18n.in_currency(amount=amount, currency='EUR')
    assert result == Amount(Decimal('2.47'), currency='EUR')


def test_template_filter_amount_i18n_in_currency_amount():
    amount = Amount(Decimal('1.23456789'), currency='USD')
    result = rates_prices_i18n.in_currency(amount, 'EUR')
    result = rates_prices_i18n.amount(result)
    assert result == '€2.47'


def test_get_rates_caches_results(conversion_rates):
    result = get_rates(qs=conversion_rates)
    assert all(currency in result.keys() for currency in ['BTC', 'GBP', 'EUR'])


def test_get_rates_force_update_cache(conversion_rates):
    expected_cache_content = {
        rate.to_currency: rate for rate in conversion_rates}
    rates = get_rates(qs=conversion_rates, force_refresh=True)
    assert rates == expected_cache_content


def test_currency_conversion_apply_for_amount():
    conversion = CurrencyConversion(
        base_currency='USD', to_currency='EUR', rate=2)
    amount = Amount(10, 'USD')
    amount_converted = conversion.apply(amount)
    assert amount_converted.currency == 'EUR'
    assert amount_converted.value == 20


def test_currency_conversion_apply_for_price():
    conversion = CurrencyConversion(
        base_currency='USD', to_currency='EUR', rate=2)
    price = Price(Amount(10, 'USD'), Amount(12, 'USD'))
    price_converted = conversion.apply(price)
    assert price_converted.net.currency == 'EUR'
    assert price_converted.net.value == 20
    assert price_converted.gross.currency == 'EUR'
    assert price_converted.gross.value == 24
