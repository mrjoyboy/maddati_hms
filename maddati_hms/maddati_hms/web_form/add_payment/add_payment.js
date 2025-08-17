frappe.ready(function() {
	// Initialize the form
	initializePaymentForm();
	
	// Auto-populate customer data with delay to ensure fields are ready
	setTimeout(function() {
		populateCustomerData();
	}, 1000);
	
	// Set up invoice filtering after customer data is populated
	setTimeout(function() {
		setupInvoiceFilter();
	}, 2000);
});

function initializePaymentForm() {
	console.log("Initializing Add Payment Form...");
	
	// Set default values
	setDefaultValues();
	
	// Make customer fields read-only
	makeCustomerFieldsReadOnly();
	
	// Disable invoice field initially
	disableInvoiceField();
	
	// Set up invoice change handler
	setupInvoiceChangeHandler();
}

function setDefaultValues() {
	// Set default payment date to today
	if (frappe.web_form.get_field('payment_date')) {
		frappe.web_form.set_value('payment_date', frappe.datetime.get_today());
	}
	
	// Set default payment type to Receive
	if (frappe.web_form.get_field('payment_type')) {
		frappe.web_form.set_value('payment_type', 'Receive');
	}
	
	// Set default status to Pending
	if (frappe.web_form.get_field('status')) {
		frappe.web_form.set_value('status', 'Pending');
	}
}

function makeCustomerFieldsReadOnly() {
	// Make fields read-only that customers shouldn't edit
	const readOnlyFields = [
		'branch', 'room', 'tenant', 'company', 'linked_customer'
	];
	
	readOnlyFields.forEach(fieldname => {
		const field = frappe.web_form.get_field(fieldname);
		if (field) {
			field.df.read_only = 1;
			field.df.hidden = 0;
			field.refresh();
		}
	});
}

function disableInvoiceField() {
	const invoiceField = frappe.web_form.get_field('invoice');
	if (invoiceField) {
		invoiceField.df.read_only = 1;
		invoiceField.df.hidden = 0;
		invoiceField.refresh();
		
		// Add a placeholder or message
		if (invoiceField.df.placeholder) {
			invoiceField.df.placeholder = "Loading your invoices...";
		}
		invoiceField.refresh();
		
		console.log("Invoice field disabled initially");
	}
}

function enableInvoiceField() {
	const invoiceField = frappe.web_form.get_field('invoice');
	if (invoiceField) {
		invoiceField.df.read_only = 0;
		invoiceField.df.hidden = 0;
		
		// Restore original placeholder or set a helpful one
		if (invoiceField.df.placeholder) {
			invoiceField.df.placeholder = "Select an invoice to pay...";
		}
		
		invoiceField.refresh();
		
		console.log("Invoice field enabled");
		frappe.show_alert("Invoice field is now ready. Please select an invoice to pay.", 3);
	}
}

function setupInvoiceChangeHandler() {
	// Set up event listener for invoice field changes
	const invoiceField = frappe.web_form.get_field('invoice');
	if (invoiceField) {
		// Listen for changes on the invoice field
		invoiceField.$input.on('change', function() {
			const selectedInvoice = frappe.web_form.get_value('invoice');
			if (selectedInvoice) {
				console.log("Invoice selected:", selectedInvoice);
				populateAmountFromInvoice(selectedInvoice);
			} else {
				// Clear amount if no invoice is selected
				frappe.web_form.set_value('amount', '');
			}
		});
		
		console.log("Invoice change handler set up");
	}
}

function populateAmountFromInvoice(invoiceName) {
	console.log("Populating amount for invoice:", invoiceName);
	
	// Get invoice details from backend
	frappe.call({
		method: 'maddati_hms.maddati_hms.web_form.add_payment.add_payment.get_invoice_details',
		args: {
			invoice_name: invoiceName
		},
		callback: function(r) {
			console.log("Invoice details response:", r);
			
			if (r.message && !r.message.error) {
				const invoiceData = r.message;
				console.log("Invoice data received:", invoiceData);
				
				// Populate amount field with outstanding amount
				if (invoiceData.outstanding_amount) {
					frappe.web_form.set_value('amount', invoiceData.outstanding_amount);
					console.log("Amount populated:", invoiceData.outstanding_amount);
					
					// Show success message
					frappe.show_alert(`Amount set to ${frappe.format(invoiceData.outstanding_amount, 'Currency')} (outstanding amount)`, 3);
				}
				
			} else {
				console.error("Error getting invoice details:", r.message);
				frappe.show_alert("Error loading invoice details. Please try again.", 5);
			}
		}
	});
}

function populateCustomerData() {
	console.log("Starting customer data population...");
	
	// Get customer data from backend
	frappe.call({
		method: 'maddati_hms.maddati_hms.web_form.add_payment.add_payment.get_customer_data',
		callback: function(r) {
			console.log("Customer data response:", r);
			
			if (r.message && !r.message.error) {
				const data = r.message;
				console.log("Customer data received:", data);
				
				// Auto-populate fields with retry logic
				populateFieldsWithRetry(data);
				
			} else {
				console.error("Error getting customer data:", r.message);
				frappe.show_alert("Error loading your information. Please contact support.", 5);
			}
		}
	});
}

function populateFieldsWithRetry(data, retryCount = 0) {
	const maxRetries = 5;
	
	// Check if fields are available
	const fields = {
		'linked_customer': frappe.web_form.get_field('linked_customer'),
		'tenant': frappe.web_form.get_field('tenant'),
		'room': frappe.web_form.get_field('room'),
		'branch': frappe.web_form.get_field('branch'),
		'company': frappe.web_form.get_field('company')
	};
	
	console.log("Checking field availability:", Object.keys(fields).map(key => ({field: key, available: !!fields[key]})));
	console.log("Data to populate:", data);
	
	// Check if all fields are available
	const allFieldsAvailable = Object.values(fields).every(field => field !== null && field !== undefined);
	
	if (allFieldsAvailable || retryCount >= maxRetries) {
		// Populate fields
		if (data.linked_customer) {
			// Temporarily make field editable
			const linkedCustomerField = frappe.web_form.get_field('linked_customer');
			if (linkedCustomerField && linkedCustomerField.df) {
				linkedCustomerField.df.read_only = 0;
				linkedCustomerField.refresh();
			}
			
			frappe.web_form.set_value('linked_customer', data.linked_customer);
			console.log("Set linked_customer:", data.linked_customer);
			
			// Make field read-only again
			if (linkedCustomerField && linkedCustomerField.df) {
				linkedCustomerField.df.read_only = 1;
				linkedCustomerField.refresh();
			}
		} else {
			console.warn("No linked_customer data available");
		}
		
		if (data.tenant) {
			frappe.web_form.set_value('tenant', data.tenant);
			console.log("Set tenant:", data.tenant);
		} else {
			console.warn("No tenant data available");
		}
		
		if (data.room) {
			frappe.web_form.set_value('room', data.room);
			console.log("Set room:", data.room);
		} else {
			console.warn("No room data available");
		}
		
		if (data.branch) {
			frappe.web_form.set_value('branch', data.branch);
			console.log("Set branch:", data.branch);
		} else {
			console.warn("No branch data available");
		}
		
		if (data.company) {
			// Temporarily make field editable
			const companyField = frappe.web_form.get_field('company');
			if (companyField && companyField.df) {
				companyField.df.read_only = 0;
				companyField.refresh();
			}
			
			frappe.web_form.set_value('company', data.company);
			console.log("Set company:", data.company);
			
			// Make field read-only again
			if (companyField && companyField.df) {
				companyField.df.read_only = 1;
				companyField.refresh();
			}
		} else {
			console.warn("No company data available");
		}
		
		// Show success message
		frappe.show_alert("Your information has been auto-filled!", 3);
		
	} else {
		// Retry after a delay
		console.log(`Fields not ready, retrying... (${retryCount + 1}/${maxRetries})`);
		setTimeout(function() {
			populateFieldsWithRetry(data, retryCount + 1);
		}, 500);
	}
}

function setupInvoiceFilter() {
	// Get the invoice field
	const invoiceField = frappe.web_form.get_field('invoice');
	
	if (invoiceField) {
		console.log("Setting up invoice field filter using whitelist function...");
		
		// Set up the query function that uses the whitelist from __init__.py
		const queryFunction = function() {
			return {
				query: 'maddati_hms.customer_invoice_query'
			};
		};
		
		// Apply the query to the field
		if (frappe.web_form.set_query) {
			frappe.web_form.set_query('invoice', queryFunction);
		}
		
		// Also set it directly on the field
		if (invoiceField.set_query) {
			invoiceField.set_query(queryFunction);
		}
		
		// Set the get_query method on the field's df
		if (invoiceField.df) {
			invoiceField.df.get_query = queryFunction;
		}
		
		// Refresh the field to apply the filter
		invoiceField.refresh();
		
		console.log("Invoice field filter applied using whitelist function from __init__.py");
		
		// Enable the invoice field now that filtering is set up
		setTimeout(function() {
			enableInvoiceField();
		}, 500);
		
	} else {
		console.error("Invoice field not found");
	}
}

// Form submission handler
frappe.web_form.onload = function() {
	frappe.web_form.after_save = function() {
		// Show success message
		frappe.show_alert("Payment submitted successfully! Hotel staff will process your payment.", 8);
		
		// Redirect to dashboard
		setTimeout(function() {
			window.location.href = '/dashboard';
		}, 2000);
	};
};

// Basic form validation
frappe.web_form.validate = function() {
	const invoice = frappe.web_form.get_value('invoice');
	const amount = frappe.web_form.get_value('amount');
	const paymentMethod = frappe.web_form.get_value('mode_of_payment');
	
	if (!invoice) {
		frappe.msgprint("Please select an invoice to pay.");
		return false;
	}
	
	if (!amount || amount <= 0) {
		frappe.msgprint("Please enter a valid payment amount.");
		return false;
	}
	
	if (!paymentMethod) {
		frappe.msgprint("Please select a payment method.");
		return false;
	}
	
	return true;
};