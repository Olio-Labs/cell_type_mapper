import json
import pandas as pd
import pathlib


def blob_to_csv(
        results_blob,
        taxonomy_tree,
        output_path,
        confidence_key='confidence',
        confidence_label='confidence',
        metadata_path=None):
    """
    Write a set of results originally formatted for a JSON blob
    out to the CSV our users will expect.

    Parameters
    ----------
    results_blob:
        The blob-form results. A list of dicts. Each dict is a cell
        and looks like
            {
                'cell_id': my_cell,
                'level1': {'assignment':...
                           'confidence':...},
                'level2': {'assignment':...,
                           'confidence':...}}
    taxonomy_tree:
        TaxonomyTree that went into this run.
        Hierarchy will be listed as a comment at the top of this file.
    output_path:
        Path to the CSV file that will be written
    confidence_key:
        The key with in the blob dict pointing to the confidence stat
    confidence_label:
        The name used for the confidence stat in the CSV header
    metadata_path:
        Path to the metadta path going with this output (if any;
        file name will be recorded as a comment at the top of
        the file)
    """
    str_hierarchy = json.dumps(taxonomy_tree.hierarchy)

    with open(output_path, 'w') as dst:
        if metadata_path is not None:
            metadata_path = pathlib.Path(metadata_path)
            dst.write(f'# metadata = {metadata_path.name}\n')
        dst.write(f'# taxonomy hierarchy = {str_hierarchy}\n')
        readable_hierarchy = [
            taxonomy_tree.level_to_name(level_label=level_label)
            for level_label in taxonomy_tree.hierarchy]
        if readable_hierarchy != taxonomy_tree.hierarchy:
            str_readable_hierarchy = json.dumps(readable_hierarchy)
            dst.write(f'# readable taxonomy hierarchy = '
                      f'{str_readable_hierarchy}\n')

        csv_data = []
        for cell in results_blob:
            values = {'cell_id': cell['cell_id']}
            for level in taxonomy_tree.hierarchy:
                readable_level = taxonomy_tree.level_to_name(level_label=level)
                label = cell[level]['assignment']
                name = taxonomy_tree.label_to_name(
                            level=level,
                            label=label,
                            name_key='name')
                values[f'{readable_level}_label'] = label
                values[f'{readable_level}_name'] = name

                if level == taxonomy_tree.leaf_level:
                    alias = taxonomy_tree.label_to_name(
                                level=level,
                                label=label,
                                name_key='alias')
                    values[f'{readable_level}_alias'] = alias

                values[f"{readable_level}_{confidence_label}"] = \
                    cell[level][confidence_key]

            csv_data.append(values)
        csv_df = pd.DataFrame(csv_data)
        csv_df.to_csv(dst, index=False, float_format='%.4f')
