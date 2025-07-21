// Copyright (c) 2025, Maddati Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student Invoice', {
  refresh(frm) {
    recalculate_total(frm);

    if (!frm.doc.__islocal) {
      if (frm.doc.outstanding_amount > 0) {
        frm.add_custom_button(__('Create Payment'), () => {
          frappe.model.open_mapped_doc({
            method: 'maddati_hms.student_invoice.make_payment_entry',
            frm: frm
          });
        }, __('Actions')).addClass('btn-primary');
      }

      frm.add_custom_button(__('Send by Email'), () => {
        frappe.call({
          method: "maddati_hms.scheduled_tasks.send_invoice_email",
          args: { invoice_name: frm.doc.name },
          callback: function(r) {
            frappe.msgprint(r.message);
          }
        });
      }, __('Actions'));
    }
  },
  student(frm) {
    if (frm.doc.student) {
      frappe.db.get_value('Student', frm.doc.student, ['student_name', 'customer'], (r) => {
        if (r) {
          frm.set_value('student_name', r.student_name);
          frm.set_value('customer', r.customer);
        }
      });
    } else {
      frm.set_value('student_name', '');
      frm.set_value('customer', '');
    }
  }
});

frappe.ui.form.on('Student Invoice Item', {
  item_code(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.item_code) {
      frappe.db.get_value('Item', row.item_code, 'standard_rate', (r) => {
        if (r && r.standard_rate != null) {
          frappe.model.set_value(cdt, cdn, 'rate', r.standard_rate);
          frappe.model.set_value(cdt, cdn, 'amount', r.standard_rate * (row.qty || 1));
          recalculate_total(frm);
        }
      });
    }
  },
  qty(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, 'amount', (row.rate || 0) * (row.qty || 0));
    recalculate_total(frm);
  },
  rate(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, 'amount', (row.rate || 0) * (row.qty || 0));
    recalculate_total(frm);
  },
  amount(frm, cdt, cdn) {
    recalculate_total(frm);
  },
  fee_items_remove(frm) {
    recalculate_total(frm);
  }
});

function recalculate_total(frm) {
  let total = 0;
  (frm.doc.fee_items || []).forEach(row => {
    total += flt(row.amount);
  });
  frm.set_value('total_amount', total);
  if (frm.doc.docstatus === 0) {
    frm.set_value('outstanding_amount', total);
  }
}
