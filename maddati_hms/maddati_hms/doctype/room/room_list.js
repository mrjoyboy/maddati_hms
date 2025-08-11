frappe.listview_settings['Room'] = {
    get_indicator: function(doc) {
        if (doc.status === "Available") {
            return [
                `<span style='color:#21ba45;font-weight:600;'><i class='fa fa-bed' style='margin-right:4px;'></i>Available</span>`,
                "green",
                "status,=,Available"
            ];
        } else if (doc.status === "Maintenance") {
            return [
                `<span style='color:#fbbd08;font-weight:600;'><i class='fa fa-wrench' style='margin-right:4px;'></i>Maintenance</span>`,
                "yellow",
                "status,=,Maintenance"
            ];
        } else if (doc.status === "Full") {
            return [
                `<span style='color:#db2828;font-weight:600;'><i class='fa fa-ban' style='margin-right:4px;'></i>Full</span>`,
                "red",
                "status,=,Full"
            ];
        }
    }
};
