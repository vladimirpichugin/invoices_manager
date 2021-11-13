# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import uuid
import datetime
from itertools import zip_longest

from .helpers import get_currency, get_months, load_assets_file, init_logger
from .mail import Mail
from .data import MessageDeliveryReport

from settings import Settings

logger = init_logger()

plain = load_assets_file('invoice_receipt_ru.txt')
html = load_assets_file('invoice_receipt_ru.html')  # (<!--(?P<open_tag>.+?)-->)(?P<payload>.+?)(<!--(?P<close_tag>.+?)-->)


class MailInvoiceReceipt:
    @staticmethod
    def paid(invoice, payee, payer):
        global plain, html

        from_addr = Settings.SMTP_RECEIPT_USER
        from_name = Settings.SMTP_RECEIPT_NAME

        invoice_id = invoice.get('id')
        invoice_name = invoice.get('name')
        invoice_currency = invoice.get('currency', 'RUB')

        payer_id = invoice.get('payer').get('id')
        payee_id = invoice.get('payee').get('id')

        payee_name = f"{payee.getraw('first_name', payee_id) + ' ' + payee.getraw('last_name', '')}".strip()

        to_addr = payer.getraw('email')

        to_name = payer_name = f"{payer.getraw('first_name', payer_id) + ' ' + payer.getraw('last_name', '')}".strip()
        first_name = payer.getraw('first_name', payer_id)

        subject = 'Счёт № %id% оплачен: %name%'
        sub_subject = 'Спешим сообщить о получении платежа.'

        subject = subject.replace('%id%', invoice_id).replace('%name%', invoice_name)

        message_id = uuid.uuid4()

        header_feedback_id = Settings.SMTP_HEADER_FEEDBACK_ID.format(
            message_id=message_id.hex,
            invoice_id=invoice_id,
            service=Settings.SMTP_RECEIPT_HEADER_SERVICE
        )

        placeholders = dict(zip_longest(Settings.PLACEHOLDERS.get('INVOICE_MAIL_TEMPLATE'), []))

        currency_symbol = get_currency().get(invoice_currency)

        placeholders['payer'] = payer_name
        placeholders['payee'] = payee_name

        placeholders['first_name'] = first_name
        placeholders['email'] = to_addr

        placeholders['currency_l'] = '' if invoice_currency == 'RUB' else f' {currency_symbol}'
        placeholders['currency_r'] = f' {currency_symbol}' if invoice_currency == 'RUB' else ''

        placeholders['message_id'] = str(message_id)
        placeholders['sub_subject'] = sub_subject
        placeholders['year'] = datetime.datetime.now().year

        for key, value in dict(invoice).items():
            if key in Settings.PLACEHOLDERS.get('INVOICE_OBJECT'):
                placeholders[key] = str(value)

        for placeholder, keys in {'date_created': ['created'], 'date_paid': ['paid_timestamp', 'created']}.items():
            for key in keys:
                if invoice.get(key) and not placeholders[placeholder]:
                    dt = datetime.datetime.fromtimestamp(invoice[key])

                    date = dt.strftime('%d %B %Y в %H:%M:%S').split(' ')
                    date[1] = get_months()[date[1]]
                    date = ' '.join(date)

                    placeholders[placeholder] = date

        if type(invoice.get('gateways')) == list:
            if len(invoice['gateways']) > 0:
                placeholders['gateway'] = Settings.GATEWAYS.get(invoice['gateways'][0], invoice['gateways'][0])

        placeholders['total'] = 0
        placeholders['discount'] = 0
        if type(invoice.get('items')) == list:
            for item in invoice['items']:
                if type(item) != dict:
                    continue

                placeholders['total'] += item.get('price', 0)
                placeholders['discount'] += item.get('discount', 0)

        placeholders['paid'] = 0
        if type(invoice.get('transactions')) == list:
            for transaction in invoice['transactions']:
                if type(transaction) != dict:
                    continue

                placeholders['paid'] += transaction.get('sum', 0)

                if 'gateway' in transaction:
                    placeholders['gateway'] = Settings.GATEWAYS.get(transaction['gateway'], transaction['gateway'])

        for _ in ['total', 'discount', 'credit', 'commission', 'paid']:
            if placeholders[_]:
                placeholders[_] = f'{float(placeholders[_]):.2f}'
            else:
                placeholders[_] = 0.0

        for key, value in placeholders.items():
            if value is None:
                placeholders[key] = 'null'
            elif type(value) != str:
                placeholders[key] = str(value)

        for placeholder, placeholder_value in placeholders.items():
            html = html.replace(f'%{placeholder}%', str(placeholder_value))
            plain = plain.replace(f'%{placeholder}%', str(placeholder_value))

        headers = {
            'Feedback-ID': header_feedback_id,
            'X-Pichugin-Notify': Settings.SMTP_RECEIPT_HEADER_SERVICE
        }

        multipart = Mail.create_multipart(from_addr, from_name, to_addr, to_name, subject, html, plain, headers)

        message = MessageDeliveryReport.create({
            '_id': message_id,
            '_v': 1,
            'type': 'email',
            'notify': Settings.SMTP_ALERT_HEADER_SERVICE,
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
            'timestamp': int(datetime.datetime.now().timestamp())
        })

        return message, from_addr, to_addr, multipart.as_string()
