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

    // Invoice Creation Buttons (only show if customer is linked and tenant is active)
    if (frm.doc.customer && frm.doc.status === 'Active') {
      // Create Admission Fee Invoice
      if (frm.doc.admission_fee && frm.doc.admission_fee > 0) {
        frm.add_custom_button(__('Create Admission Fee Invoice'), () => {
          create_tenant_invoice(frm, 'Tenant Admission Fee', frm.doc.admission_fee, 'Admission Fee');
        }, __('Create Invoice'));
      }

      // Create Security Deposit Invoice
      if (frm.doc.security_deposit && frm.doc.security_deposit > 0) {
        frm.add_custom_button(__('Create Security Deposit Invoice'), () => {
          create_tenant_invoice(frm, 'Tenant Security Deposit', frm.doc.security_deposit, 'Security Deposit');
        }, __('Create Invoice'));
      }

      // Create Monthly Fee Invoice
      if (frm.doc.monthly_fee && frm.doc.monthly_fee > 0) {
        frm.add_custom_button(__('Create Monthly Fee Invoice'), () => {
          create_tenant_invoice(frm, 'Tenant Monthly Fee', frm.doc.monthly_fee, 'Monthly Fee');
        }, __('Create Invoice'));
      }
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
      frappe.db.get_value('Room', frm.doc.room, ['monthly_rent', 'admission_fee', 'security_deposit', 'capacity', 'occupied_beds', 'status'], (r) => {
        frm.set_value('monthly_fee', r.monthly_rent || 0);
        frm.set_value('admission_fee', r.admission_fee || 0);
        frm.set_value('security_deposit', r.security_deposit || 0);
        
        // Check if room is full and show warning
        if (r.capacity && r.occupied_beds !== undefined) {
          const available = r.capacity - r.occupied_beds;
          if (available <= 0 && frm.doc.status === 'Active') {
            frappe.show_alert(__('Warning: This room is full. Cannot assign active tenant to a full room.'), 'red');
            frm.set_value('room', '');
          }
        }
      });
    } else {
      frm.set_value('monthly_fee', 0);
      frm.set_value('admission_fee', 0);
      frm.set_value('security_deposit', 0);
    }
  },

  status(frm) {
    // Show warning if changing from Active to other status
    if (frm.doc.status && frm.doc.status !== 'Active' && frm.doc.room) {
      frappe.db.get_value('Room', frm.doc.room, ['occupied_beds'], (r) => {
        if (r.occupied_beds > 0) {
          frappe.show_alert(__('Note: Changing status from Active will decrease room occupancy by 1'), 'yellow');
        }
      });
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

function create_tenant_invoice(frm, item_code, amount, invoice_type) {
  if (!frm.doc.customer) {
    frappe.show_alert(__('Customer must be linked to create invoices.'), 'red');
    return;
  }

  if (!frm.doc.branch) {
    frappe.show_alert(__('Branch must be selected to create invoices.'), 'red');
    return;
  }

  frappe.call({
    method: 'maddati_hms.maddati_hms.doctype.tenant.tenant.create_single_invoice',
    args: {
      tenant_name: frm.doc.name,
      item_code: item_code,
      amount: amount,
      invoice_type: invoice_type
    },
    freeze: true,
    freeze_message: __('Creating {0} Invoice...', [invoice_type]),
    callback: (r) => {
      if (r.exc) {
        frappe.show_alert(__('Error creating invoice: {0}', [r.exc]), 'red');
      } else if (r.message && r.message.success) {
        frappe.show_alert(__('{0} Invoice created successfully: {1}', [invoice_type, r.message.invoice_name]), 'green');
        // Optionally open the created invoice
        if (r.message.invoice_name) {
          frappe.set_route('Form', 'Sales Invoice', r.message.invoice_name);
        }
      } else {
        frappe.show_alert(__('Error creating invoice. Please check the console for details.'), 'red');
      }
    }
  });
}

