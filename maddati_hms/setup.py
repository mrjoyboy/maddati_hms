import frappe

def enable_auto_repeat_for_sales_invoice():
    doctype = "Sales Invoice"
    meta = frappe.get_doc("DocType", doctype)
    
    if not meta.allow_auto_repeat:
        meta.allow_auto_repeat = 1
        meta.save()
        frappe.db.commit()
