#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
aics/pipeline_integrated_single_cell distribution

This script will take the output of the AICS `single_cell_pipeline` and package and distribute it using `quilt3`.
"""

from pathlib import Path

import pandas as pd

from quilt3distribute import Dataset
from quilt3distribute.validation import validate

# Step 1:
# Import the data
# Using pathlib here to verify that we have a valid target and to resolve any path issues
scp_output_dir = Path("/allen/aics/modeling/gregj/results/ipp/scp_19_06_05/").resolve(strict=True)
scp_manifest = (scp_output_dir / "data_jobs_out.csv").resolve(strict=True)
raw = pd.read_csv(scp_manifest)

# Step 2:
# Drop any columns that are filled with filepaths that we don't want to send out at this time
# In this case, it is because that data is available in a more production form from `aics/pipeline_integrated_cell`
# In the future these columns will likely be kept in on a script the sends out the entire pipeline. So that we don't
# have to split up single cell and full field packages.
raw = raw.drop([
    "MembraneContourReadPath", "MembraneContourFilename", "MembraneSegmentationReadPath",
    "MembraneSegmentationFilename", "NucleusContourReadPath", "NucleusContourFilename",
    "NucleusSegmentationReadPath", "NucleusSegmentationFilename", "SourceReadPath",
    "SourceFilename", "StructureContourReadPath", "StructureContourFilename",
    "StructureSegmentationReadPath", "StructureSegmentationFilename", "save_dir"
], axis=1)


# Optional:
# Add extra metadata that isn't found in the database
def create_feature_explorer_url(row):
    return "https://www.allencell.org/cell-feature-explorer.html?cellSelectedFor3D={}".format(row["CellId"])


raw["FeatureExplorerURL"] = raw.apply(create_feature_explorer_url, axis=1)

# Step 3:
# Validate and prune the raw data
# During the prune operation we lose ~16 rows of data to missing single cell feature files
# We are still investigating this...
cleaned = validate(raw, drop_on_error=True)
print(f"Dropped {len(raw) - len(cleaned.data)} rows during validation.")

# Step 4:
# Send to dataset object for package construction
ds = Dataset(cleaned.data, "Pipeline Integrated Single Cell", "aics", "readme.md")

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
    "save_feats_path": "cell_features",
    "save_reg_path": "cell_images_3d",
    "save_reg_path_flat": "cell_images_2d",
    "save_reg_path_flat_proj": "cell_images_2d_projections"
})

# Add any extra files
ds.set_extra_files({
    "contact_sheets": list(scp_output_dir.glob("diagnostics_*.png"))
})

# Step 6:
# Distribute the package
ds.distribute(
    push_uri="s3://quilt-aics",
    message="Add feature explorer links to metadata"
)

print("-" * 80)
print("COMPLETE")
