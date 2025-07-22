frappe.ui.form.on('Branch', {
    refresh: function(frm) {
        // Disable abbr if document is saved (not new)
        if (!frm.is_new()) {
            frm.set_df_property('abbr', 'read_only', 1);
        }
    }
});
