# Copyright (c) 2025, Maddati Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class StudentInvoice(Document):
    def validate(self):
        # Recalculate total
        self.total_amount = sum([float(item.amount or 0) for item in self.fee_items])

        # Calculate payments made
        payments = frappe.get_all(
            'Payment',
            filters={'invoice': self.name, 'status': 'Completed'},
            fields=['amount']
        )
        paid_amount = sum([float(p.amount or 0) for p in payments])

        # Set outstanding amount
        self.outstanding_amount = self.total_amount - paid_amount

        # Update status
        if self.outstanding_amount <= 0:
            self.status = "Paid"
        elif self.due_date and str(self.due_date) < nowdate():
            self.status = "Overdue"
        else:
            self.status = "Submitted"

    def on_submit(self):
        # Recalculate status
        if float(self.outstanding_amount) > 0:
            if self.due_date and str(self.due_date) < nowdate():
                self.status = "Overdue"
            else:
                self.status = "Submitted"
        else:
            self.status = "Paid"

        # Create Sales Invoice automatically
        sales_invoice = frappe.new_doc("Sales Invoice")
        sales_invoice.customer = self.customer
        sales_invoice.posting_date = self.posting_date
        sales_invoice.due_date = self.due_date

        # Fetch default income account from Company
        default_income_account = frappe.db.get_value(
            "Company", frappe.defaults.get_user_default("company"), "default_income_account"
        )
        if not default_income_account:
            frappe.throw("Please set Default Income Account in Company master.")

        # Add items from fee_items
        for item in self.fee_items:
            sales_invoice.append("items", {
                "item_name": item.description,
                "description": item.description,
                "qty": 1,
                "rate": item.amount,
                "income_account": default_income_account
            })

        # Save and submit Sales Invoice
        sales_invoice.insert()
        sales_invoice.submit()

        # Link Sales Invoice back to Student Invoice
        self.db_set("linked_sales_invoice", sales_invoice.name)

    def on_cancel(self):
        self.status = "Draft"

    def get_linked_payments(self):
        return frappe.get_all(
            "Payment",
            filters={"invoice": self.name},
            fields=["name", "amount", "payment_date", "status"]
        )

    def onload(self):
        # Refill linked payments child table
        self.set("linked_payments", [])
        payments = frappe.get_all(
            "Payment",
            filters={"invoice": self.name},
            fields=["name", "amount", "payment_date", "docstatus", "status"]
        )
        for p in payments:
            payment_status = p.status
            if p.docstatus == 2:
                payment_status = "Cancelled"
            self.append("linked_payments", {
                "payment": p.name,
                "amount": p.amount,
                "payment_date": p.payment_date,
                "status": payment_status
            })
