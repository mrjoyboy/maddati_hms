import frappe
from frappe import _

def get_context(context):
    """
    Set up context for add payment web form
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw(_("Please login to make payments"), frappe.PermissionError)
    
    context.update({
        "title": _("Add Payment"),
        "show_sidebar": True,
        "show_header": True
    })

@frappe.whitelist()
def get_customer_data():
    """
    Get customer data for JavaScript auto-population
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        return {"error": "Please login"}
    
    # Get customer linked to current user
    customer = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    if not customer:
        return {"error": "No customer record found for your account"}
    
    print(f"Found customer: {customer}")  # Debug log
    
    # Get tenant information
    tenant = frappe.db.get_value("Tenant", {"customer": customer}, "name")
    if not tenant:
        return {"error": "No tenant record found for your account"}
    
    print(f"Found tenant: {tenant}")  # Debug log
    
    # Get tenant details
    tenant_doc = frappe.get_doc("Tenant", tenant)
    room = tenant_doc.room
    branch = frappe.db.get_value("Room", room, "branch") if room else None
    
    print(f"Room: {room}, Branch: {branch}")  # Debug log
    
    # Get company from branch doctype
    company = None
    if branch:
        company = frappe.db.get_value("Branch", branch, "company")
        print(f"Company from branch {branch}: {company}")  # Debug log
    
    # Get linked customer from tenant record
    linked_customer = None
    if hasattr(tenant_doc, 'customer') and tenant_doc.customer:
        linked_customer = tenant_doc.customer
    else:
        linked_customer = customer  # Fallback to current customer
    
    print(f"Linked customer: {linked_customer}")  # Debug log
    
    # Additional fallback for company if not found from branch
    if not company and branch:
        # Try to get company from tenant's company field if it exists
        if hasattr(tenant_doc, 'company') and tenant_doc.company:
            company = tenant_doc.company
            print(f"Company from tenant: {company}")  # Debug log
    
    # Final fallback for company - get from system settings or default
    if not company:
        company = frappe.defaults.get_global_default('company')
        print(f"Company from defaults: {company}")  # Debug log
    
    result = {
        "customer": customer,
        "customer_name": frappe.db.get_value("Customer", customer, "customer_name"),
        "tenant": tenant,
        "room": room,
        "branch": branch,
        "company": company,
        "linked_customer": linked_customer
    }
    
    print(f"Final result: {result}")  # Debug log
    return result

@frappe.whitelist()
def get_invoice_details(invoice_name):
    """
    Get invoice details for auto-populating amount field
    """
    if not frappe.session.user or frappe.session.user == "Guest":
        return {"error": "Please login"}
    
    if not invoice_name:
        return {"error": "Invoice name is required"}
    
    # Get customer linked to current user
    customer = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    if not customer:
        return {"error": "No customer record found for your account"}
    
    # Get invoice details and verify it belongs to the current customer
    invoice_data = frappe.db.sql("""
        SELECT 
            name,
            customer,
            grand_total,
            outstanding_amount,
            posting_date,
            due_date,
            status
        FROM `tabSales Invoice`
        WHERE name = %s AND customer = %s AND docstatus = 1
    """, (invoice_name, customer), as_dict=True)
    
    if not invoice_data:
        return {"error": "Invoice not found or access denied"}
    
    invoice = invoice_data[0]
    
    return {
        "name": invoice.name,
        "customer": invoice.customer,
        "grand_total": invoice.grand_total,
        "outstanding_amount": invoice.outstanding_amount,
        "posting_date": invoice.posting_date,
        "due_date": invoice.due_date,
        "status": invoice.status
    }
