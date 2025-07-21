frappe.ui.form.on('Tenant', {
  refresh(frm) {
    if (!frm.doc.__islocal) {
      // Create Tenant Portal button (placeholder)
      frm.add_custom_button(__('Create Tenant Portal'), () => {
        frappe.msgprint(__('Tenant Portal creation coming soon.'));
      }, __('Actions'));
    }
  },

  onload(frm) {
    frm.fields_dict.room.get_query = () => ({
      filters: { branch: frm.doc.branch },
      query: 'maddati_hms.custom_room_query_with_status'
    });
  },

  branch(frm) {
    frm.set_value('room', null);
    frm.fields_dict.room.get_query = () => ({
      filters: { branch: frm.doc.branch },
      query: 'maddati_hms.custom_room_query_with_status'
    });
  },

  room(frm) {
    if (frm.doc.room) {
      frappe.db.get_value('Room', frm.doc.room, 'price', (r) => {
        frm.set_value('monthly_fee', r.price || 0);
      });
    } else {
      frm.set_value('monthly_fee', 0);
    }
  },

  extra_services_add(frm) {
    setTimeout(() => calculate_extra_services_fees(frm), 100);
  },

  extra_services_remove(frm) {
    calculate_extra_services_fees(frm);
  },

  extra_services_amount(frm, cdt, cdn) {
    calculate_extra_services_fees(frm);
  },

  extra_services_edit(frm) {
    calculate_extra_services_fees(frm);
  }
});

frappe.ui.form.on('Tenant Extra Service', {
  amount(frm) {
    calculate_extra_services_fees(frm);
  },
  service(frm) {
    calculate_extra_services_fees(frm);
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
