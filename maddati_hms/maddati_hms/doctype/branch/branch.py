import frappe
from frappe.model.document import Document
from frappe import _

class Branch(Document):

    def validate(self):
        # Prevent duplicate Company Abbr
        if self.abbr and frappe.db.exists("Company", {"abbr": self.abbr, "name": ["!=", self.company]}):
            frappe.throw(f"A company with abbreviation '{self.abbr}' already exists.")

    def after_insert(self):
        # Prevent duplicate Company
        if frappe.db.exists("Company", {"company_name": self.branch_name}):
            company = frappe.get_doc("Company", {"company_name": self.branch_name})
        else:
            company = frappe.new_doc("Company")
            company.company_name = self.branch_name
            company.abbr = self.abbr
            company.default_currency = self.default_currency
            company.country = self.country
            company.create_chart_of_accounts_based_on = "Standard"
            company.insert()

        # Link the company to this branch (assumes 'company' is a Link field in Branch)
        self.db_set("company", company.name)

    def on_update(self):
        if self.company and frappe.db.exists("Company", self.company):
            company = frappe.get_doc("Company", self.company)
            updated = False

            if company.company_name != self.branch_name:
                company.company_name = self.branch_name
                updated = True
            if company.abbr != self.abbr:
                company.abbr = self.abbr
                updated = True
            if company.default_currency != self.default_currency:
                company.default_currency = self.default_currency
                updated = True
            if company.country != self.country:
                company.country = self.country
                updated = True

            if updated:
                company.save()

    def on_trash(self):
        # Prevent deletion if linked Company exists
        if self.company and frappe.db.exists("Company", self.company):
            frappe.throw(_("Cannot delete Branch as linked Company '{0}' exists.").format(self.company))
