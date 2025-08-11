frappe.listview_settings['Branch'] = {
    get_indicator: function(doc) {
        if (doc.status === "Active") {
            return [
                `<span style='color:#21ba45;font-weight:600;'><i class='fa fa-building' style='margin-right:4px;'></i>Active</span>`,
                "green",
                "status,=,Active"
            ];
        } else if (doc.status === "Maintenance") {
            return [
                `<span style='color:#fbbd08;font-weight:600;'><i class='fa fa-tools' style='margin-right:4px;'></i>Maintenance</span>`,
                "yellow",
                "status,=,Maintenance"
            ];
        } else if (doc.status === "Closed") {
            return [
                `<span style='color:#db2828;font-weight:600;'><i class='fa fa-lock' style='margin-right:4px;'></i>Closed</span>`,
                "red",
                "status,=,Closed"
            ];
        }
    }
};
