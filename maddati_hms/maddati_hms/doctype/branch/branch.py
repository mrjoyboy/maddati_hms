import frappe
from frappe.model.document import Document
from frappe import _

class Branch(Document):

    def validate(self):
        # Prevent duplicate Company Abbr
        if self.abbr and frappe.db.exists("Company", {"abbr": self.abbr, "name": ["!=", self.company]}):
            frappe.throw(f"A company with abbreviation '{self.abbr}' already exists.")
        
        # Update linked customers if company changes
        if not self.is_new():
            old_doc = frappe.get_doc(self.doctype, self.name)
            if old_doc.company != self.company:
                self._update_linked_customers(old_doc.company, self.company)

    def _update_linked_customers(self, old_company, new_company):
        """Update custom_company field for all customers linked to tenants in this branch"""
        if not new_company:
            return
            
        # Find all tenants in this branch
        tenants = frappe.get_all('Tenant', 
            filters={'branch': self.name, 'customer': ['is', 'set']},
            fields=['customer']
        )
        
        # Update customer custom_company field
        for tenant in tenants:
            if tenant.customer:
                frappe.db.set_value('Customer', tenant.customer, 'custom_company', new_company)

    def on_trash(self):
        # Prevent deletion if linked Company exists
        if self.company and frappe.db.exists("Company", self.company):
            frappe.throw(_("Cannot delete Branch as linked Company '{0}' exists.").format(self.company))

    def get_indicator(self):
        color_map = {
            "Active": "green",
            "Maintenance": "yellow",
            "Closed": "red"
        }
        return (self.status, color_map.get(self.status, "gray"), f"status,=,{self.status}")
