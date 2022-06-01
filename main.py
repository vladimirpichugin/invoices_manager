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

			payer_gateways = payer.get('gateways') or gateways
			payer_currency = payer.get('currency') or currency

			prepaid = payer.get('prepaid') or False
			if payer_gateways[0] == 'GIFT':
				prepaid = True

			invoice = Invoice(Settings.INVOICE_TEMPLATE)

			invoice.update(Settings.INVOICE_TEMPLATE)

			invoice['_id'] = str(uuid.uuid4())
			invoice['id'] = invoice_id
			invoice['name'] = invoice_name
			invoice['status'] = 'UNPAID'
			invoice['currency'] = payer_currency
			invoice['gateways'] = payer_gateways
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
				item['name'] = item['name'].\
					replace('%month%', L10n.get("months.nom.{month}".format(month=dt.strftime('%B'))).title()).\
					replace('%year%', str(dt.strftime('%Y')))

			if prepaid:
				total, discount = 0, 0
				for item in invoice['items']:
					total += item.get('price', 0)
					discount += item.get('discount', 0)
				total -= discount

				transaction = {
						'gateway': payer_gateways[0],
						'timestamp': invoice['created'],
						'sum': total
				}
				invoice['transactions'] = [transaction]
				invoice['status'] = 'PAID'
				invoice['paid_timestamp'] = invoice['created']

			storage.save_invoice(invoice)


def invoice_notify():
	dt = datetime.datetime.now()
	dt_timestamp = int(dt.timestamp())
	invoices = storage.get_invoices({'status': 'UNPAID', '_version': Settings.INVOICE_VERSION})

	for invoice in invoices:
		if invoice.get('status') == 'PAID':
			continue

		created = datetime.datetime.fromtimestamp(invoice.get('created'))
		due = datetime.datetime.fromtimestamp(invoice.get('due'))

		message = None

		notify_inform = invoice.get('_notify_inform', {})

		if dt > due and 'notify_overdue' not in notify_inform:
			message = 'notify_overdue'
			notify_inform['notify_overdue'] = dt_timestamp
			invoice['status'] = 'OVERDUE'
		else:
			if 'notify' not in notify_inform:
				message = 'notify'
				notify_inform['notify'] = dt_timestamp
			else:
				diff = due.date() - created.date()

				if diff.days <= 3:
					continue

				due_diff = due.date() - dt.date()
				due_diff = due_diff.days

				if due_diff == 2 and ('notify_unpaid' not in notify_inform):
					message = 'notify_unpaid'
					notify_inform['notify_unpaid'] = dt_timestamp

				if due_diff == 1 and ('notify_unpaid_final' not in notify_inform):
					message = 'notify_unpaid_final'
					notify_inform['notify_unpaid_final'] = dt_timestamp

		if message:
			ok = send_with_delivery_report(invoice=invoice, message=message)
			if ok:
				try:
					invoice['_notify_inform'] = notify_inform
					invoice.changed = True
					storage.save_invoice(invoice)
				except:
					logger.error(f"Problems with saving invoice inform status", exc_info=True)


def invoice_receipt():
	invoices = storage.get_invoices({'status': 'PAID'})

	for invoice in invoices:
		notify_inform = invoice.get('_notify_inform', {})

		if 'paid' not in notify_inform:
			notify_inform['paid'] = int(datetime.datetime.now().timestamp())

			ok = send_with_delivery_report(invoice=invoice, message='receipt')
			if ok:
				try:
					invoice['_notify_inform'] = notify_inform
					invoice.changed = True
					storage.save_invoice(invoice)
				except:
					logger.error(f"Problems with saving invoice inform status", exc_info=True)


def invoice_notify_refunded():
	invoices = storage.get_invoices({'status': 'REFUNDED'})

	for invoice in invoices:
		notify_inform = invoice.get('_notify_inform', {})

		if 'refunded' not in notify_inform:
			notify_inform['refunded'] = int(datetime.datetime.now().timestamp())

			ok = send_with_delivery_report(invoice=invoice, message='notify_refund')
			if ok:
				try:
					invoice['_notify_inform'] = notify_inform
					invoice.changed = True
					storage.save_invoice(invoice)
				except:
					logger.error(f"Problems with saving invoice inform status", exc_info=True)


def invoice_notify_cancelled():
	invoices = storage.get_invoices({'status': 'CANCELLED'})

	for invoice in invoices:
		notify_inform = invoice.get('_notify_inform', {})

		if 'cancelled' not in notify_inform:
			notify_inform['cancelled'] = int(datetime.datetime.now().timestamp())

			ok = send_with_delivery_report(invoice=invoice, message='notify_cancel')
			if ok:
				try:
					invoice['_notify_inform'] = notify_inform
					invoice.changed = True
					storage.save_invoice(invoice)
				except:
					logger.error(f"Problems with saving invoice inform status", exc_info=True)


def send_with_delivery_report(invoice, message) -> bool:
	try:
		mail_send, delivery_report = send_message(invoice=invoice, message=message)
		logger.debug(f"Message {message} was sent successfully, delivery report: {delivery_report} SMTP response: {mail_send}")
	except:
		logger.error(f"Can't send message {message}, problems with SMTP client.", exc_info=True)
		return False

	try:
		storage.save_report(delivery_report)
	except:
		logger.error(f"Problems with saving notify delivery-report", exc_info=True)

	return True


def send_message(invoice, message, service='email'):
	if service != 'email':
		return Warning('Unknown service')

	message_key = message.split('_')[0]

	if message_key == 'receipt':
		from_addr = Settings.SMTP_RECEIPT_USER
		from_pass = Settings.SMTP_RECEIPT_PASS
		header_service = Settings.SMTP_RECEIPT_HEADER_SERVICE
	elif message_key == 'notify':
		from_addr = Settings.SMTP_ALERT_USER
		from_pass = Settings.SMTP_ALERT_PASS
		header_service = Settings.SMTP_ALERT_HEADER_SERVICE
	else:
		raise Warning(f'Unknown message key {message_key}') from None

	message_id = str(uuid.uuid4())  # Create message ID.
	invoice_id = invoice.get('_id')

	payee = storage.get_client(invoice.get('payee').get('id'))
	payer = storage.get_client(invoice.get('payer').get('id'))

	to_addr, to_name, subject, html, plain = InvoiceMail.make(
		message=message, message_id=message_id, invoice=invoice, payee=payee, payer=payer
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
