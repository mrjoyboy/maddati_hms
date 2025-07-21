# Copyright (c) 2025, Maddati Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Tenant(Document):

    def validate(self):
        if self.room and self.status == "Active":
            if self.is_new() or self.has_value_changed("room"):
                room = frappe.get_doc('Room', self.room)
                if room.occupied_beds >= (room.capacity or 0) and not self.flags.ignore_full_check:
                    frappe.throw(f"Room {room.room_number} is already full. Please select another room.")

        # Prevent branch/room change unless status is Active
        if self.status != "Active":
            if self.has_value_changed("branch") or self.has_value_changed("room"):
                frappe.throw("You cannot change Branch or Room unless tenant status is Active.")

    def after_insert(self):
        if not self.customer:
            customer_doc = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": self.tenant_name or self.name,
                "customer_type": "Individual",
                "customer_group": "Hostel Tenants",
                "territory": "All Territories",
                "customer_email_address": self.email or "",
                "custom_tenant": self.name,
                "custom_company": self.branch,
                "image": self.photo or "",
                "gender": self.gender or ""
            })
            customer_doc.insert()
            self.db_set("customer", customer_doc.name)

            self.send_email("Tenant Welcome Email")

        if self.room:
            self.update_room_occupancy(increase=True)

    def before_save(self):
        self.update_accommodation_history()

    def update_accommodation_history(self):
        if not self.branch or not self.room:
            return

        today = frappe.utils.today()

        if self.status == "Active":
            existing = None
            for row in self.accommodation_history:
                if row.room == self.room and row.branch == self.branch and row.status == "Active" and not row.to_date:
                    existing = row
                    break

            if not existing:
                self.append("accommodation_history", {
                    "branch": self.branch,
                    "room": self.room,
                    "from_date": today,
                    "status": "Active"
                })

        elif self.status in ["Left", "Cancelled"]:
            for row in self.accommodation_history:
                if row.room == self.room and row.branch == self.branch and row.status == "Active" and not row.to_date:
                    row.to_date = today
                    row.status = self.status

    def on_update(self):
        if self.room and self.status in ["Left", "Cancelled"]:
            self.update_room_occupancy(increase=False)

        if self.has_value_changed("branch") or self.has_value_changed("room"):
            self.send_email("Tenant Update Email")

        if self.has_value_changed("status") and self.status in ["Left", "Cancelled"]:
            self.send_email("Tenant Left Email")

        self.sync_customer()

    def on_cancel(self):
        if self.room:
            self.update_room_occupancy(increase=False)

    def on_trash(self):
        if self.status not in ["Left", "Cancelled"]:
            frappe.throw("You can only delete an Admission if its status is Left or Cancelled.")

        if self.room:
            self.update_room_occupancy(increase=False)

        if self.customer:
            customer = frappe.get_doc('Customer', self.customer)
            if not customer.disabled:
                customer.disabled = 1
                customer.save()

    def update_room_occupancy(self, increase=True):
        room = frappe.get_doc('Room', self.room)
        if increase:
            room.occupied_beds = (room.occupied_beds or 0) + 1
        else:
            room.occupied_beds = max((room.occupied_beds or 1) - 1, 0)

        room.status = "Full" if room.occupied_beds >= (room.capacity or 0) else "Available"
        room.save()

    def sync_customer(self):
        if not self.customer:
            return

        customer = frappe.get_doc('Customer', self.customer)
        updated = False

        field_map = {
            "customer_name": self.tenant_name or self.name,
            "customer_email_address": self.email or "",
            "gender": self.gender or "",
            "image": self.photo or "",
            "custom_tenant": self.name,
            "custom_company": self.branch
        }

        for field, value in field_map.items():
            if customer.get(field) != value:
                customer.set(field, value)
                updated = True

        if self.status in ["Left", "Cancelled"]:
            if not customer.disabled:
                customer.disabled = 1
                updated = True
        elif self.status == "Active":
            if customer.disabled:
                customer.disabled = 0
                updated = True

        if updated:
            customer.save()

    def send_email(self, template_name):
        if not self.email:
            return

        try:
            template = frappe.get_doc("Email Template", template_name)
            subject = template.subject or "Hostel Notification"
            message = frappe.render_template(template.response, {"doc": self})

            frappe.sendmail(
                recipients=self.email,
                subject=subject,
                message=message
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Failed to send email for {template_name}")
