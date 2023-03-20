import numpy as np


def match_genes(
        reference_gene_names,
        query_gene_names):
    """
    Find the genes that overlap between a baseline dataset
    and a query data set.

    Parameters
    ----------
    reference_gene_names:
        List of gene names from the reference data set

    query_gene_names:
        List of gene names from the query data set

    Returns
    -------
    Dict:
        "reference":
            np.ndarray of ints; the indices of shared
            genes in the reference data

        "query":
            np.ndarray of ints; the indices of shared genes
            in the query data
    """
    reference_set = set(reference_gene_names)
    query_set = set(query_gene_names)
    shared_set = list(reference_set.intersection(query_set))
    shared_set.sort()

    result = {
        'reference': _gene_name_to_int(
                        ordered_gene_name=shared_set,
                        unordered_gene_name=reference_gene_names),
        'query': _gene_name_to_int(
                        ordered_gene_name=shared_set,
                        unordered_gene_name=query_gene_names)}

    return result


def _gene_name_to_int(
        ordered_gene_name,
        unordered_gene_name):
    """
    Return the np.ndarray of ints that can be used to
    slice unordered_gene_name to produce ordered_gene_name
    """
    unordered_lookup = {g: ii
                        for ii, g in enumerate(unordered_gene_name)}
    return np.array(
        [unordered_lookup[g] for g in ordered_gene_name])