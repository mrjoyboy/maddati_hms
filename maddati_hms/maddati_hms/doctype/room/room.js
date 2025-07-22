frappe.ui.form.on("Room", {
    onload(frm) {
        // Run room_type logic on load
        frm.trigger("room_type");

        // If branch is already selected, set prefix
        if (frm.doc.branch) {
            frm.trigger("branch");
        }
    },
    room_type(frm) {
        // Existing logic for capacity and read_only
        frm.set_df_property("capacity", "read_only", frm.doc.room_type !== "Dormitory");

        let rt = frm.doc.room_type;
        if (rt === "Single") {
            frm.set_value("capacity", 1);
        } else if (rt === "Double") {
            frm.set_value("capacity", 2);
        } else {
            frm.set_value("capacity", null);
        }
    },
    branch(frm) {
        if (frm.doc.branch) {
            frappe.db.get_value("Branch", frm.doc.branch, "abbr", (r) => {
                if (r && r.abbr) {
                    // Set room number prefix
                    frm.set_value("room_number", r.abbr + "-");
                }
            });
        }
    }
});
