frappe.ui.form.on('Tenant', {
  refresh(frm) {
    // ensure branch and room are editable
    frm.set_df_property('branch', 'read_only', 0);
    frm.set_df_property('room', 'read_only', 0);

    // Create/Link Customer action
    frm.add_custom_button(__('Create Customer'), () => {
      if (!frm.doc.name) return;
      
      // Check if tenant status is Active
      if (frm.doc.status !== 'Active') {
        frappe.show_alert({ 
          message: __('Customer can only be created for Active tenants. Current status: {0}', [frm.doc.status || 'Not Set']), 
          indicator: 'red' 
        });
        return;
      }
      

      
      frappe.call({
        method: 'maddati_hms.maddati_hms.doctype.tenant.tenant.create_or_link_customer',
        args: { tenant: frm.doc.name },
        freeze: true,
        freeze_message: __('Linking Customer...'),
        callback: (r) => {
          const m = r && r.message;
          if (m && m.customer) {
            frm.set_value('customer', m.customer);
            frm.refresh_field('customer');
            frm.save();
            frm.refresh();
          }
        }
      });
    }, __('Actions'));

    // Unlink Customer action (only show if customer is linked)
    if (frm.doc.customer) {
      frm.add_custom_button(__('Unlink Customer'), () => {
        if (!frm.doc.name) return;
        
        frappe.confirm(
          __('Are you sure you want to unlink Customer "{0}" from this Tenant?', [frm.doc.customer]),
          () => {
            frappe.call({
              method: 'maddati_hms.maddati_hms.doctype.tenant.tenant.unlink_customer',
              args: { tenant: frm.doc.name },
              freeze: true,
              freeze_message: __('Unlinking Customer...'),
              callback: (r) => {
                const m = r && r.message;
                if (m && m.success) {
                  frm.set_value('customer', '');
                  frm.refresh_field('customer');
                  frm.save();
                  frm.refresh();
                }
              }
            });
          },
          () => {
            // User cancelled
          }
        );
      }, __('Actions'));
    }
  },

  onload(frm) {
    // Link Room list to selected Branch with custom server query
    frm.fields_dict.room.get_query = () => ({
      filters: { branch: frm.doc.branch },
      query: 'maddati_hms.custom_room_query_with_status'
    });

    // Filter Extra Services to Items in 'Tenant Extra Services' group, non-stock, enabled
    if (frm.fields_dict.extra_services && frm.fields_dict.extra_services.grid) {
      frm.fields_dict.extra_services.grid.get_field('service').get_query = () => ({
        filters: {
          item_group: 'Tenant Extra Services',
          is_stock_item: 0,
          disabled: 0
        }
      });
    }
  },

  branch(frm) {
    // reset room and reapply query when branch changes
    frm.set_value('room', null);
    frm.fields_dict.room.get_query = () => ({
      filters: { branch: frm.doc.branch },
      query: 'maddati_hms.custom_room_query_with_status'
    });
  },

  room(frm) {
    if (frm.doc.room) {
      frappe.db.get_value('Room', frm.doc.room, ['monthly_rent', 'admission_fee', 'security_deposit'], (r) => {
        frm.set_value('monthly_fee', r.monthly_rent || 0);
        frm.set_value('admission_fee', r.admission_fee || 0);
        frm.set_value('security_deposit', r.security_deposit || 0);
      });
    } else {
      frm.set_value('monthly_fee', 0);
      frm.set_value('admission_fee', 0);
      frm.set_value('security_deposit', 0);
    }
  }
});

frappe.ui.form.on('Tenant Extra Service', {
  amount(frm) {
    calculate_extra_services_fees(frm);
  },
  service(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    if (!row || !row.service) {
      calculate_extra_services_fees(frm);
      return;
    }
    // Pull standard_rate into amount (qty assumed 1); set description if empty
    frappe.db.get_value('Item', row.service, ['standard_rate', 'description', 'item_name']).then(r => {
      const v = (r && r.message) || {};
      row.amount = (v.standard_rate != null) ? v.standard_rate : (row.amount || 0);
      if (!row.description) {
        row.description = v.description || v.item_name || '';
      }
      frm.refresh_field('extra_services');
      calculate_extra_services_fees(frm);
    }).catch(() => {
      calculate_extra_services_fees(frm);
    });
  },
  extra_services_remove(frm) {
    calculate_extra_services_fees(frm);
  }
});

function calculate_extra_services_fees(frm) {
  let total = 0;
  (frm.doc.extra_services || []).forEach(row => {
    total += flt(row.amount);
  });
  frm.set_value('extra_services_fees', total);
}

