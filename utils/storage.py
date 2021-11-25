# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import pymongo
from .data import SDict, Invoice, Client, MessageDeliveryReport
from .helpers import init_logger

from settings import Settings

logger = init_logger()


class Storage:
    def __init__(self):
        self.mongo_client = pymongo.MongoClient(Settings.MONGO, authSource='admin')
        self.db = self.mongo_client.get_database(Settings.MONGO_DATABASE)
        self.clients = self.db.get_collection(Settings.MONGO_C_CLIENTS)
        self.invoices = self.db.get_collection(Settings.MONGO_C_INVOICES)
        self.messages = self.db.get_collection(Settings.MONGO_C_MESSAGES)

    def get_client(self, client_id: str):
        data = self.get_data(self.clients, client_id)

        if not data:
            return None

        client = Client.create(data)

        return client

    def get_invoice(self, invoice_id: str):
        data = self.get_data(self.invoices, invoice_id)

        if not data:
            return None

        invoice = Invoice(data)

        return invoice

    def get_invoices(self):
        data = self.invoices.find({})

        invoices = []
        for invoice in data:
            invoices.append(Invoice(invoice))

        return invoices

    def save_invoice(self, invoice: Invoice) -> bool:
        if not invoice.changed:
            logger.debug(f'Invoice <{invoice.id}> already saved, data not changed.')
            return True

        save = self.save_data(self.invoices, invoice.id, invoice)

        if save:
            logger.debug(f'Invoice <{invoice.id}> saved, result: {save}')
            return True

        logger.error(f'Invoice <{invoice.id}> not saved, result: {save}')

        return False

    def save_report(self, report: MessageDeliveryReport):
        save = self.save_data(self.messages, report.id, report)

        if save:
            logger.debug(f'Report <{report.id}> saved, result: {save}')
            return True

        logger.error(f'Report <{report.id}> not saved, result: {save}')

        return False

    @staticmethod
    def get_data(c: pymongo.collection.Collection, value, name="_id"):
        data = c.find_one({name: value})

        if data:
            return SDict(data)

        return None

    @staticmethod
    def save_data(c: pymongo.collection.Collection, value, data: SDict, name="_id"):
        if c.find_one({name: value}):
            return c.update_one({name: value}, {"$set": data})
        else:
            return c.insert_one(data)
