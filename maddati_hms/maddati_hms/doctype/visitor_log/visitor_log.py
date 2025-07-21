# Copyright (c) 2025, Maddati Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VisitorLog(Document):
	def validate(self):
		if self.check_out and self.visit_datetime:
			if self.check_out < self.visit_datetime:
				frappe.throw("Check Out cannot be before Check In.")
