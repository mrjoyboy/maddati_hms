import frappe

@frappe.whitelist()
def get_tenant_item_amount(tenant, item_code):
    doc = frappe.get_doc("Tenant", tenant)
    if item_code == "Tenant Monthly Fee":
        return doc.monthly_fee or 0
    if item_code == "Tenant Admission Fee":
        return doc.admission_fee or 0
    if item_code == "Tenant Security Deposit":
        return doc.security_deposit or 0
    return 0
