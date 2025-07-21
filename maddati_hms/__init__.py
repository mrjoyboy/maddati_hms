__version__ = "0.0.1"

import frappe

@frappe.whitelist()
def custom_room_query_with_status(doctype, txt, searchfield, start, page_len, filters):
    branch = filters.get("branch") if isinstance(filters, dict) else None
    return frappe.db.sql("""
        SELECT
            name,
            CONCAT(room_number, ' (', status, ')')
        FROM `tabRoom`
        WHERE branch=%s
        AND status != 'Maintenance'
        AND (room_number LIKE %s OR name LIKE %s)
        LIMIT %s, %s
    """, (branch, f"%{txt}%", f"%{txt}%", start, page_len))