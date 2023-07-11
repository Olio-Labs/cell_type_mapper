import h5py
import json
import numpy as np
import time
import warnings

from cell_type_mapper.marker_selection.selection_pipeline import (
    select_all_markers)


def create_marker_cache_from_reference_markers(
        output_cache_path,
        input_cache_path,
        query_gene_names,
        taxonomy_tree,
        n_per_utility=15,
        n_processors=6,
        behemoth_cutoff=10000000):
    """
    Populate the temporary HDF5 file with the lists of marker
    genes for each parent node.

    Parameters
    ----------
    output_cache_path:
        The file to be written
    input_cache_path:
        Path to the cache of marker gene data from the
        reference dataset
    query_gene_names:
        list of gene names in the query dataset
    taxonomy_tree:
        Dict encoding the cell type taxonomy
    n_per_utility:
        How many genes to select per (taxon_pair, sign)
        combination
    n_processors:
        Number of independent workers to spin up.
    behemoth_cutoff:
        Number of leaf nodes for a parent to be considered
        a behemoth
    """
    print(f"creating marker gene cache in {output_cache_path}")
    t0 = time.time()

    # create a dict mapping from parent_node to
    # lists of marker gene names
    marker_lookup = select_all_markers(
        marker_cache_path=input_cache_path,
        query_gene_names=query_gene_names,
        taxonomy_tree=taxonomy_tree,
        n_per_utility=n_per_utility,
        n_processors=n_processors,
        behemoth_cutoff=behemoth_cutoff)

    with h5py.File(input_cache_path, 'r') as in_file:
        reference_gene_names = json.loads(
            in_file['full_gene_names'][()].decode('utf-8'))

    # reformat marker lookup so the keys are the
    # 'parent/level' groups that will actually be
    # stored in the final HDF5 file
    created_groups = set()
    reformatted_lookup = dict()
    parent_list = list(marker_lookup.keys())
    for parent in parent_list:
        if parent is None:
            parent_grp = 'None'
        else:
            parent_grp = f'{parent[0]}/{parent[1]}'

        if parent_grp in created_groups:
            raise RuntimeError(
                "tried to create query marker group\n"
                f"{parent_grp}\n"
                "more than once")

        created_groups.add(parent_grp)
        reformatted_lookup[parent_grp] = marker_lookup.pop(parent)

    write_query_markers_to_h5(
        marker_lookup=reformatted_lookup,
        reference_gene_names=reference_gene_names,
        query_gene_names=query_gene_names,
        output_cache_path=output_cache_path)

    duration = (time.time()-t0)/3600.0
    print(f"created {output_cache_path} in {duration:.2e} hours")


def create_marker_cache_from_specified_markers(
        marker_lookup,
        reference_gene_names,
        query_gene_names,
        output_cache_path,
        log=None):
    """
    Write marker genes to HDF5 file

    Parameters
    ----------
    marker_lookup:
        Dict mapping the parent/level groups as they will
        appear in the HDF5 file to lists of marker genes
    reference_gene_names:
        Ordered list of genes in reference dataset
    query_gene_names:
        Ordered list of genes in query dataset
    output_cache_path:
        Path to HDF5 file that will be written
    log:
        Optional object to log messages/warnings for CLI

    Notes
    -----
    If there are marker genes missing from query_gene_names,
    those markers will just be dropped and a warning issued
    """
    print(f"creating marker gene cache in {output_cache_path}")
    t0 = time.time()
    query_gene_set = set(query_gene_names)
    reference_gene_set = set(reference_gene_names)
    final_marker_lookup = dict()
    missing_query_markers = set()
    missing_reference_markers = set()
    for parent_node in marker_lookup:
        if parent_node == 'metadata':
            continue
        marker_set = set(marker_lookup[parent_node])
        these_markers = list(marker_set.intersection(query_gene_set))

        if len(these_markers) == 0 and len(marker_set) > 0:
            these_markers = list(query_gene_set)
            msg = f"No markers at parent node '{parent_node}' were present "
            msg += f"in query set. Using all {len(query_gene_set)} "
            msg += "query genes at this node"
            if log is None:
                warnings.warn(msg)
            else:
                log.warn(msg)

        final_marker_lookup[parent_node] = these_markers
        missing_query_markers = missing_query_markers.union(
            marker_set-query_gene_set)
        missing_reference_markers = missing_reference_markers.union(
            marker_set-reference_gene_set)

    if len(missing_reference_markers) > 0:
        missing_reference_markers = list(missing_reference_markers)
        missing_reference_markers.sort()
        msg = "The following marker genes are not "
        msg += "in the reference dataset\n"
        msg += f"{missing_reference_markers}\n"
        if log is None:
            raise RuntimeError(msg)
        else:
            log.error(msg)

    write_query_markers_to_h5(
        marker_lookup=final_marker_lookup,
        reference_gene_names=reference_gene_names,
        query_gene_names=query_gene_names,
        output_cache_path=output_cache_path)

    if len(missing_query_markers) > 0:
        missing_query_markers = list(missing_query_markers)
        missing_query_markers.sort()
        n_missing = len(missing_query_markers)
        msg = f"{n_missing} marker genes were not present "
        msg += "in the query dataset. "
        msg += "They have been ignored"
        if log is None:
            warnings.warn(msg)
        else:
            log.warn(msg)

    duration = (time.time()-t0)/3600.0
    print(f"created {output_cache_path} in {duration:.2e} hours")


def write_query_markers_to_h5(
        marker_lookup,
        reference_gene_names,
        query_gene_names,
        output_cache_path):
    """
    Write marker genes to HDF5 file

    Parameters
    ----------
    marker_lookup:
        Dict mapping the parent/level groups as they will
        appear in the HDF5 file to lists of marker genes
    reference_gene_names:
        Ordered list of genes in reference dataset
    query_gene_names:
        Ordered list of genes in query dataset
    output_cache_path:
        Path to HDF5 file that will be written
    """

    parent_node_list = list(marker_lookup.keys())
    parent_node_list.sort()
    with h5py.File(output_cache_path, 'w') as out_file:
        out_file.create_dataset(
            'parent_node_list',
            data=json.dumps(parent_node_list).encode('utf-8'))

    query_name_to_int = {
        n: ii for ii, n in enumerate(query_gene_names)}
    reference_name_to_int = {
        n: ii for ii, n in enumerate(reference_gene_names)}

    # all of the indexes of genes that get used as markers
    query_genes = set()
    reference_genes = set()
    for parent in marker_lookup:
        for gene in marker_lookup[parent]:
            query_genes.add(query_name_to_int[gene])
            reference_genes.add(reference_name_to_int[gene])
    query_genes = np.sort(np.array(list(query_genes)))
    reference_genes = np.sort(np.array(list(reference_genes)))

    with h5py.File(output_cache_path, "a") as cache_file:
        cache_file.create_dataset(
            "all_query_markers",
            data=query_genes)
        cache_file.create_dataset(
            "all_reference_markers",
            data=reference_genes)
        cache_file.create_dataset(
            "query_gene_names",
            data=json.dumps(query_gene_names).encode("utf-8"))
        cache_file.create_dataset(
            "reference_gene_names",
            data=json.dumps(reference_gene_names).encode('utf-8'))

        for parent_grp in marker_lookup:
            out_grp = cache_file.create_group(parent_grp)
            these_reference = []
            these_query = []
            for gene in marker_lookup[parent_grp]:
                these_reference.append(reference_name_to_int[gene])
                these_query.append(query_name_to_int[gene])
            if len(these_reference) > 0:
                these_reference = np.array(these_reference)
                these_query = np.array(these_query)
                sorted_dex = np.argsort(these_reference)
                these_reference = these_reference[sorted_dex]
                these_query = these_query[sorted_dex]

            out_grp.create_dataset(
                'reference',
                data=np.array(these_reference))
            out_grp.create_dataset(
                'query',
                data=np.array(these_query))


def serialize_markers(
        marker_cache_path,
        taxonomy_tree):
    """
    Take a path to a marker gene cache and return a dict of marker
    genes suitable for serialization to the final output

    Parameters
    ----------
    marker_cache_path:
        Path to HDF5 file written by create_maker_cache_... method
    taxonomy_tree:
        TaxonomyTree defining the taxonomy

    Returns
    -------
    Dict mapping strings representing 'level/node' parents to lists
    of marker genes.
    """
    marker_gene_lookup = dict()
    with h5py.File(marker_cache_path, "r") as src:
        reference_gene_names = json.loads(
            src['reference_gene_names'][()].decode('utf-8'))
        for level in taxonomy_tree.hierarchy[:-1]:
            for node in taxonomy_tree.nodes_at_level(level):
                grp_key = f"{level}/{node}"
                if len(taxonomy_tree.children(level=level, node=node)) < 2:
                    ref_idx = []
                else:
                    ref_idx = src[grp_key]['reference'][()]
                marker_gene_lookup[grp_key] = [
                    str(reference_gene_names[ii]) for ii in ref_idx]

        grp_key = "None"
        ref_idx = src[grp_key]['reference'][()]
        marker_gene_lookup[grp_key] = [
            str(reference_gene_names[ii]) for ii in ref_idx]
    return marker_gene_lookup