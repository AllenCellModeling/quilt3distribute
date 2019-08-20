#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
aics/pipeline_integrated_cell distribution

This script will take the output of the AICS Pipeline 4 Query and package and distribute it using `quilt3`.
"""

import pandas as pd
from lkaccess import LabKey, contexts

from quilt3distribute import Dataset
from quilt3distribute.validation import validate

# Step 1:
# Pull the data
lk = LabKey(contexts.PROD)
raw = lk.dataset.get_pipeline_4_production_cells()
raw = pd.DataFrame(raw)

# Step 2:
# Drop any columns we don't want to send out
raw = raw.drop(
    ['MembraneContourFileId', 'MembraneContourFilename', 'MembraneSegmentationFileId',
     'MembraneSegmentationFilename', 'NucleusContourFileId', 'NucleusContourFilename',
     'NucleusSegmentationFileId', 'NucleusSegmentationFilename', 'SourceFileId',
     'SourceFilename', 'StructureContourFileId', 'StructureContourFilename',
     'StructureSegmentationFileId', 'StructureSegmentationFilename'],
    axis=1
)

# Optional:
# Add extra metadata that isn't found in the database
grouped = raw.groupby("FOVId")

# This will create a dataframe that has cell id and the fully resolved feature explorer link for all cells in the fov
cell_id_to_fov_id_fe_link = []
for key, rows in grouped.groups.items():
    # Get the full rows from the dataframe for the group
    rows = raw.loc[rows]

    # Collect the cell ids
    cell_ids = list(rows["CellId"])

    # Create the feature explorer link for the entire FOV
    fe_cell_selections = "&".join([f"selectedPoint[{i}]={c_id}" for i, c_id in enumerate(cell_ids)])
    fe_link = f"https://cfe.allencell.org/?{fe_cell_selections}"

    # Create rows of cell id to the entire FOV feature explorer link
    for cell_id in cell_ids:
        cell_id_to_fov_id_fe_link.append({"CellId": cell_id, "FeatureExplorerURL": fe_link})

# Create dataframe from rows
cell_id_to_fov_id_fe_link = pd.DataFrame(cell_id_to_fov_id_fe_link)

# Merge the dataframes into one
raw = raw.merge(cell_id_to_fov_id_fe_link, left_on="CellId", right_on="CellId", suffixes=("_raw", "_fe_link"))

# Step 3:
# Validate and prune the raw data
# We shouldn't lose any rows here but we are doing this as a safety measure
cleaned = validate(raw, drop_on_error=True)
print(f"Dropped {len(raw) - len(cleaned.data)} rows during validation.")

# Step 4:
# Send to dataset object for package construction
ds = Dataset(cleaned.data, "Pipeline Integrated Cell", "aics", "readme.md")

# Step 5:
# Add a license
ds.add_license("https://www.allencell.org/terms-of-use.html")

# Indicate column values to use for file metadata
ds.set_metadata_columns([
    "CellId", "CellIndex", "CellLine", "NucMembSegmentationAlgorithm",
    "NucMembSegmentationAlgorithmVersion", "FOVId", "Gene", "PlateId", "WellId",
    "ProteinDisplayName", "StructureDisplayName", "Workflow", "FeatureExplorerURL"
])

# Set produced package directory naming
ds.set_column_names_map({
    "MembraneContourReadPath": "membrane_contours",
    "MembraneSegmentationReadPath": "membrane_segmentations",
    "NucleusContourReadPath": "dna_contours",
    "NucleusSegmentationReadPath": "dna_segmentations",
    "SourceReadPath": "fovs",
    "StructureContourReadPath": "structure_contours",
    "StructureSegmentationReadPath": "structure_segmentations"
})

# Step 6:
# Distribute the package
ds.distribute(
    push_uri="s3://allencell",
    message="Update feature explorer links"
)

print("-" * 80)
print("COMPLETE")
