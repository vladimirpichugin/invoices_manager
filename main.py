# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import threading
import schedule
import uuid

from utils import *

logger = init_logger()

logger.info("Initializing..")

try:
	logger.info("Initializing storage..")
	storage = Storage()
	logger.debug(f"MongoDB Server version: {storage.mongo_client.server_info()['version']}")
except Exception as e:
	logger.error('Storage crashed', exc_info=True)
	raise RuntimeError from e


def run_threaded(name, func):
	job_thread = threading.Thread(target=func)
	job_thread.setName(f'{name}Thread')
	job_thread.start()


def auto_invoice(pre_next_month=False):
	auto_invoices = storage.get_auto_invoices()
	dt = get_first_day_of_month_dt(pre_next_month)
	payee_name = 'Владимир Пичугин'

	for auto_invoice in auto_invoices:
		if auto_invoice.get('disabled'):
			continue

		a_i_id = auto_invoice.get('_id')
		invoice_name = auto_invoice.get('name', a_i_id)

		invoice_id = '{id}_{month}_{year}'.format(
			id=a_i_id,
			month=str(dt.month),
			year=str(dt.strftime('%y'))
		)

		items = auto_invoice.get('items', [])
		gateways = auto_invoice.get('gateways', [])

		payee_id = auto_invoice.get('payee', {}).get('id')
		payers = auto_invoice.get('payers', [])

		currency = auto_invoice.get('currency', 'RUB')
		due = int(auto_invoice.get('due', 604800))

		for payer in payers:
			payer_id = payer.get('id')
			payer_name = parse_name(storage.get_client(payer_id))

			find_invoice = storage.invoices.find_one({'id': invoice_id, 'payer.id': payer_id})
			if find_invoice:
				continue

			prepaid = payer.get('prepaid', False)

			invoice = Invoice(Settings.INVOICE_TEMPLATE)

			invoice.update(Settings.INVOICE_TEMPLATE)

			invoice['_id'] = str(uuid.uuid4())
			invoice['id'] = invoice_id
			invoice['name'] = invoice_name
			invoice['status'] = 'UNPAID'
			invoice['currency'] = currency
			invoice['gateways'] = payer.get('gateways', gateways)
			invoice['items'] = payer.get('items', items)
			invoice['payer'] = {'id': payer_id, 'payer': payer_name}
			invoice['payee'] = {'id': payee_id, 'payee': payee_name}
			invoice['created'] = int(datetime.datetime.now().timestamp())
			invoice['due'] = int(dt.timestamp()+due)

			invoice['name'] = invoice['name'].replace(
				'%month%',
				L10n.get("months.nom.{month}".format(month=dt.strftime('%B'))).title()
			).replace(
				'%year%',
				str(dt.strftime('%Y'))
			)

			for item in invoice['items']:
				item['name'] = item['name'].replace(
					'%month%',
					L10n.get("months.nom.{month}".format(month=dt.strftime('%B'))).title()
				).replace(
					'%year%',
					str(dt.strftime('%Y'))
				)

			if prepaid:
				total, discount = 0, 0
				for item in invoice['items']:
					total += item.get('price', 0)
					discount += item.get('discount', 0)
				total -= discount

				invoice['paid_timestamp'] = invoice['created']
				invoice['status'] = 'PAID'
				invoice['transactions'] = [{
						'gateway': 'CREDIT',
						'timestamp': invoice['created'],
						'sum': total
				}]

			storage.save_invoice(invoice)


def invoice_notify():
	invoices = storage.get_invoices()

	for invoice in invoices:
		if invoice.get('status') != 'UNPAID':
			continue

		if not invoice.get('_informed_notify'):
			message = "notify"
			invoice_tag = '_informed_notify'
		else:
			continue
			#if not invoice.get('_informed_notify_unpaid'):
			#	message = "invoice.notify.mail.unpaid"
			#   invoice_tag =
			#elif not invoice.get('_informed_notify_unpaid_last'):
			#	message = "invoice.notify.mail.unpaid.last"
		    #   invoice_tag =

		ok = False
		try:
			mail_send, delivery_report = send_message(invoice=invoice, message=message)
			ok = True
			logger.debug(f"Notify was sent successfully, delivery report: {delivery_report} SMTP response: {mail_send}")
		except Exception:
			logger.error("Can't send notify, problems with SMTP client", exc_info=True)

		if ok:
			try:
				storage.save_report(delivery_report)
			except Exception:
				logger.error(f"Problems with saving notify delivery-report", exc_info=True)

			try:
				invoice[invoice_tag] = True
				storage.save_invoice(invoice)
			except Exception:
				logger.error(f"Problems with saving notify informed status", exc_info=True)


def invoice_receipt():
	invoices = storage.get_invoices()

	for invoice in invoices:
		if invoice.get('status') != 'PAID':
			continue

		paid_timestamp = int(invoice.get('paid_timestamp') or 0)

		if not paid_timestamp:
			continue

		if invoice.get('_informed_receipt'):
			continue

		paid_dt = datetime.datetime.fromtimestamp(paid_timestamp)

		time_diff = datetime.datetime.today() - paid_dt

		if time_diff.total_seconds() < 28800:
			ok = False
			try:
				mail_send, delivery_report = send_message(invoice=invoice, message='receipt')
				ok = True
				logger.debug(f"Receipt was sent successfully, delivery report: {delivery_report} SMTP response: {mail_send}")
			except Exception:
				logger.error("Can't send receipt, problems with SMTP client", exc_info=True)

			if ok:
				try:
					storage.save_report(delivery_report)
				except Exception:
					logger.error(f"Problems with saving receipt delivery-report", exc_info=True)

				try:
					invoice['_informed_receipt'] = True
					storage.save_invoice(invoice)
				except Exception:
					logger.error(f"Problems with saving receipt informed status", exc_info=True)


def send_message(invoice, message, service='email'):
	if service != 'email':
		return Warning('Unknown service')

	if message == 'receipt':
		from_addr = Settings.SMTP_RECEIPT_USER
		from_pass = Settings.SMTP_RECEIPT_PASS
		header_service = Settings.SMTP_RECEIPT_HEADER_SERVICE
	elif message == 'notify':
		from_addr = Settings.SMTP_ALERT_USER
		from_pass = Settings.SMTP_ALERT_PASS
		header_service = Settings.SMTP_ALERT_HEADER_SERVICE
	else:
		raise Warning('Unknown message type')

	message_id = str(uuid.uuid4())
	invoice_id = invoice.get('_id')

	payee = storage.get_client(invoice.get('payee').get('id'))
	payer = storage.get_client(invoice.get('payer').get('id'))

	to_addr, to_name, subject, html, plain = InvoiceMail.make(
		message_id=message_id, invoice=invoice, payee=payee, payer=payer, message_key=message
	)

	logger.debug(f"[message id:{message_id}] Preparing mail-{header_service} ({invoice_id})")

	headers = Mail.create_headers(message_id=message_id, invoice_id=invoice_id, service=header_service)

	multipart = Mail.create_multipart(from_addr, Settings.SMTP_NAME, to_addr, to_name, subject, html, plain, headers)
	msg = multipart.as_string()

	delivery_report = Mail.create_delivery_report(invoice_id, message_id, from_addr, to_addr, to_name, subject, headers)

	logger.info(f"[message id:{message_id}] Sending mail-{header_service} to <{to_addr}> ({invoice_id})`")

	response = Mail.send(
		user=from_addr,
		password=from_pass,
		to_addr=to_addr,
		msg=msg
	)

	logger.info(f"[message id:{message_id}] Sending mail-{header_service} to <{to_addr}> ({invoice_id})\nResponse: {response}")

	return response, delivery_report


def console():
	while True:
		try:
			cmd, arg = None, None

			try:
				args = input().split(' ')
				if len(args) > 0:
					cmd = args[0]
				if len(args) > 1:
					arg = args[1]
			except EOFError:
				continue

			if cmd == "invoice":
				logger.info("Find invoice by id {}".format(arg))
				invoice = storage.get_invoice(arg)

				for key, value in invoice.items():
					logger.info(f"{key}: {value}")
			elif cmd == "client":
				logger.info("Find client by id {}".format(arg))
				client = storage.get_client(arg)

				for key, value in client.items():
					logger.info(f"{key}: {value}")
			elif cmd == "tasks":
				if schedule.get_jobs():
					for job in schedule.get_jobs():
						logger.info(f'Task: {job}')
						logger.info(f'Next run: {job.next_run}')
				else:
					logger.info('No tasks.')
			elif cmd == "ai":
				pre_next_month = True if arg else False
				logger.info(f'pre_next_month: {pre_next_month}')
				auto_invoice(pre_next_month=pre_next_month)
			elif cmd == "stop":
				break
			else:
				logger.info("Command not found")
		except Exception:
			logger.error("Exception in console", exc_info=True)
