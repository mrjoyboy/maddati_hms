import frappe
from frappe.model.document import Document

class Payment(Document):
    def validate(self):
        # If invoice is selected, fetch student and prevent overpayment
        if self.invoice:
            invoice = frappe.get_doc('Student Invoice', self.invoice)
            self.student = invoice.student  # auto-fill student
            if float(self.amount) > float(invoice.outstanding_amount):
                frappe.throw(f"Payment amount cannot exceed the outstanding amount ({invoice.outstanding_amount}) for this invoice.")
        # If no invoice, student must be set
        elif not self.student:
            frappe.throw("Student is required if no invoice is selected.")

    def on_submit(self):
        # Update invoice outstanding amount and status using force update
        if self.invoice:
            invoice = frappe.get_doc('Student Invoice', self.invoice)
            new_outstanding = float(invoice.outstanding_amount or 0) - float(self.amount or 0)
            new_status = 'Paid' if new_outstanding <= 0 else 'Submitted'
            frappe.db.set_value('Student Invoice', invoice.name, {
                'outstanding_amount': max(new_outstanding, 0),
                'status': new_status
            })

    def on_cancel(self):
        # Restore invoice outstanding amount and status using force update
        if self.invoice:
            invoice = frappe.get_doc('Student Invoice', self.invoice)
            new_outstanding = float(invoice.outstanding_amount or 0) + float(self.amount or 0)
            new_status = 'Submitted'
            frappe.db.set_value('Student Invoice', invoice.name, {
                'outstanding_amount': new_outstanding,
                'status': new_status
            })