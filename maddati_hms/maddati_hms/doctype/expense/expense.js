// Copyright (c) 2025, Maddati Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on('Expense', {
    refresh: function(frm) {
        frm.toggle_display('staff', frm.doc.expense_for === 'Salary' || frm.doc.expense_for === 'Bonus');
        frm.toggle_display('paid_to', !(frm.doc.expense_for === 'Salary' || frm.doc.expense_for === 'Bonus'));
    },
    expense_for: function(frm) {
        frm.toggle_display('staff', frm.doc.expense_for === 'Salary' || frm.doc.expense_for === 'Bonus');
        frm.toggle_display('paid_to', !(frm.doc.expense_for === 'Salary' || frm.doc.expense_for === 'Bonus'));
        // Clear amount if switching to Bonus
        if(frm.doc.expense_for === 'Bonus') {
            frm.set_value('amount', null);
        }
    },
    staff: function(frm) {
        if((frm.doc.expense_for === 'Salary' || frm.doc.expense_for === 'Bonus') && frm.doc.staff) {
            frappe.db.get_value('Staff', frm.doc.staff, ['salary', 'branch'], function(r) {
                if(r) {
                    if(frm.doc.expense_for === 'Salary') {
                        frm.set_value('amount', r.salary !== undefined ? r.salary : null);
                    }
                    frm.set_value('branch', r.branch || null);
                } else {
                    if(frm.doc.expense_for === 'Salary') {
                        frm.set_value('amount', null);
                    }
                    frm.set_value('branch', null);
                }
            });
        } else {
            frm.set_value('amount', null);
            frm.set_value('branch', null);
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
