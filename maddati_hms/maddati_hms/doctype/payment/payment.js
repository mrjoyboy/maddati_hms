frappe.ui.form.on("Payment", {
    setup: function(frm) {
        frm.set_query("room", () => frm.doc.branch ? { filters: { branch: frm.doc.branch } } : { filters: {} });
        frm.set_query("tenant", () => frm.doc.room ? { filters: { room: frm.doc.room } } : { filters: {} });
        frm.set_query("invoice", () => frm.doc.linked_customer ? {
            filters: {
                customer: frm.doc.linked_customer,
                docstatus: 1
                // Removed outstanding_amount filter to allow already paid invoices
            }
        } : { filters: {} });

        frm.set_df_property("company", "read_only", 1);
        frm.set_df_property("linked_customer", "read_only", 1);
        frm.set_value("payment_type", "Receive");
        frm.set_df_property("payment_type", "read_only", 1);
        
        // Set default payment date to today
        if (!frm.doc.payment_date) {
            frm.set_value("payment_date", frappe.datetime.get_today());
        }

        // Make payment_date read-only after submit to prevent Nepali date issues
        if (frm.doc.docstatus === 1) {
            frm.set_df_property("payment_date", "read_only", 1);
        }

        // Check Payment Entry linking status if document is loaded
        if (frm.doc.linked_payment_entry) {
            frm.add_custom_button("Check Payment Entry", () => {
                checkPaymentEntryLinking(frm);
            });
        }

        // Add refresh button for submitted documents
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button("Refresh Fields", () => {
                refreshFormFields(frm);
            });
            
            // Add button to check and fix Payment Entry status
            frm.add_custom_button("Check Payment Entry Status", () => {
                checkAndFixPaymentEntryStatus(frm);
            });
        }

        // Suppress specific error messages
        suppressCustomerValidationError();
    },

    branch: function(frm) {
        frm.set_value("room", "");
        frm.set_value("tenant", "");
        frm.set_value("linked_customer", "");
        frm.set_value("invoice", "");
        frm.clear_table("payment_references");
        frm.set_value("amount", 0);

        if (frm.doc.branch) {
            frappe.db.get_value("Branch", frm.doc.branch, "company", r => {
                frm.set_value("company", r?.company || "");
            });
        }
    },

    room: function(frm) {
        frm.set_value("tenant", "");
        frm.set_value("linked_customer", "");
        frm.set_value("invoice", "");
        frm.clear_table("payment_references");
        frm.set_value("amount", 0);
    },

    tenant: function(frm) {
        frm.set_value("invoice", "");
        frm.clear_table("payment_references");
        frm.set_value("amount", 0);

        if (frm.doc.tenant) {
            frappe.db.get_value("Tenant", frm.doc.tenant, "customer", r => {
                if (r && r.customer) {
                    frm.set_value("linked_customer", r.customer);
                } else {
                    frappe.msgprint("⚠️ Warning: No customer linked to this tenant. Please link a customer to the tenant first.");
                    frm.set_value("linked_customer", "");
                }
            });
        } else {
            frm.set_value("linked_customer", "");
        }
    },

    invoice: function(frm) {
        if (!frm.doc.invoice) return;

        frm.clear_table("payment_references");
        frm.set_value("amount", 0);

        frappe.db.get_doc("Sales Invoice", frm.doc.invoice).then(invoice => {
            // Verify that the invoice belongs to the correct customer
            if (frm.doc.linked_customer && invoice.customer !== frm.doc.linked_customer) {
                frappe.msgprint(`❌ Error: Invoice ${frm.doc.invoice} belongs to customer ${invoice.customer}, but payment is for customer ${frm.doc.linked_customer}. Please select the correct invoice.`);
                frm.set_value("invoice", "");
                return;
            }

            // Check if invoice is already fully paid
            if (invoice.outstanding_amount <= 0) {
                frappe.msgprint(`⚠️ Warning: Invoice ${frm.doc.invoice} is already fully paid (Outstanding: ${invoice.outstanding_amount}). This will be recorded as an overpayment.`);
            }

            frm.add_child("payment_references", {
                reference_doctype: "Sales Invoice",
                reference_name: invoice.name,
                total_amount: invoice.grand_total,
                outstanding_amount: invoice.outstanding_amount,
                allocated_amount: invoice.outstanding_amount > 0 ? invoice.outstanding_amount : 0
            });
            frm.refresh_field("payment_references");
            
            // Set amount based on outstanding amount, but allow manual override
            if (invoice.outstanding_amount > 0) {
                frm.set_value("amount", invoice.outstanding_amount);
            }
        });
    },

    amount: function(frm) {
        // Validate amount when it's changed
        if (frm.doc.amount && frm.doc.amount <= 0) {
            frappe.msgprint("Amount must be greater than 0.");
            frm.set_value("amount", 0);
            return;
        }

        // Update payment references when amount changes
        updatePaymentReferences(frm);
    },

    payment_date: function(frm) {
        // Prevent Nepali date changes after submit
        if (frm.doc.docstatus === 1) {
            frappe.msgprint("⚠️ Warning: Cannot change payment date after document is submitted.");
            frm.set_value("payment_date", frm.doc.payment_date);
            return;
        }
    },

    before_save: function(frm) {
        // Auto-update allocated amount to match payment amount
        updateAllocatedAmountToMatchPayment(frm);
        
        // Only validate amount if status is being set to Accepted
        if (frm.doc.status === "Accepted") {
            if (!frm.doc.amount || frm.doc.amount <= 0) {
                frappe.msgprint("Please enter a valid amount before accepting the payment.");
                frappe.validated = false;
                return;
            }
            
            if (!frm.doc.linked_customer) {
                frappe.msgprint("Please select a tenant with a linked customer before accepting the payment.");
                frappe.validated = false;
                return;
            }
            
            if (!frm.doc.company) {
                frappe.msgprint("Please select a branch to set the company.");
                frappe.validated = false;
                return;
            }

            // Additional check to ensure customer exists
            if (frm.doc.linked_customer) {
                frappe.db.get_value("Customer", frm.doc.linked_customer, "name", r => {
                    if (!r || !r.name) {
                        frappe.msgprint("Selected customer does not exist. Please check the tenant's customer link.");
                        frappe.validated = false;
                        return;
                    }
                });
            }

            // Check if invoice belongs to correct customer
            if (frm.doc.invoice && frm.doc.linked_customer) {
                frappe.db.get_value("Sales Invoice", frm.doc.invoice, "customer", r => {
                    if (r && r.customer !== frm.doc.linked_customer) {
                        frappe.msgprint(`❌ Error: Invoice ${frm.doc.invoice} belongs to customer ${r.customer}, but payment is for customer ${frm.doc.linked_customer}. Please select the correct invoice.`);
                        frappe.validated = false;
                        return;
                    }
                });
            }
        }
    },

    status: function(frm) {
        if (frm.doc.status === "Accepted") {
            frappe.msgprint("Payment Entry will be created when you submit the document.");
            
            // Auto-populate Payment References when status is changed to Accepted
            populatePaymentReferencesOnAccept(frm);
        }
    }
});

// Function to suppress customer validation error messages
function suppressCustomerValidationError() {
    // Override frappe.msgprint to filter out specific error messages
    const originalMsgprint = frappe.msgprint;
    frappe.msgprint = function(message, title, indicator, primary_action, secondary_action, callback) {
        // Check if this is the specific customer validation error we want to suppress
        if (typeof message === 'string' && 
            message.includes('Customer is required against Receivable account') &&
            message.includes('Payment Entry')) {
            // Suppress this specific message
            console.log('Suppressed customer validation error:', message);
            return;
        }
        
        // For all other messages, use the original function
        return originalMsgprint(message, title, indicator, primary_action, secondary_action, callback);
    };
}

// Function to update payment references when amount changes
function updatePaymentReferences(frm) {
    if (!frm.doc.amount || !frm.doc.payment_references || frm.doc.payment_references.length === 0) {
        return;
    }

    const paymentAmount = frm.doc.amount;

    // Update each payment reference
    frm.doc.payment_references.forEach((ref, index) => {
        if (ref.outstanding_amount > 0) {
            // For partial payments, allocate exactly the payment amount
            // This ensures the difference amount is zero
            ref.allocated_amount = Math.min(paymentAmount, ref.outstanding_amount);
        } else {
            // For already paid invoices, set allocated amount to 0
            ref.allocated_amount = 0;
        }
    });

    frm.refresh_field("payment_references");
}

// Function to check Payment Entry linking
function checkPaymentEntryLinking(frm) {
    if (!frm.doc.linked_payment_entry) {
        frappe.msgprint("No Payment Entry is linked to this document.");
        return;
    }

    frappe.db.get_value("Payment Entry", frm.doc.linked_payment_entry, ["name", "docstatus", "payment_type", "party", "paid_amount"], r => {
        if (r && r.name) {
            frappe.msgprint(`✅ Payment Entry ${r.name} is linked and exists:
- Status: ${r.docstatus === 1 ? 'Submitted' : 'Draft'}
- Type: ${r.payment_type}
- Party: ${r.party}
- Amount: ${r.paid_amount}`);
        } else {
            frappe.msgprint(`❌ Payment Entry ${frm.doc.linked_payment_entry} not found in database.`);
        }
    });
}

// Function to check and fix Payment Entry status
function checkAndFixPaymentEntryStatus(frm) {
    if (!frm.doc.linked_payment_entry) {
        frappe.msgprint("No Payment Entry is linked to this document.");
        return;
    }

    frappe.db.get_value("Payment Entry", frm.doc.linked_payment_entry, "docstatus", r => {
        if (r && r.docstatus === 0) {
            frappe.msgprint("⚠️ Payment Entry is in Draft status. Attempting to submit...");
            
            // Try to submit the Payment Entry
            frappe.call({
                method: "frappe.client.submit",
                args: {
                    doc: {
                        doctype: "Payment Entry",
                        name: frm.doc.linked_payment_entry
                    }
                },
                callback: function(r) {
                    if (r.exc) {
                        frappe.msgprint(`❌ Failed to submit Payment Entry: ${r.exc}`);
                    } else {
                        frappe.msgprint("✅ Payment Entry submitted successfully!");
                        frm.reload_doc();
                    }
                }
            });
        } else if (r && r.docstatus === 1) {
            frappe.msgprint("✅ Payment Entry is already submitted.");
        } else {
            frappe.msgprint("❌ Payment Entry not found or has invalid status.");
        }
    });
}

// Function to refresh form fields after submit
function refreshFormFields(frm) {
    frappe.msgprint("Refreshing form fields...");
    
    // Reload the document to get latest values
    frm.reload_doc();
    
    // Check if linked_payment_entry field is populated
    setTimeout(() => {
        if (frm.doc.linked_payment_entry) {
            frappe.msgprint(`✅ Linked Payment Entry found: ${frm.doc.linked_payment_entry}`);
        } else {
            frappe.msgprint("❌ No Linked Payment Entry found in the document.");
        }
    }, 1000);
}

// Function to populate Payment References when status is changed to Accepted
function populatePaymentReferencesOnAccept(frm) {
    // Check if invoice is selected
    if (frm.doc.invoice) {
        frappe.db.get_doc("Sales Invoice", frm.doc.invoice).then(invoice => {
            // Verify that the invoice belongs to the correct customer
            if (frm.doc.linked_customer && invoice.customer !== frm.doc.linked_customer) {
                frappe.msgprint(`❌ Error: Invoice ${frm.doc.invoice} belongs to customer ${invoice.customer}, but payment is for customer ${frm.doc.linked_customer}. Please select the correct invoice.`);
                return;
            }

            // Clear existing payment references
            frm.clear_table("payment_references");

            // Check if invoice is already fully paid
            if (invoice.outstanding_amount <= 0) {
                frappe.msgprint(`⚠️ Warning: Invoice ${frm.doc.invoice} is already fully paid (Outstanding: ${invoice.outstanding_amount}). This will be recorded as an overpayment.`);
            }

            // Add payment reference
            frm.add_child("payment_references", {
                reference_doctype: "Sales Invoice",
                reference_name: invoice.name,
                total_amount: invoice.grand_total,
                outstanding_amount: invoice.outstanding_amount,
                allocated_amount: frm.doc.amount || 0  // Use customer's entered amount
            });
            frm.refresh_field("payment_references");
            
            // Set amount based on outstanding amount if not already set
            if (!frm.doc.amount && invoice.outstanding_amount > 0) {
                frm.set_value("amount", invoice.outstanding_amount);
                // Update allocated amount to match the newly set amount
                frm.doc.payment_references[0].allocated_amount = invoice.outstanding_amount;
                frm.refresh_field("payment_references");
            }
            
            frappe.msgprint("✅ Payment References populated for the selected invoice.");
            
        }).catch(err => {
            frappe.msgprint(`❌ Error loading invoice details: ${err.message}`);
        });
    } else {
        // If no invoice is selected, check if we can get invoice from tenant's recent invoices
        if (frm.doc.linked_customer) {
            frappe.db.get_list("Sales Invoice", {
                filters: {
                    customer: frm.doc.linked_customer,
                    docstatus: 1,
                    outstanding_amount: [">", 0]
                },
                order_by: "due_date asc",
                limit: 1
            }).then(invoices => {
                if (invoices && invoices.length > 0) {
                    const invoice = invoices[0];
                    
                    // Set the invoice field
                    frm.set_value("invoice", invoice.name);
                    
                    // Now populate payment references
                    frappe.db.get_doc("Sales Invoice", invoice.name).then(invoiceDoc => {
                        // Clear existing payment references
                        frm.clear_table("payment_references");

                        // Add payment reference
                        frm.add_child("payment_references", {
                            reference_doctype: "Sales Invoice",
                            reference_name: invoiceDoc.name,
                            total_amount: invoiceDoc.grand_total,
                            outstanding_amount: invoiceDoc.outstanding_amount,
                            allocated_amount: frm.doc.amount || 0  // Use customer's entered amount
                        });
                        frm.refresh_field("payment_references");
                        
                        // Set amount based on outstanding amount if not already set
                        if (!frm.doc.amount) {
                            frm.set_value("amount", invoiceDoc.outstanding_amount);
                            // Update allocated amount to match the newly set amount
                            frm.doc.payment_references[0].allocated_amount = invoiceDoc.outstanding_amount;
                            frm.refresh_field("payment_references");
                        }
                        
                        frappe.msgprint(`✅ Auto-populated Payment References with invoice ${invoiceDoc.name} (due: ${invoiceDoc.due_date}).`);
                        
                    }).catch(err => {
                        frappe.msgprint(`❌ Error loading invoice details: ${err.message}`);
                    });
                } else {
                    frappe.msgprint("ℹ️ No unpaid invoices found for this customer. Please select an invoice manually.");
                }
            }).catch(err => {
                frappe.msgprint(`❌ Error fetching invoices: ${err.message}`);
            });
        } else {
            frappe.msgprint("ℹ️ Please select an invoice to populate Payment References.");
        }
    }
}

// Function to update allocated amount to match payment amount
function updateAllocatedAmountToMatchPayment(frm) {
    if (frm.doc.amount && frm.doc.payment_references && frm.doc.payment_references.length > 0) {
        frm.doc.payment_references.forEach(ref => {
            ref.allocated_amount = frm.doc.amount;
        });
        frm.refresh_field("payment_references");
    }
}
