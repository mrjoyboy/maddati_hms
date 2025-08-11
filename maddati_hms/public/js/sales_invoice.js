frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {
        // Any refresh logic can go here
    },
    
    customer(frm) {
        // When customer is selected, automatically set the company
        if (frm.doc.customer) {
            frappe.call({
                method: 'maddati_hms.api.get_customer_company',
                args: { customer: frm.doc.customer },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('company', r.message);
                        frm.refresh_field('company');
                    }
                }
            });
        }
    }
}); 