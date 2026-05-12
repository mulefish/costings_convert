/**
 * CIF table layout: same groups as PTS (including Total Terms), but identity columns are
 * Row + Region only (labels from usa_forwarding_cost.json → cif_regions).
 * GET /api/cif keys match this order; values are per-region averages of PTS rows sharing that Region label.
 */
const cif_meta = Object.assign(
    {
        "": {
            Row: "Row",
            Region: "Region"
        }
    },
    Object.fromEntries(
        Object.entries(pts_meta).filter(
            ([groupLabel]) =>
                groupLabel !== "" && groupLabel !== "Weslaco" && groupLabel !== "Shelby"
        )
    )
);

function getCifViewConfig() {
    const columns = [];
    const headerGroups = [];
    const columnLabels = {};

    Object.entries(cif_meta).forEach(([groupLabel, fields]) => {
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
