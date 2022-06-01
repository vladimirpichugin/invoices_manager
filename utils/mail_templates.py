# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import datetime
from itertools import zip_longest

from .helpers import L10n, load_assets_file, parse_placeholders, replace_placeholders, get_gateway, format_date, parse_name

from settings import Settings


class InvoiceMail:
    @staticmethod
    def make(message, message_id, invoice, payee, payer):
        message = message.lower()
        message_key = message.split('_')[0]

        plain = load_assets_file('invoice_{}_ru.txt'.format(message))
        html = load_assets_file('invoice_{}_ru.html'.format(message))
        subject = L10n.get('{}.subject'.format(message))
        preview = L10n.get('{}.preview'.format(message))
        placeholders = dict(zip_longest(Settings.PLACEHOLDERS.get(message_key.upper()), []))

        invoice_id = invoice.get('id')
        invoice_name = invoice.get('name', invoice_id)

        invoice_currency = invoice.get('currency') if invoice.get('currency') in Settings.CURRENCY else Settings.DEFAULT_CURRENCY

        to_addr = payer.getraw('email')
        to_name = payer_name = parse_name(payer)
        first_name = payer.getraw('first_name') or to_name
        payee_name = parse_name(payee)

        transactions = invoice.get('transactions') if type(invoice.get('transactions')) == list else []
        gateways = invoice.get('gateways') if type(invoice.get('gateways')) == list else []
        items = invoice.get('items') if type(invoice.get('items')) == list else []

        preview = preview.replace('%id%', invoice_id).replace('%name%', invoice_name)
        subject = subject.replace('%id%', invoice_id).replace('%name%', invoice_name)

        placeholders['email'] = to_addr
        placeholders['message_id'] = str(message_id)
        placeholders['payer'] = payer_name
        placeholders['first_name'] = first_name
        placeholders['payee'] = payee_name
        placeholders['preview'] = preview
        placeholders['year'] = datetime.datetime.now().year

        for key, value in dict(invoice).items():
            if key in Settings.PLACEHOLDERS.get('INVOICE_OBJECT'):
                placeholders[key] = str(value)

        for placeholder, keys in {'date_created': ['created'], 'date_paid': ['paid_timestamp', 'created'], 'date_due': ['due', 'created']}.items():
            for key in keys:
                if invoice.get(key) and not placeholders[placeholder]:
                    date = format_date(invoice[key])
                    placeholders[placeholder] = date

        placeholders['gateway'] = get_gateway(gateways[0]) if len(invoice['gateways']) > 0 else '-'

        placeholders['price'] = 0
        placeholders['discount'] = 0
        for item in items:
            if type(item) != dict:
                continue

            for item_key in ['price', 'discount']:
                item_value = item.get(item_key)

                if not item_value or type(item_value) not in [int, float]:
                    item_value = 0.0

                placeholders[item_key] += float(item_value)

        placeholders['paid'] = 0
        for transaction in transactions:
            if type(transaction) != dict:
                continue

            placeholders['paid'] += transaction.get('sum', 0)

            gateway = transaction.get('gateway')
            if gateway:
                placeholders['gateway'] = get_gateway(gateway)

        for key in ['price', 'discount', 'paid']:
            try:
                if placeholders[key]:
                    placeholders[key] = f'{float(placeholders[key]):,.2f}'
                else:
                    placeholders[key] = 0.0
            except KeyError:
                placeholders[key] = 0.0

            placeholders[key] = L10n.get('currency.{currency}'.format(currency=invoice_currency)).format(value=placeholders[key])

        placeholders = parse_placeholders(placeholders)
        html, plain = replace_placeholders(placeholders, html, plain)

        return to_addr, to_name, subject, html, plain
