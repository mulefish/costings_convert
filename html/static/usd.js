/**
 * USD table layout: group label -> data column key -> header display text.
 * Data keys must match keys returned by GET /api/usd (unique keys per column).
 */
const usd_meta = {
    "": {
        Row: "Row",
        Warehouse: "Warehouse",
        Name: "Name",
        City: "City",
        State: "State",
        Region: "Region",
        Export: "Export",
        Port: "Port"
    },
    "Origin Warehouse": {
        Terms: "Terms",
        Recv: "Receiving",
        Load: "Load Out",
        Compr: "Compression",
        Class: "Class",
        Mark: "Marking",
        Strg: "Storage",
        ESO: "ESO",
        Interest: "Interest",
        "Origin Comm": "Origin Comm",
        "Total Equity": "Total Equity",
        "Total Origin": "Total Origin"
    },
    "Inland Logistics": {
        Flatbed: "Flatbed",
        "Late Fee": "Late Fee",
        "Transit Truck": "Transit Truck",
        "Total Transit": "Total Transit"
    },
    Consolidation: {
        Consol_Block: "InAndOut",
        Consol_Strg: "TotalStorage",
        Consol_Interest: "Interest",
        Total_Consol: "Total Consol"
    },
    "Outbound Logistics": {
        Dray: "Dray",
        Ocean: "Ocean base",
        Total_Out: "Total Out"
    },
    Documentation: {
        Sight_LC: "Sight LC",
        Forwarding: "Forwarding",
        Controlling: "Controlling",
        Insurance: "Insurance",
        Total_Doc: "Total Doc"
    },
    CIF: {
        Dest_Commission: "Dest Com",
        Cost_of_Funds: "CoF",
        Qclaim: "Qclaim",
        Total_CIF: "Total CIF"
    },
    Weslaco: {
        Weslaco_Transit: "Transit Truck"
    },
    Shelby: {
        Shelby_Transit: "Transit Truck"
    }
};

function getUsdViewConfig() {
    const columns = [];
    const headerGroups = [];
    const columnLabels = {};

    Object.entries(usd_meta).forEach(([groupLabel, fields]) => {
        const groupColumns = [];
        Object.entries(fields).forEach(([dataKey, headerText]) => {
            columns.push(dataKey);
            groupColumns.push(dataKey);
            columnLabels[dataKey] = headerText;
        });
        headerGroups.push({
            label: groupLabel,
            columns: groupColumns
        });
    });

    return {
        columns,
        headerGroups,
        columnLabels,
        rows: []
    };
}
