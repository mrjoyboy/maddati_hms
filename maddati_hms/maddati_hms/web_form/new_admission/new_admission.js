frappe.ready(function() {
    // Helper to apply server-side query to the Room link field
    function applyRoomQuery(branchValue) {
        const queryObj = {
            query: 'maddati_hms.custom_room_query_with_status',
            params: { branch: branchValue || null }, // used by web (autocomplete)
            filters: { branch: branchValue || null }  // used by desk (link search)
        };
        if (frappe.web_form.set_query) {
            frappe.web_form.set_query('room', () => queryObj);
        }
        try {
            const roomField = frappe.web_form.get_field('room');
            if (roomField) {
                roomField.get_query = () => queryObj;
                if (roomField.df) {
                    roomField.df.get_query = () => queryObj;
                }
            }
        } catch (e) {
            // no-op
        }
    }
    
    // Ensure query is applied on load
    if (frappe.web_form?.events?.on) {
        frappe.web_form.events.on('after_load', () => {
            applyRoomQuery(frappe.web_form.get_value('branch'));
        });
    } else {
        // Fallback: apply immediately
        applyRoomQuery(frappe.web_form.get_value('branch'));
    }
    
    // Handle branch selection
    frappe.web_form.on('branch', (field, value) => {
        frappe.web_form.set_value('room', '');
        frappe.web_form.set_value('monthly_fee', '');
        frappe.web_form.set_value('admission_fee', '');
        frappe.web_form.set_value('security_deposit', '');

        // Limit built-in Room link field to selected branch via custom server query
        applyRoomQuery(value);
    });

    // Handle room selection for monthly fee,
    frappe.web_form.on('room', (field, value) => {
        if (value) {
            frappe.call({
                method: 'maddati_hms.api.get_room_fees',
                args: { room: value },
                callback: function(r) {
                    const m = r && r.message ? r.message : {};
                    const status = (m.status || '').toLowerCase();
                    if (status === 'full' || status === 'maintenance') {
                        frappe.msgprint({
                            message: __('Selected room is not available (Status: {0}). Please choose another room.', [m.status || 'N/A']),
                            indicator: 'red'
                        });
                        // Clear selection and fees
                        frappe.web_form.set_value('room', '');
                        frappe.web_form.set_value('monthly_fee', '');
                        frappe.web_form.set_value('admission_fee', '');
                        frappe.web_form.set_value('security_deposit', '');
                        return;
                    }
                    if (m) {
                        frappe.web_form.set_value('monthly_fee', m.monthly_rent || '');
                        frappe.web_form.set_value('admission_fee', m.admission_fee || '');
                        frappe.web_form.set_value('security_deposit', m.security_deposit || '');
                    }
                }
            });
        } else {
            frappe.web_form.set_value('monthly_fee', '');
            frappe.web_form.set_value('admission_fee', '');
            frappe.web_form.set_value('security_deposit', '');
        }
    });

    // Initial load if branch is already selected
    const initialBranch = frappe.web_form.get_value('branch');
    if (initialBranch) {
        frappe.web_form.trigger('branch');
    }
});
