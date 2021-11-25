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

    #schedule.every(1).hour.do(main.run_threaded, name='AutoInvoices', func=main.auto_invoice).run()
    #schedule.every(10).minutes.do(main.run_threaded, name='Notify', func=main.invoice_notify).run()
    schedule.every().day.at('10:00').do(main.run_threaded, name='Receipt', func=main.invoice_receipt)

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
