frappe.listview_settings['Tenant'] = {
    get_indicator: function(doc) {
        if (doc.status === "Active") {
            return [
                `<span style='color:#21ba45;font-weight:600;'><i class='fa fa-user-check' style='margin-right:4px;'></i>Active</span>`,
                "green",
                "status,=,Active"
            ];
        } else if (doc.status === "Left") {
            return [
                `<span style='color:#db2828;font-weight:600;'><i class='fa fa-user-minus' style='margin-right:4px;'></i>Left</span>`,
                "red",
                "status,=,Left"
            ];
        } else if (doc.status === "Pending") {
            return [
                `<span style='color:#2185d0;font-weight:600;'><i class='fa fa-hourglass-half' style='margin-right:4px;'></i>Pending</span>`,
                "blue",
                "status,=,Pending"
            ];
        } else if (doc.status === "Rejected") {
            return [
                `<span style='color:#767676;font-weight:600;'><i class='fa fa-user-slash' style='margin-right:4px;'></i>Rejected</span>`,
                "gray",
                "status,=,Rejected"
            ];
        }
    }
};
