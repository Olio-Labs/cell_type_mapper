import pathlib

from hierarchical_mapping.gene_id.gene_id_mapper import (
    GeneIdMapper)

from hierarchical_mapping.taxonomy.data_release_utils import (
    get_alias_mapper)

from hierarchical_mapping.taxonomy.taxonomy_tree import (
    TaxonomyTree)

def main():
    marker_dir = pathlib.Path(
        '/allen/programs/celltypes/workgroups/rnaseqanalysis/shiny/Taxonomies/AIT17.0_mouse/Templates/marker_list_on_nodes')

    marker_dir = pathlib.Path(
        '/allen/programs/celltypes/workgroups/rnaseqanalysis/shiny/Taxonomies/AIT17_knowledge/nlevel4_marker_index/marker_list_on_nodes')

    assert marker_dir.is_dir()

    data_dir = pathlib.Path(
        "/allen/programs/celltypes/workgroups/rnaseqanalysis/lydian/ABC_handoff/metadata/")
    assert data_dir.is_dir()

    cluster_membership = data_dir / "WMB-taxonomy/20230630/cluster_to_cluster_annotation_membership.csv"
    assert cluster_membership.is_file()

    cluster_annotation = data_dir / "WMB-taxonomy/20230630/cluster_annotation_term.csv"
    assert cluster_annotation.is_file()

    cell_metadata = data_dir / "WMB-10X/20230630/cell_metadata.csv"
    assert cell_metadata.is_file()

    taxonomy_tree = TaxonomyTree.from_data_release(
        cell_metadata_path=cell_metadata,
        cluster_annotation_path=cluster_annotation,
        cluster_membership_path=cluster_membership,
        hierarchy=[
        "CCN20230504_CLAS",
        "CCN20230504_SUBC",
        "CCN20230504_SUPT",
        "CCN20230504_CLUS"])

    taxonomy_tree = taxonomy_tree.drop_level("CCN20230504_SUPT")
    print(taxonomy_tree.hierarchy)

    alias_mapper = get_alias_mapper(
        csv_path=cluster_membership,
        valid_term_set_labels=taxonomy_tree.hierarchy,
        alias_column_name='cluster_annotation_term_name',
        strict_alias=True)

    level_to_idx = {n:ii+2 for ii, n in enumerate(taxonomy_tree.hierarchy)}
    print('level to idx')
    print(level_to_idx)
    good_ct = 0
    bad_ct = 0
    parent_list = taxonomy_tree.all_parents

    expected_file_names = []
    missing_file_names = []
    for parent_node in parent_list:
        if parent_node is None:
            fname = 'marker.1.root.csv'
        else:
            children = taxonomy_tree.children(parent_node[0], parent_node[1])
            if len(children) < 2:
                continue
            level_idx = level_to_idx[parent_node[0]]
            readable_name = alias_mapper[(parent_node[0], parent_node[1])]
            prefix = readable_name.split()[0]
            readable_name = readable_name.replace(f'{prefix} ','')
            munged = readable_name.replace(' ','+').replace('/','__')
            fname = f'marker.{level_idx}.{munged}.csv'
        fpath = marker_dir / fname
        expected_file_names.append(fname)
        if fpath.is_file():
            good_ct += 1
            print(f'found {fname}')
        else:
            bad_ct += 1
            missing_file_names.append(fname)
            print(f"{fname} does not exist")
    print(f"good {good_ct} bad {bad_ct}")
    missing_file_names.sort()
    expected_file_names.sort()
    str_dir = str(marker_dir.resolve().absolute())
    with open("expected_marker_files.csv", "w") as dst:
        dst.write("# list of expected file names\n")
        dst.write(f"# in dir {str_dir}\n")
        for f in expected_file_names:
            dst.write(f"{f}\n")

    with open("missing_marker_files.csv", "w") as dst:
        dst.write("# list of missing file names\n")
        dst.write(f"# in dir {str_dir}\n")
        for f in missing_file_names:
            dst.write(f"{f}\n")
 

    print("all done")

if __name__ == "__main__":
    main()