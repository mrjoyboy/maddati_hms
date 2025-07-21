// Copyright (c) 2025, Maddati Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Visitor Log", {
	refresh(frm) {

	},
	branch: function(frm) {
		frm.set_query("room", function() {
			if (frm.doc.branch) {
				return {
					filters: {
						branch: frm.doc.branch
					}
				};
			}
		});
	},
	related_person_type: function(frm) {
		if (frm.doc.related_person_type === "Other") {
			frm.set_df_property("related_person", "hidden", 1);
			frm.set_value("related_person", null);
		} else {
			frm.set_df_property("related_person", "hidden", 0);
		}
	},
	onload: function(frm) {
		frm.trigger("branch");
		frm.trigger("related_person_type");
	}
});
