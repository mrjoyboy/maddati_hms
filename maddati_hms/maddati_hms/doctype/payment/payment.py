import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class Payment(Document):

    def on_update(self):
        """
        Handle updates to the document (but don't create Payment Entry here).
        """
        # Only log the update, don't create Payment Entry
        # frappe.msgprint(f"on_update called - Status: {self.status}, DocStatus: {self.docstatus}")
        
        # Don't create Payment Entry on update - only on submit
        # This prevents duplicate Payment Entry creation

    def on_submit(self):
        """
        Trigger Payment Entry creation when document is submitted.
        """
        # frappe.msgprint(f"on_submit called - Status: {self.status}, DocStatus: {self.docstatus}")
        
        if self.status != "Accepted":
            frappe.msgprint("Status is not 'Accepted', skipping Payment Entry creation")
            return

        if self.linked_payment_entry:
            frappe.msgprint(f"Payment Entry already exists: {self.linked_payment_entry}")
            return

        # Fetch linked customer from tenant if not set
        if self.tenant and not self.linked_customer:
            self.linked_customer = frappe.db.get_value("Tenant", self.tenant, "customer")
            self.db_set("linked_customer", self.linked_customer)
            # frappe.msgprint(f"Linked customer set to: {self.linked_customer}")

        if not self.linked_customer:
            frappe.msgprint("Linked Customer is not set. Cannot create Payment Entry.")
            return

        if not self.company:
            frappe.msgprint("Company is not set. Cannot create Payment Entry.")
            return

        if not self.amount or self.amount <= 0:
            frappe.msgprint("Received Amount is mandatory and must be greater than 0.")
            return

        # frappe.msgprint("All validations passed, creating Payment Entry...")
        self.create_payment_entry()

    def after_submit(self):
        """
        Verify Payment Entry linking after submit.
        """
        # frappe.msgprint(f"after_submit called - Linked Payment Entry: {self.linked_payment_entry}")
        
        if self.linked_payment_entry:
            # Verify the Payment Entry exists and is submitted
            if frappe.db.exists("Payment Entry", self.linked_payment_entry):
                pe_docstatus = frappe.db.get_value("Payment Entry", self.linked_payment_entry, "docstatus")
                if pe_docstatus == 1:
                    frappe.msgprint(f"✅ Payment Entry {self.linked_payment_entry} successfully linked and submitted.")
                else:
                    frappe.msgprint(f"⚠️ Warning: Payment Entry {self.linked_payment_entry} exists but is not submitted (Status: {pe_docstatus}).")
            else:
                frappe.msgprint(f"❌ Warning: Linked Payment Entry {self.linked_payment_entry} not found in database.")
        else:
            frappe.msgprint("❌ No Payment Entry linked after submit.")

    def create_payment_entry(self):
        # frappe.msgprint("create_payment_entry method called")
        
        # Get the default receivable account for the company
        paid_to_account = frappe.db.get_value("Company", self.company, "default_receivable_account")
        if not paid_to_account:
            frappe.msgprint(f"Default Receivable Account not set for Company {self.company}")
            return

        # frappe.msgprint(f"Using paid_to_account: {paid_to_account}")

        # Ensure customer is properly set
        if not self.linked_customer:
            frappe.msgprint("Customer is not set. Cannot create Payment Entry.")
            return

        # Verify customer exists
        if not frappe.db.exists("Customer", self.linked_customer):
            frappe.msgprint(f"Customer {self.linked_customer} does not exist.")
            return

        try:
            # Prepare references data for ERPNext Payment Entry
            references = []
            invoice_already_paid = False
            
            # If payment_references table has data, use it
            if hasattr(self, 'payment_references') and self.payment_references:
                for ref in self.payment_references:
                    # Check if the referenced document is already fully paid
                    if ref.reference_doctype == "Sales Invoice":
                        invoice_doc = frappe.get_doc("Sales Invoice", ref.reference_name)
                        if invoice_doc.outstanding_amount <= 0:
                            invoice_already_paid = True
                            frappe.msgprint(f"⚠️ Warning: Invoice {ref.reference_name} is already fully paid. This will be recorded as an overpayment.")
                    
                    references.append({
                        "reference_doctype": ref.reference_doctype,
                        "reference_name": ref.reference_name,
                        "total_amount": ref.total_amount,
                        "outstanding_amount": ref.outstanding_amount,
                        "allocated_amount": ref.allocated_amount
                    })
            
            # If no references from payment_references table but invoice is selected, create a reference
            if not references and self.invoice:
                # Get invoice details and verify customer matches
                invoice_doc = frappe.get_doc("Sales Invoice", self.invoice)
                
                # Verify that the invoice belongs to the same customer
                if invoice_doc.customer != self.linked_customer:
                    frappe.msgprint(f"❌ Invoice {self.invoice} belongs to customer {invoice_doc.customer}, but payment is for customer {self.linked_customer}. Please select the correct invoice.")
                    return
                
                # Check if invoice is already fully paid
                if invoice_doc.outstanding_amount <= 0:
                    invoice_already_paid = True
                    frappe.msgprint(f"⚠️ Warning: Invoice {self.invoice} is already fully paid. This will be recorded as an overpayment.")
                    # For already paid invoices, set allocated amount to 0
                    allocated_amount = 0
                else:
                    # For partial payments, allocate exactly the payment amount
                    allocated_amount = min(self.amount, invoice_doc.outstanding_amount)
                
                references.append({
                    "reference_doctype": "Sales Invoice",
                    "reference_name": self.invoice,
                    "total_amount": invoice_doc.grand_total,
                    "outstanding_amount": invoice_doc.outstanding_amount,
                    "allocated_amount": allocated_amount
                })

            # frappe.msgprint(f"References prepared: {references}")

            # Validate that total allocated amount equals payment amount
            total_allocated = sum(ref.get("allocated_amount", 0) for ref in references)
            if total_allocated != self.amount:
                # frappe.msgprint(f"⚠️ Warning: Total allocated amount ({total_allocated}) does not match payment amount ({self.amount}). Adjusting allocated amounts...")
                
                # Adjust allocated amounts to match payment amount
                for ref in references:
                    if ref.get("outstanding_amount", 0) > 0:
                        ref["allocated_amount"] = min(self.amount, ref["outstanding_amount"])
                        break

            # Create Payment Entry document with proper customer handling
            pe_data = {
                "doctype": "Payment Entry",
                "payment_type": "Receive",
                "party_type": "Customer",
                "party": self.linked_customer,
                "paid_to": paid_to_account,
                "mode_of_payment": self.mode_of_payment or "Cash",
                "posting_date": self.payment_date or nowdate(),
                "reference_no": self.reference_no,
                "paid_amount": self.amount,
                "received_amount": self.amount,
                "company": self.company,
                "references": references
            }

            # frappe.msgprint(f"Payment Entry data: {pe_data}")

            # Create and insert Payment Entry
            pe_doc = frappe.get_doc(pe_data)
            # frappe.msgprint("Payment Entry document created, inserting...")
            pe_doc.insert(ignore_permissions=True)
            # frappe.msgprint("Payment Entry inserted, submitting...")
            
            # Submit the Payment Entry with proper error handling
            try:
                pe_doc.submit()
                # frappe.msgprint("Payment Entry submitted successfully")
            except Exception as submit_error:
                frappe.msgprint(f"⚠️ Warning: Payment Entry created but could not submit: {str(submit_error)}")
                # Continue anyway as the Payment Entry exists

            # Update the linked payment entry field
            # frappe.msgprint(f"Updating linked_payment_entry field to: {pe_doc.name}")
            self.db_set("linked_payment_entry", pe_doc.name)
            
            # Log the linking for debugging
            frappe.logger().info(f"Payment Entry {pe_doc.name} linked to Payment {self.name}")
            
            if invoice_already_paid:
                frappe.msgprint(f"✅ Payment Entry {pe_doc.name} created successfully for customer {self.linked_customer}. Note: This payment includes overpayment for already settled invoices.")
            else:
                frappe.msgprint(f"✅ Payment Entry {pe_doc.name} created successfully for customer {self.linked_customer}.")

        except Exception as e:
            frappe.msgprint(f"❌ Failed to create Payment Entry: {str(e)}")
            frappe.log_error(f"Payment Entry Creation Error: {str(e)}", "Payment Entry Creation Failed")
            
            # If the error is about customer validation, try to provide more specific guidance
            if "Customer is required" in str(e):
                frappe.msgprint("💡 Tip: This error usually occurs when the customer field is not properly set. Please ensure the tenant has a customer linked.")

    def suppress_customer_validation_error(self):
        """
        Suppress the specific customer validation error message that appears after Payment Entry creation.
        This method can be called to prevent the "Customer is required" message from showing.
        """
        # This is a placeholder method to suppress the error message
        # The actual suppression happens in the JavaScript
        pass
