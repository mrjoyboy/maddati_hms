__version__ = "0.0.1"

import frappe

@frappe.whitelist(allow_guest=True)
def custom_room_query_with_status(
    doctype=None,
    txt=None,
    searchfield=None,
    start=0,
    page_len=10,
    filters=None,
    as_dict=False,
    reference_doctype=None,
    ignore_user_permissions=False,
    **kwargs,
):
    branch = None
    if isinstance(filters, dict) and filters.get("branch"):
        branch = filters.get("branch")
    if not branch:
        branch = kwargs.get("branch")

    txt = txt or ""
    start = int(start or 0)
    page_len = int(page_len or 10)

    raw_rows = frappe.db.sql(
        """
        SELECT
            name,
            room_number,
            COALESCE(status, '') as status,
            COALESCE(capacity, 0) as capacity,
            COALESCE(occupied_beds, 0) as occupied_beds,
            COALESCE(monthly_rent, 0) as monthly_rent
        FROM `tabRoom`
        WHERE (%s IS NULL OR branch = %s)
        AND (
            room_number LIKE %s OR name LIKE %s
        )
        ORDER BY room_number ASC
        LIMIT %s, %s
        """,
        (branch, branch, f"%{txt}%", f"%{txt}%", start, page_len),
        as_dict=False,
    )

    desk_rows = []
    web_rows = []
    for name, room_number, status, capacity, occupied_beds, monthly_rent in raw_rows:
        monthly_str = frappe.utils.fmt_money((monthly_rent or 0), currency=None, precision=0)
        # Plain description (works for Desk)
        plain_desc = f"({status}) - (Capacity-{capacity}) - (Occupied Beds -{occupied_beds}) - (Monthly Rent - {monthly_str})"

        # Build small badge + muted description for Web
        status_lower = (status or "").lower()
        if status_lower == "available":
            status_fg = "#1e7e34"  # green text
            status_bg = "#e6f4ea"  # green light bg
        elif status_lower == "full":
            status_fg = "#b02a37"  # red text
            status_bg = "#fdecea"  # red light bg
        elif status_lower == "maintenance":
            status_fg = "#b8860b"  # yellow text
            status_bg = "#fff8e1"  # yellow light bg
        else:
            status_fg = "#6c757d"
            status_bg = "#f1f3f5"

        is_unavailable = status_lower in ("full", "maintenance")
        muted_style = "color: #6c757d;" if is_unavailable else ""

        esc_status = frappe.utils.escape_html(status or "")
        esc_details = frappe.utils.escape_html(
            f"(Capacity-{capacity}) - (Occupied Beds -{occupied_beds}) - (Monthly Rent - {monthly_str})"
        )
        badge_html = (
            f"<span style=\"display:inline-block;margin-right:8px;padding:2px 8px;border-radius:999px;"
            f"font-size:11px;line-height:1;background-color:{status_bg};color:{status_fg};\">{esc_status}</span>"
        )
        web_desc_html = f"<span style=\"{muted_style}\">{badge_html}<span class=\"small\">{esc_details}</span></span>"

        # Desk tuples
        desk_rows.append([name, room_number, plain_desc])
        # Web objects
        web_rows.append({
            "value": name,
            "label": room_number,
            "description": web_desc_html,
        })

    if doctype:
        return desk_rows
    else:
        return web_rows

@frappe.whitelist(allow_guest=True)
def customer_invoice_query(
    doctype=None,
    txt=None,
    searchfield=None,
    start=0,
    page_len=10,
    filters=None,
    as_dict=False,
    reference_doctype=None,
    ignore_user_permissions=False,
    **kwargs,
):
    """
    Query function to get only unpaid invoices for the current logged-in customer
    """
    # Get current user's customer
    customer = None
    if frappe.session.user and frappe.session.user != "Guest":
        customer = frappe.db.get_value("Customer", {"email_id": frappe.session.user}, "name")
    
    if not customer:
        return []

    txt = txt or ""
    start = int(start or 0)
    page_len = int(page_len or 10)

    raw_rows = frappe.db.sql(
        """
        SELECT
            name,
            posting_date,
            due_date,
            grand_total,
            outstanding_amount,
            status
        FROM `tabSales Invoice`
        WHERE customer = %s
        AND docstatus = 1
        AND outstanding_amount > 0
        AND (
            name LIKE %s OR 
            CONCAT(name, ' - Outstanding: ', outstanding_amount) LIKE %s
        )
        ORDER BY due_date ASC, name ASC
        LIMIT %s, %s
        """,
        (customer, f"%{txt}%", f"%{txt}%", start, page_len),
        as_dict=False,
    )

    desk_rows = []
    web_rows = []
    for name, posting_date, due_date, grand_total, outstanding_amount, status in raw_rows:
        # Format amounts
        outstanding_str = frappe.utils.fmt_money((outstanding_amount or 0), currency=None, precision=2)
        total_str = frappe.utils.fmt_money((grand_total or 0), currency=None, precision=2)
        
        # Format dates
        posting_str = frappe.utils.formatdate(posting_date) if posting_date else ""
        due_str = frappe.utils.formatdate(due_date) if due_date else ""
        
        # Determine payment status
        if outstanding_amount == grand_total:
            payment_status = "Unpaid"
            status_color = "#dc3545"  # Red for unpaid
            status_bg = "#f8d7da"      # Light red background
        else:
            payment_status = "Partly Paid"
            status_color = "#fd7e14"  # Orange for partly paid
            status_bg = "#fff3cd"     # Light orange background
        
        # Plain description (works for Desk)
        plain_desc = f"[{payment_status}] Remaining: {outstanding_str} | Total: {total_str} | Due: {due_str}"

        # Build description for Web with status badge
        esc_outstanding = frappe.utils.escape_html(f"Remaining: {outstanding_str}")
        esc_total = frappe.utils.escape_html(f"Total: {total_str}")
        esc_due = frappe.utils.escape_html(f"Due: {due_str}")
        
        # Create status badge HTML
        status_badge = (
            f"<span style=\"display:inline-block;margin-right:8px;padding:2px 8px;border-radius:999px;"
            f"font-size:11px;line-height:1;background-color:{status_bg};color:{status_color};"
            f"font-weight:bold;\">{payment_status}</span>"
        )
        
        # Show due date on next line to prevent cropping
        web_desc_html = (
            f"{status_badge}<span class=\"small\">{esc_outstanding} | {esc_total}</span><br>"
            f"<span class=\"small\" style=\"color: #6c757d; margin-left: 20px;\">{esc_due}</span>"
        )

        # Desk tuples
        desk_rows.append([name, name, plain_desc])
        # Web objects
        web_rows.append({
            "value": name,
            "label": name,
            "description": web_desc_html,
        })

    if doctype:
        return desk_rows
    else:
        return web_rows
