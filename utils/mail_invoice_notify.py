# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import uuid
import datetime
from itertools import zip_longest

from .helpers import get_currency, get_months, load_assets_file, init_logger, parse_placeholders, replace_placeholders
from .json import Json
from .mail import Mail
from .data import MessageDeliveryReport

from settings import Settings

logger = init_logger()
L10n = Json('assets/L10n_ru.json')


class MailInvoiceNotify:
    @staticmethod
    def make(invoice, payee, payer, from_addr, from_name):
        # (<!--(?P<open_tag>.+?)-->)(?P<payload>.+?)(<!--(?P<close_tag>.+?)-->)
        plain = load_assets_file('invoice_notify_ru.txt')
        html = load_assets_file('invoice_notify_ru.html')
        subject = L10n.get('invoice.notify.mail.subject')
        preview = L10n.get('invoice.notify.mail.preview')
        text = L10n.get('invoice.notify.mail.text')
        placeholders = dict(zip_longest(Settings.PLACEHOLDERS.get('INVOICE_MAIL_TEMPLATE'), []))
        placeholders['text'] = text

        header_service = Settings.SMTP_ALERT_HEADER_SERVICE

        invoice_id = invoice.get('id')
        invoice_name = invoice.get('name')
        invoice_currency = invoice.get('currency', 'RUB')

        payer_id = invoice.get('payer').get('id')
        payee_id = invoice.get('payee').get('id')

        payee_name = f"{payee.getraw('first_name', payee_id) + ' ' + payee.getraw('last_name', '')}".strip()

        # to_addr = payer.getraw('email')
        to_addr = 'vladimir@pichug.in'  # todo: remove debug

        to_name = payer_name = f"{payer.getraw('first_name', payer_id) + ' ' + payer.getraw('last_name', '')}".strip()
        first_name = payer.getraw('first_name', payer_id)

        message_id = uuid.uuid4()

        header_feedback_id = Settings.SMTP_HEADER_FEEDBACK_ID.format(
            message_id=message_id.hex,
            invoice_id=invoice_id,
            service=header_service
        )

        currency_symbol = get_currency().get(invoice_currency)

        placeholders['payer'] = payer_name
        placeholders['payee'] = payee_name

        placeholders['first_name'] = first_name
        placeholders['email'] = to_addr

        placeholders['currency_l'] = '' if invoice_currency == 'RUB' else f' {currency_symbol}'
        placeholders['currency_r'] = f' {currency_symbol}' if invoice_currency == 'RUB' else ''

        placeholders['message_id'] = str(message_id)
        placeholders['preview'] = preview.replace('%id%', invoice_id).replace('%name%', invoice_name)
        placeholders['year'] = datetime.datetime.now().year

        for key, value in dict(invoice).items():
            if key in Settings.PLACEHOLDERS.get('INVOICE_OBJECT'):
                placeholders[key] = str(value)

        for placeholder, keys in {'date_created': ['created'], 'date_paid': ['paid_timestamp', 'created'], 'date_due': ['due', 'created']}.items():
            for key in keys:
                if invoice.get(key) and not placeholders[placeholder]:
                    dt = datetime.datetime.fromtimestamp(invoice[key])

                    date = dt.strftime('%d %B %Y в %H:%M:%S').split(' ')
                    date[1] = get_months()[date[1]]
                    date = ' '.join(date)

                    placeholders[placeholder] = date

        placeholders['total'] = 0
        if type(invoice.get('items')) == list:
            for item in invoice['items']:
                if type(item) != dict:
                    continue

                placeholders['total'] += item.get('price', 0)

        for _ in ['total']:
            if placeholders[_]:
                placeholders[_] = f'{float(placeholders[_]):,.2f}'
            else:
                placeholders[_] = 0.0

        placeholders = parse_placeholders(placeholders)
        html, plain = replace_placeholders(placeholders, html, plain)

        subject = subject.replace('%id%', invoice_id).replace('%name%', invoice_name)

        headers = {
            'Feedback-ID': header_feedback_id,
            'X-Pichugin-Service': header_service
        }

        multipart = Mail.create_multipart(from_addr, from_name, to_addr, to_name, subject, html, plain, headers)

        message = MessageDeliveryReport.create({
            '_id': message_id,
            'type': 'email',
            'notify': header_service,
            'message': {
                'payer_id': payer_id,
                'invoice_id': invoice_id,
                'to_addr': to_addr,
                'to_name': to_name,
                'from_addr': from_addr,
                'from_name': from_name,
                'subject': subject,
                'feedback_id': header_feedback_id
            },
            'timestamp': int(datetime.datetime.now().timestamp()),
            '_v': 1
        })

        return message, to_addr, multipart.as_string()
