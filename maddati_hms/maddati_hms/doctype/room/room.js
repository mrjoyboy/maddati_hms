frappe.ui.form.on("Room", {
onload(frm) {
    // Only set prefix if branch is selected and doc is new
    if (frm.doc.branch && frm.is_new()) {
        frm.trigger("branch");
    }
},
room_type(frm) {
    // Set capacity field as read-only for Single/Double, editable for Dormitory
    frm.set_df_property("capacity", "read_only", frm.doc.room_type !== "Dormitory");

    let rt = frm.doc.room_type;
    if (frm.is_new()) {
        if (rt === "Single") {
            frm.set_value("capacity", 1);
        } else if (rt === "Double") {
            frm.set_value("capacity", 2);
        }
        // For Dormitory, leave capacity for user input
    } else {
        if (rt === "Single" && frm.doc.capacity !== 1) {
            frm.set_value("capacity", 1);
        } else if (rt === "Double" && frm.doc.capacity !== 2) {
            frm.set_value("capacity", 2);
        }
        // For Dormitory, do not overwrite capacity
    }
},
branch(frm) {
    if (frm.doc.branch && frm.is_new()) {
        frappe.db.get_value("Branch", frm.doc.branch, "abbr", (r) => {
            if (r && r.abbr) {
                // Set room number prefix only for new docs
                frm.set_value("room_number", r.abbr + "-");
            }
        });
    }
}
});

// Trigger room_type logic only when room_type field is changed
frappe.ui.form.on('Room', {
    room_type: function(frm) {
        frm.events.room_type(frm);
    }
});
