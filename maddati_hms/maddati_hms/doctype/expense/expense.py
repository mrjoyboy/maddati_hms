# Copyright (c) 2025, Maddati Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Expense(Document):
	def on_submit(self):
		if self.expense_for in ["Salary", "Bonus"] and self.staff:
			staff = frappe.get_doc("Staff", self.staff)
			staff.append("salary_slips", {
				"expense": self.name,
				"type": self.expense_for,
				"amount": self.amount,
				"payment_date": self.date,  # changed from expense_date to date
				"remarks": self.description,
				"status": "Completed"
			})
			staff.save()

	def on_cancel(self):
		if self.expense_for in ["Salary", "Bonus"] and self.staff:
			staff = frappe.get_doc("Staff", self.staff)
			for row in staff.salary_slips:
				if row.expense == self.name:
					row.status = "Cancelled"
			staff.save()
