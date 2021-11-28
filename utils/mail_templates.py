# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import datetime
from itertools import zip_longest

from .helpers import L10n, load_assets_file, parse_placeholders, replace_placeholders, get_gateway, format_date, parse_name

from settings import Settings


class InvoiceMail:
    @staticmethod
    def make(message_key, message_id, invoice, payee, payer):
        # (<!--(?P<open_tag>.+?)-->)(?P<payload>.+?)(<!--(?P<close_tag>.+?)-->)
        plain = load_assets_file('invoice_{}_ru.txt'.format(message_key))
        html = load_assets_file('invoice_{}_ru.html'.format(message_key))
        subject = L10n.get('invoice.{}.mail.subject'.format(message_key))
        preview = L10n.get('invoice.{}.mail.preview'.format(message_key))
        text = L10n.get('invoice.{}.mail.text'.format(message_key))
        placeholders = dict(zip_longest(Settings.PLACEHOLDERS.get(message_key.upper()), []))

        invoice_id = invoice.get('id')
        invoice_name = invoice.get('name')

        invoice_currency = invoice.get('currency', 'RUB')
        if invoice_currency not in ['RUB', 'EUR', 'USD']:
            invoice_currency = 'RUB'

        # to_addr = payer.getraw('email')
        to_addr = 'vladimir@pichug.in'  # todo: remove debug
        to_name = payer_name = parse_name(payer)
        first_name = payer.getraw('first_name', to_name)
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
        placeholders['text'] = text
        placeholders['year'] = datetime.datetime.now().year

        for key, value in dict(invoice).items():
            if key in Settings.PLACEHOLDERS.get('INVOICE_OBJECT'):
                placeholders[key] = str(value)

        for placeholder, keys in {'date_created': ['created'], 'date_paid': ['paid_timestamp', 'created'], 'date_due': ['due', 'created']}.items():
            for key in keys:
                if invoice.get(key) and not placeholders[placeholder]:
                    date = format_date(invoice[key])
                    placeholders[placeholder] = date

        if len(invoice['gateways']) > 0:
            placeholders['gateway'] = get_gateway(gateways[0])
        else:
            placeholders['gateway'] = '-'

        placeholders['total'] = 0
        placeholders['discount'] = 0
        for item in items:
            if type(item) != dict:
                continue

            placeholders['total'] += item.get('price', 0)
            placeholders['discount'] += item.get('discount', 0)

        placeholders['paid'] = 0
        for transaction in transactions:
            if type(transaction) != dict:
                continue

            placeholders['paid'] += transaction.get('sum', 0)

            gateway = transaction.get('gateway')
            if gateway:
                placeholders['gateway'] = get_gateway(gateway)

        for key in ['total', 'discount', 'commission', 'paid']:
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
