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

@frappe.whitelist(allow_guest=True)
def get_room_fees(room: str):
    if not room:
        return {}
    values = frappe.db.get_value(
        "Room",
        room,
        ["status", "monthly_rent", "admission_fee", "security_deposit"],
        as_dict=True,
    )
    return values or {}

@frappe.whitelist()
def get_customer_company(customer):
    """Get the company associated with a customer"""
    if not customer:
        return None
    
    # First try to get from custom_company field
    custom_company = frappe.db.get_value('Customer', customer, 'custom_company')
    if custom_company:
        return custom_company
    
    # If no custom_company, try to get from linked tenant's branch company
    tenant = frappe.db.get_value('Customer', customer, 'custom_tenant')
    if tenant:
        branch = frappe.db.get_value('Tenant', tenant, 'branch')
        if branch:
            company = frappe.db.get_value('Branch', branch, 'company')
            if company:
                return company
    
    # If still no company found, return the default company
    default_company = frappe.db.get_value('Global Defaults', None, 'default_company')
    return default_company

