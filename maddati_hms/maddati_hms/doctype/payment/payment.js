// Copyright (c) 2025, Maddati Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment', {
	invoice(frm) {
		if (frm.doc.invoice) {
			frappe.db.get_doc('Student Invoice', frm.doc.invoice).then(invoice => {
				frm.set_value('student', invoice.student);
				frm.set_value('amount', invoice.outstanding_amount);
			});
		}
	},
	amount: function(frm) {
		if (frm.doc.amount) {
			frm.set_value("amt_in_float", parseFloat(frm.doc.amount));
		} else {
			frm.set_value("amt_in_float", null);
		}
	},
	onload: function(frm) {
		if (frm.doc.amount) {
			frm.set_value("amt_in_float", parseFloat(frm.doc.amount));
		}
	}
});
