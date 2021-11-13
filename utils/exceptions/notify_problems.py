# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>


class NotificationDeliveryProblem(Exception):
    def __init__(self, message):
        self.message = message
