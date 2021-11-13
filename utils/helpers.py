# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import os
import pathlib
import logging

from settings import Settings


def init_logger():
    logger = logging.Logger('invoices_manager', level=logging.DEBUG if Settings.DEBUG else logging.INFO)

    file_handler = get_logger_file_handler()
    file_handler.setLevel(logging.DEBUG)

    stream_handler = get_logger_stream_handler()
    stream_handler.setLevel(level=logging.DEBUG if Settings.DEBUG else logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


def get_logger_formatter(f=u'%(pathname)s:%(lineno)d\n[%(asctime)s] %(levelname)-5s %(threadName)-15s: %(message)s') -> logging.Formatter:
    return logging.Formatter(
        fmt=f,
        datefmt='%d.%m.%y %H:%M:%S')


def get_logger_file_handler() -> logging.FileHandler:
    pathlib.Path('logs').mkdir(exist_ok=True)
    file_handler = logging.FileHandler(os.path.join('logs', 'log.txt'), encoding='utf-8')

    file_handler.setFormatter(get_logger_formatter())

    return file_handler


def get_logger_stream_handler() -> logging.StreamHandler:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(get_logger_formatter(u'[%(asctime)s] %(levelname)-5s %(threadName)-15s: %(message)s'))

    return stream_handler


def get_currency() -> dict:
    return {'RUB': '₽', 'EUR': '€', 'USD': '$'}


def get_months() -> dict:
    return {
      'January': 'января', 'February': 'февраля', 'March': 'марта',
      'April': 'апреля', 'May': 'мая', 'June': 'июня', 'July': 'июля',
      'August': 'августа', 'September': 'сентября', 'October': 'октября',
      'November': 'ноября', 'December': 'декабря'
    }


def load_assets_file(file) -> str:
    with open(os.path.join(os.getcwd(), 'assets', file), 'r', encoding='utf8') as f:
        return f.read().strip()
