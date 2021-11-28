# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import os
import datetime
from dateutil.relativedelta import relativedelta

from settings import Settings

from .json import Json

L10n = Json('assets/L10n_ru.json')


def load_assets_file(file) -> str:
    with open(os.path.join(os.getcwd(), 'assets', file), 'r', encoding='utf8') as f:
        return f.read().strip()


def parse_placeholders(placeholders):
    for key, value in placeholders.items():
        if value is None:
            placeholders[key] = 'null'
        elif type(value) != str:
            placeholders[key] = str(value)

    return placeholders


def replace_placeholders(placeholders, html, plain) -> (str, str):
    for placeholder, placeholder_value in placeholders.items():
        html = html.replace(f'%{placeholder}%', str(placeholder_value))
        plain = plain.replace(f'%{placeholder}%', str(placeholder_value))

    return html, plain


def parse_header_feedback_id(message_id, invoice_id, service) -> str:
    header = L10n.get('smtp.header.feedback_id')

    header_feedback_id = header.format(
        message_id=message_id,
        invoice_id=invoice_id,
        service=service
    )

    return header_feedback_id


def get_gateways() -> list:
    return ['CASH', 'CREDIT', 'GIFT', 'CARD_ALFABANK', 'CARD_SBERBANK', 'SBP_ALFABANK', 'SBP_SBERBANK', 'QIWI', 'YOOMONEY', 'WEBMONEY_R', 'WEBMONEY_P', 'WEBMONEY_Z', 'WEBMONEY_E', 'PAYPAL']


def get_gateway(gateway: str):
    gateway = gateway.upper()

    if gateway not in get_gateways():
        return None

    return L10n.get(f'gateways.name.{gateway}', gateway)


def format_date(timestamp) -> str:
    dt = datetime.datetime.fromtimestamp(timestamp)

    date = dt.strftime(L10n.get('date_time')).split(' ')

    date[1] = L10n.get("months.{month}".format(month=date[1]))

    date = ' '.join(date)

    return date


def parse_name(client) -> str:
    first_name = client.getraw('first_name', '') or ''
    last_name = client.getraw('last_name', '') or ''

    return "{} {}".format(first_name, last_name).strip()


def get_first_day_of_month_dt(next_month=False):
    now = datetime.datetime.now()

    dt = datetime.datetime(day=1, month=now.month, year=now.year)
    if next_month:
        return dt + relativedelta(months=1)

    return dt
