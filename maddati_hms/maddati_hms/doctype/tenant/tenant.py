
# Copyright (c) 2025, Maddati Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from datetime import date

class Tenant(Document):
    def validate(self):
        """
        - Create new row in accommodation history child table when status, branch, or room is changed
        - If status is Active and changed to Left/Cancelled, add new row with from and to date
        - If status is Left/Cancelled and changed to Active, add new row with from date only
        - If branch or room is changed, add new row
        - Don't allow branch/room change when status is Active
        """
        if not self.is_new():
            old_doc = frappe.get_doc(self.doctype, self.name)
            status_changed = old_doc.status != self.status
            branch_changed = old_doc.branch != self.branch
            room_changed = old_doc.room != self.room

            # Status change logic
            if status_changed:
                # Active -> Left/Cancelled: update existing active row
                if old_doc.status == "Active" and self.status in ["Left", "Cancelled"]:
                    updated = False
                    for h in reversed(self.accommodation_history):
                        if h.status == "Active" and not h.to_date:
                            h.status = self.status
                            h.to_date = date.today().strftime('%Y-%m-%d')
                            h.remarks = f"Status changed from {old_doc.status} to {self.status}"
                            updated = True
                            break
                    if not updated:
                        # fallback: add new row if no active found
                        self._add_accommodation_history_row(from_date=date.today(), to_date=date.today(), status=self.status, remarks=f"Status changed from {old_doc.status} to {self.status}")
                    # Decrement occupied_beds in old room
                    if old_doc.room:
                        room_doc = frappe.get_doc("Room", old_doc.room)
                        if room_doc.occupied_beds and room_doc.occupied_beds > 0:
                            room_doc.occupied_beds -= 1
                            room_doc.save(ignore_permissions=True)
                # Left/Cancelled -> Active: check if there's already an active entry, if not add new row
                elif old_doc.status in ["Left", "Cancelled"] and self.status == "Active":
                    # Check if there's already an active entry
                    has_active_entry = any(h.status == "Active" and not h.to_date for h in self.accommodation_history)
                    if not has_active_entry:
                        self._add_accommodation_history_row(from_date=date.today(), to_date=None, status=self.status, remarks=f"Status changed from {old_doc.status} to {self.status}")
                        # Increment occupied_beds in new room
                        if self.room:
                            room_doc = frappe.get_doc("Room", self.room)
                            room_doc.occupied_beds = (room_doc.occupied_beds or 0) + 1
                            room_doc.save(ignore_permissions=True)
            # Branch/Room change logic
            elif branch_changed or room_changed:
                # If status is Active, close previous active row with Left status and create new active row
                if old_doc.status == "Active":
                    # Close previous active row
                    updated = False
                    for h in reversed(self.accommodation_history):
                        if h.status == "Active" and not h.to_date:
                            h.status = "Left"
                            h.to_date = date.today().strftime('%Y-%m-%d')
                            h.remarks = f"Auto-closed due to branch/room change"
                            updated = True
                            break
                    if not updated:
                        self._add_accommodation_history_row(from_date=date.today(), to_date=date.today(), status="Left", remarks="Auto-closed due to branch/room change")
                    # Create new active row for new branch/room
                    self._add_accommodation_history_row(from_date=date.today(), to_date=None, status="Active", remarks="Branch/Room changed while status Active")
                # If status is Left/Cancelled, update last Left/Cancelled row
                elif self.status in ["Left", "Cancelled"]:
                    updated = False
                    for h in reversed(self.accommodation_history):
                        if h.status in ["Left", "Cancelled"] and h.to_date:
                            h.branch = self.branch
                            h.room = self.room
                            h.remarks = f"Branch/Room changed while status {self.status}"
                            updated = True
                            break
                    if not updated:
                        # fallback: add new row if no Left/Cancelled found
                        self._add_accommodation_history_row(from_date=date.today(), to_date=date.today(), status=self.status, remarks=f"Branch/Room changed")
                else:
                    # For other statuses, add new row
                    self._add_accommodation_history_row(from_date=date.today(), to_date=None, status=self.status, remarks=f"Branch/Room changed")

            # Enable/Disable linked Customer based on status change
            if status_changed:
                if (self.status or "").lower() == "active":
                    # Ensure a customer exists; create/link if missing
                    if not self.customer:
                        result = create_or_link_customer(self.name)
                        if result and isinstance(result, dict) and result.get("customer"):
                            self.customer = result["customer"]
                            # Update the customer field in the database
                            self.db_set("customer", self.customer)
                    if self.customer:
                        frappe.db.set_value('Customer', self.customer, 'disabled', 0)
                else:
                    # Non-active statuses: disable linked customer if present
                    if self.customer:
                        frappe.db.set_value('Customer', self.customer, 'disabled', 1)

        else:
            # New tenant: create initial row if branch and room are set
            if self.branch and self.room:
                self._add_accommodation_history_row(from_date=date.today(), to_date=None, status=self.status or "Active", remarks="Initial accommodation assignment")

        self._validate_accommodation_history()
        
        # Sync customer fields if tenant is linked to a customer
        if self.customer:
            self._sync_customer_fields()

    def after_rename(self, old_name, new_name, merge=False):
        """Handle tenant rename - update customer name to match new tenant ID"""
        if self.customer:
            # Update customer name to match the new tenant ID
            frappe.db.set_value('Customer', self.customer, 'customer_name', new_name)
            # Also update the custom_tenant field to ensure consistency
            frappe.db.set_value('Customer', self.customer, 'custom_tenant', new_name)
            frappe.msgprint(_('Customer "{0}" name updated to match new tenant ID "{1}"').format(self.customer, new_name), indicator='green')

    def after_insert(self):
        # Auto-create/link Customer only if new Tenant is Active and customer not set
        if (self.status or "").lower() == "active" and not self.customer:
            create_or_link_customer(self.name)

    def before_delete(self):
        # Prevent deletion when Tenant is Active or linked to Customer
        if (self.status or "").lower() == "active":
            frappe.throw(_("Cannot delete Tenant while status is Active. Set status to Left, then delete."))
        if self.customer:
            frappe.throw(_("Tenant linked to Customer cannot be deleted. Unlink the Customer first."))

    def before_trash(self):
        # Extra safety: some flows call before_trash
        if (self.status or "").lower() == "active":
            frappe.throw(_("Cannot delete Tenant while status is Active. Set status to Left, then delete."))
        if self.customer:
            frappe.throw(_("Tenant linked to Customer cannot be deleted. Unlink the Customer first."))

    def on_trash(self):
        # Final guard on deletion
        if (self.status or "").lower() == "active":
            frappe.throw(_("Cannot delete Tenant while status is Active. Set status to Left, then delete."))
        if self.customer:
            frappe.throw(_("Tenant linked to Customer cannot be deleted. Unlink the Customer first."))

    def _add_accommodation_history_row(self, from_date, to_date, status, remarks):
        self.append("accommodation_history", {
            "branch": self.branch,
            "room": self.room,
            "from_date": from_date.strftime('%Y-%m-%d') if hasattr(from_date, 'strftime') else str(from_date),
            "to_date": to_date.strftime('%Y-%m-%d') if to_date and hasattr(to_date, 'strftime') else (str(to_date) if to_date else None),
            "status": status,
            "remarks": remarks
        })

    def _sync_customer_fields(self):
        """Sync tenant fields to linked customer"""
        if not self.customer:
            return
            
        customer_updates = {}
        
        # Sync tenant name to customer name
        if self.tenant_name:
            customer_updates['customer_name'] = self.tenant_name
            
        # Sync email
        if self.email:
            customer_updates['email_id'] = self.email
            customer_updates['customer_email_address'] = self.email
            

            
        # Sync custom_tenant field
        customer_updates['custom_tenant'] = self.name
        
        # Sync company from branch
        if self.branch:
            company = frappe.db.get_value('Branch', self.branch, 'company')
            if company:
                customer_updates['custom_company'] = company
        
        # Update customer if there are changes
        if customer_updates:
            frappe.db.set_value('Customer', self.customer, customer_updates)

    def _validate_accommodation_history(self):
        # Only one active entry (status = "Active" and no to_date) allowed
        active_entries = [h for h in self.accommodation_history if h.status == "Active" and not h.to_date]
        if len(active_entries) > 1:
            frappe.throw(_("Only one active accommodation entry should exist at a time."))
        # Validate required fields
        for h in self.accommodation_history:
            if not h.branch:
                frappe.throw(_("Branch is required for all accommodation history entries."))
            if not h.room:
                frappe.throw(_("Room is required for all accommodation history entries."))
            if not h.from_date:
                frappe.throw(_("From Date is required for all accommodation history entries."))
            if h.status == "Active" and h.to_date:
                frappe.throw(_("Active status entries should not have a To Date."))
            if h.status in ["Left", "Cancelled"] and not h.to_date:
                frappe.throw(_("Left/Cancelled status entries must have a To Date."))

@frappe.whitelist()
def create_or_link_customer(tenant: str):
    doc = frappe.get_doc('Tenant', tenant)
    if doc.customer:
        frappe.msgprint(_('Customer is already linked: {0}').format(doc.customer), indicator='blue')
        return { 'customer': doc.customer }

    # Try matching existing Customer by custom fields or name/email
    customer = frappe.db.get_value('Customer', { 'custom_tenant': doc.name }, 'name')
    if not customer:
        customer = frappe.db.get_value('Customer', { 'customer_name': doc.tenant_name }, 'name')  # Look for customer with tenant name
    if not customer and doc.email:
        customer = frappe.db.get_value('Customer', { 'customer_email_address': doc.email }, 'name')
    if not customer and doc.email:
        customer = frappe.db.get_value('Customer', { 'email_id': doc.email }, 'name')

    if not customer:
        # Create new Customer
        customer = frappe.get_doc({
            'doctype': 'Customer',
            'customer_name': doc.name,  # Use tenant ID instead of tenant_name for easier identification
            'customer_type': 'Individual',
            'customer_group': 'Individual',
            'email_id': doc.email,
            'mobile_no': doc.contact_number,
            'custom_tenant': doc.name,
            'customer_email_address': doc.email,
            'custom_company': frappe.db.get_value('Branch', doc.branch, 'company') if doc.branch else None,
            'disabled': 0,
        }).insert(ignore_permissions=True).name
        frappe.msgprint(_('New Customer created and linked: {0}').format(customer), indicator='green')
    else:
        # Update custom mappings and re-enable customer if it was disabled
        frappe.db.set_value('Customer', customer, 'custom_tenant', doc.name)
        frappe.db.set_value('Customer', customer, 'disabled', 0)  # Re-enable the customer
        if doc.email:
            frappe.db.set_value('Customer', customer, 'customer_email_address', doc.email)
        if doc.branch:
            company = frappe.db.get_value('Branch', doc.branch, 'company')
            if company:
                frappe.db.set_value('Customer', customer, 'custom_company', company)
        frappe.msgprint(_('Existing Customer re-enabled and linked: {0}').format(customer), indicator='green')

    # Don't modify the tenant document here - let the client handle it
    return { 'customer': customer }

@frappe.whitelist()
def unlink_customer(tenant: str):
    doc = frappe.get_doc('Tenant', tenant)
    if not doc.customer:
        frappe.msgprint(_('No customer linked to this tenant'), indicator='red')
        return { 'success': False, 'message': 'No customer linked to this tenant' }
    
    customer_name = doc.customer
    
    # Clear custom_tenant field in customer and disable it
    frappe.db.set_value('Customer', customer_name, 'custom_tenant', '')
    frappe.db.set_value('Customer', customer_name, 'disabled', 1)
    
    frappe.msgprint(_('Customer "{0}" unlinked and disabled successfully').format(customer_name), indicator='green')
    return { 'success': True, 'customer': customer_name }

@frappe.whitelist()
def create_single_invoice(tenant_name: str, item_code: str, amount: float, invoice_type: str):
    """
    Create a single Sales Invoice for a specific item type
    """
    try:
        tenant_doc = frappe.get_doc('Tenant', tenant_name)
        
        if not tenant_doc.customer:
            return {
                'success': False,
                'message': f'No customer linked to tenant {tenant_name}. Cannot create invoice.'
            }
            
        if not tenant_doc.branch:
            return {
                'success': False,
                'message': f'No branch assigned to tenant {tenant_name}. Cannot create invoice.'
            }
            
        # Get company from branch
        company = frappe.db.get_value('Branch', tenant_doc.branch, 'company')
        if not company:
            return {
                'success': False,
                'message': f'No company assigned to branch {tenant_doc.branch}. Cannot create invoice.'
            }
            
        # Get default receivable account for the company
        receivable_account = frappe.db.get_value('Company', company, 'default_receivable_account')
        if not receivable_account:
            return {
                'success': False,
                'message': f'No default receivable account set for company {company}. Cannot create invoice.'
            }
            
        # Get default income account for the company
        income_account = frappe.db.get_value('Company', company, 'default_income_account')
        if not income_account:
            return {
                'success': False,
                'message': f'No default income account set for company {company}. Cannot create invoice.'
            }
            
        # Get customer name
        customer_name = frappe.db.get_value('Customer', tenant_doc.customer, 'customer_name')
        
        # Get cost center from company
        cost_center = frappe.db.get_value('Company', company, 'cost_center')
        
        # Create description based on invoice type
        if invoice_type == 'Monthly Fee':
            description = f'Monthly fee for tenant {tenant_doc.name} - {tenant_doc.tenant_name} ({frappe.utils.formatdate(frappe.utils.today(), "MMMM YYYY")})'
        else:
            description = f'{invoice_type.lower()} for tenant {tenant_doc.name} - {tenant_doc.tenant_name}'
        
        # Create Sales Invoice
        invoice = frappe.get_doc({
            'doctype': 'Sales Invoice',
            'customer': tenant_doc.customer,
            'customer_name': customer_name,
            'company': company,
            'posting_date': frappe.utils.today(),
            'due_date': frappe.utils.add_days(frappe.utils.today(), 7),  # Due in 7 days
            'debit_to': receivable_account,
            'items': [{
                'item_code': item_code,
                'item_name': item_code,
                'description': description,
                'qty': 1,
                'rate': amount,
                'amount': amount,
                'income_account': income_account,
                'cost_center': cost_center,
                'item_group': 'Services'
            }],
            'custom_tenant': tenant_doc.name,
            'custom_branch': tenant_doc.branch,
            'custom_room': tenant_doc.room,
            'custom_invoice_type': invoice_type
        })
        
        invoice.insert(ignore_permissions=True)
        invoice.submit()
        
        return {
            'success': True,
            'invoice_name': invoice.name,
            'message': f'{invoice_type} Invoice created successfully: {invoice.name} for amount {frappe.format(amount, "Currency")}'
        }
        
    except Exception as e:
        frappe.log_error(f'Error creating {invoice_type} invoice for tenant {tenant_name}: {str(e)}', f'{invoice_type} Invoice Creation Failed')
        return {
            'success': False,
            'message': f'Error creating {invoice_type} invoice: {str(e)}'
        }