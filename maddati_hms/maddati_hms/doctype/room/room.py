# Copyright (c) 2025, Maddati Tech and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Room(Document):
    def validate(self):
        if self.room_type == "Single":
            if self.capacity != 1:
                frappe.throw("Capacity must be 1 for Single rooms.")
        elif self.room_type == "Double":
            if self.capacity != 2:
                frappe.throw("Capacity must be 2 for Double rooms.")
        elif self.room_type == "Dormitory":
            if not self.capacity or self.capacity < 1:
                frappe.throw("Capacity must be at least 1 for Dormitory rooms.")
        else:
            frappe.throw("Invalid room type. Must be Single, Double, or Dormitory.")
