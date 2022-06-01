# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import time
import threading
import schedule

import main


if __name__ == "__main__":
    console_thread = threading.Thread(target=main.console)
    console_thread.setName('ConsoleThread')
    console_thread.daemon = True
    console_thread.start()

    schedule.every(5).minutes.do(main.run_threaded, name='AutoInvoice', func=main.auto_invoice).run()
    schedule.every(5).minutes.do(main.run_threaded, name='NotifyPaid', func=main.invoice_notify).run()
    schedule.every(5).minutes.do(main.run_threaded, name='NotifyCancelled', func=main.invoice_notify_cancelled).run()
    schedule.every(5).minutes.do(main.run_threaded, name='NotifyRefunded', func=main.invoice_notify_refunded).run()
    schedule.every(5).minutes.do(main.run_threaded, name='Receipt', func=main.invoice_receipt).run()

    # Поддерживать работу основного потока, пока поток демона жив.
    while True:
        try:
            if not console_thread.is_alive():
                main.logger.error("ConsoleThread is not alive, shutting down..")
                break

            schedule.run_pending()

            time.sleep(1)
        except KeyboardInterrupt:
            main.logger.info("Shutting down..")
            break
