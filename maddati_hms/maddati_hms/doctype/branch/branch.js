frappe.ui.form.on('Branch', {
    refresh: function(frm) {
       // do nothing
    },
    branch_name: function(frm) {
        if (frm.doc.branch_name) {
            // Split branch_name into words
            let words = frm.doc.branch_name.split(/\s+/);
            let abbr = words.map(word => {
                // If word is a number, keep as is; else take first letter
                return /^\d+$/.test(word) ? word : word.charAt(0).toUpperCase();
            }).join('');
            frm.set_value('abbr', abbr);
        } else {
            frm.set_value('abbr', '');
        }
    }
});
