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
lk = LabKey(host=contexts.PROD)
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

# Step 3:
# Validate and prune the raw data
# We shouldn't lose any rows here but we are doing this as a safety measure
cleaned = validate(raw, drop_on_error=True)
print(f"Dropped {len(raw) - len(cleaned)} rows during validation.")

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
    "ProteinDisplayName", "StructureDisplayName", "Workflow"
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
    push_uri="s3://quilt-aics",
    message="Switched to Quilt3Distribute. Metadata structure updated."
)
