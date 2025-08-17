frappe.ui.form.on("Room", {
onload(frm) {
    // Only set prefix if branch is selected and doc is new
    if (frm.doc.branch && frm.is_new()) {
        frm.trigger("branch");
    }
},

refresh(frm) {
    // Add button to show active tenants in this room
    if (frm.doc.name) {
        frm.add_custom_button(__('Show Active Tenants'), () => {
            show_active_tenants_in_room(frm.doc.name);
        }, __('Tenants'));
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
},

capacity(frm) {
    // Update status based on capacity and occupied_beds
    if (frm.doc.capacity && frm.doc.occupied_beds !== undefined) {
        if (frm.doc.occupied_beds >= frm.doc.capacity) {
            frm.set_value("status", "Full");
        } else {
            frm.set_value("status", "Available");
        }
    }
},

occupied_beds(frm) {
    // Update status based on capacity and occupied_beds
    if (frm.doc.capacity && frm.doc.occupied_beds !== undefined) {
        if (frm.doc.occupied_beds >= frm.doc.capacity) {
            frm.set_value("status", "Full");
        } else {
            frm.set_value("status", "Available");
        }
    }
}
});

// Trigger room_type logic only when room_type field is changed

function show_active_tenants_in_room(room_name) {
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Tenant',
            filters: {
                room: room_name,
                status: 'Active'
            },
            fields: ['name', 'tenant_name', 'email', 'contact_number', 'admission_date']
        },
        callback: (r) => {
            if (r.message && r.message.length > 0) {
                let content = `
                    <div style="padding: 15px;">
                        <h4>${__('Active Tenants in Room')}</h4>
                        <table class="table table-bordered">
                            <thead>
                                <tr>
                                    <th>${__('Tenant ID')}</th>
                                    <th>${__('Name')}</th>
                                    <th>${__('Email')}</th>
                                    <th>${__('Contact')}</th>
                                    <th>${__('Admission Date')}</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                
                r.message.forEach(tenant => {
                    content += `
                        <tr>
                            <td><a href="/app/tenant/${tenant.name}" target="_blank">${tenant.name}</a></td>
                            <td>${tenant.tenant_name || ''}</td>
                            <td>${tenant.email || ''}</td>
                            <td>${tenant.contact_number || ''}</td>
                            <td>${tenant.admission_date || ''}</td>
                        </tr>
                    `;
                });
                
                content += `
                            </tbody>
                        </table>
                        <p><strong>${__('Total Active Tenants')}: ${r.message.length}</strong></p>
                    </div>
                `;
                
                const d = new frappe.ui.Dialog({
                    title: __('Active Tenants - {0}', [room_name]),
                    size: 'large',
                    fields: [{
                        fieldtype: 'HTML',
                        options: content
                    }]
                });
                d.show();
            } else {
                frappe.show_alert(__('No active tenants found in this room'), 'blue');
            }
        }
    });
}
