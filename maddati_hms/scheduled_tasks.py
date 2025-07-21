import frappe
from frappe.utils import nowdate, add_months, getdate, add_days

def auto_create_student_invoices():
    frappe.logger().info("[Auto Invoice] Running auto_create_student_invoices scheduled task.")
    students = frappe.get_all('Student', filters={'status': 'Active', 'auto_invoice': 1}, fields=['name', 'monthly_fee', 'discount', 'last_invoice_date', 'admission_date', 'extra_services_fees'])
    today = getdate(nowdate())
    for student in students:
        ref_date = student.last_invoice_date or student.admission_date
        if not ref_date:
            continue
        ref_date = getdate(ref_date)
        # Loop to catch up on all missed months
        while today >= getdate(add_months(ref_date, 1)):
            next_invoice_date = add_months(ref_date, 1)
            # Check for existing invoice for this period (idempotency)
            exists = frappe.db.exists(
                "Student Invoice",
                {
                    "student": student.name,
                    "posting_date": ["between", [ref_date, next_invoice_date]]
                }
            )
            if exists:
                ref_date = next_invoice_date
                continue
            invoice = frappe.new_doc('Student Invoice')
            invoice.student = student.name
            invoice.posting_date = next_invoice_date
            invoice.due_date = add_days(next_invoice_date, 5)
            monthly_fee = student.monthly_fee or 0
            if monthly_fee > 0:
                invoice.append('items', {
                    'item_name': 'Monthly Rent',
                    'amount': monthly_fee,
                    'description': 'Monthly Rent'
                })
            discount = student.discount or 0
            if discount > 0:
                invoice.append('items', {
                    'item_name': 'Discount',
                    'amount': -discount,
                    'description': 'Discount'
                })
            extra_services_fees = student.extra_services_fees or 0
            if extra_services_fees > 0:
                invoice.append('items', {
                    'item_name': 'Extra Services Fees',
                    'amount': extra_services_fees,
                    'description': 'Extra Services Fees'
                })
            if invoice.items:
                invoice.insert()
                invoice.submit()
                frappe.db.set_value('Student', student.name, 'last_invoice_date', next_invoice_date)
                frappe.logger().info(f"[Auto Invoice] Created invoice for student: {student.name}")
                recipient = frappe.db.get_value("Student", invoice.student, "email")
                if recipient:
                    frappe.sendmail(
                        recipients=[recipient],
                        subject=f"Your Hostel Invoice {invoice.name}",
                        message="Dear Student, your hostel invoice is attached.",
                        attachments=[frappe.attach_print("Student Invoice", invoice.name, print_format='Student Invoice Branded')],
                    )
                    frappe.logger().info(f"[Auto Invoice] Sent invoice {invoice.name} to {recipient}")
            ref_date = next_invoice_date

@frappe.whitelist()
def send_invoice_email(invoice_name):
    invoice = frappe.get_doc("Student Invoice", invoice_name)
    recipient = frappe.db.get_value("Student", invoice.student, "email")
    if not recipient:
        return "No email found for student."
    frappe.sendmail(
        recipients=[recipient],
        subject=f"Your Hostel Invoice {invoice.name}",
        message="Dear Student, your hostel invoice is attached.",
        attachments=[frappe.attach_print("Student Invoice", invoice.name, print_format='Student Invoice Branded')],
    )
    return f"Invoice sent to {recipient}"

def notify_upcoming_rent_payments():
    today = getdate(nowdate())
    # Find students whose next rent cycle is in 2 days or less (idempotent, robust)
    students = frappe.get_all('Student', filters={'status': 'Active', 'auto_invoice': 1}, fields=['name', 'monthly_fee', 'discount', 'last_invoice_date', 'admission_date', 'email'])
    for student in students:
        ref_date = student.last_invoice_date or student.admission_date
        if not ref_date:
            continue
        ref_date = getdate(ref_date)
        next_rent_date = add_months(ref_date, 1)
        days_until_next_rent = (next_rent_date - today).days
        # Notify for all students whose rent is due in 2 days or less (but not overdue)
        if 0 < days_until_next_rent <= 2:
            if student.email:
                frappe.sendmail(
                    recipients=[student.email],
                    subject="Upcoming Hostel Rent Payment",
                    message=f"Dear Student, your next monthly rent will be due in {days_until_next_rent} day(s) (on {next_rent_date}). Please ensure timely payment.",
                )
                frappe.logger().info(f"[Rent Reminder] Sent upcoming rent notification to {student.email} for {student.name}")

def mark_overdue_invoices():
    today = nowdate()
    # Idempotent: always updates all overdue invoices, even after downtime
    overdue_invoices = frappe.get_all(
        'Student Invoice',
        filters={
            'status': ['in', ['Submitted', 'Overdue']],  # include already overdue for idempotency
            'due_date': ['<', today],
            'outstanding_amount': ['>', 0]
        },
        fields=['name', 'status']
    )
    for inv in overdue_invoices:
        # Only update if not already Overdue (optional, for efficiency)
        if inv.status != 'Overdue':
            frappe.db.set_value('Student Invoice', inv.name, 'status', 'Overdue')
            frappe.logger().info(f"[Overdue Invoices] Marked invoice {inv.name} as Overdue.")
    # Notify students about overdue invoices
    for inv in overdue_invoices:
        student_email = frappe.db.get_value("Student Invoice", inv.name, "student_email")
        if student_email:
            frappe.sendmail(
                recipients=[student_email],
                subject=f"Your Hostel Invoice {inv.name} is Overdue",
                message="Dear Student, your hostel invoice is overdue. Please make the payment at your earliest convenience.",
                attachments=[frappe.attach_print("Student Invoice", inv.name, print_format='Student Invoice Branded')],
            )
            frappe.logger().info(f"[Overdue Invoices] Sent overdue notification for invoice {inv.name} to {student_email}")
        else:
            frappe.logger().warning(f"[Overdue Invoices] No email found for invoice {inv.name}")