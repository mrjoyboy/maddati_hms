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