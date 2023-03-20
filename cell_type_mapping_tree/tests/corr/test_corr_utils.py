import pytest

import numpy as np

from hierarchical_mapping.corr.utils import (
    match_genes)


@pytest.mark.parametrize(
        "query, expected",
        [(['b', 'x', 'f', 'e', 'w'],
          {'reference': np.array([0, 5, 3]),
           'query': np.array([0, 3, 2])}),
          (['w', 'x', 'y'],
           {'reference': [],
            'query': []}
          ),
          (['x', 'f', 'e', 'w', 'b'],
          {'reference': np.array([0, 5, 3]),
           'query': np.array([4, 2, 1])}),
        ])
def test_match_genes(
        query,
        expected):
    reference_gene_names = ['b', 'a', 'c', 'f', 'd', 'e']
    actual = match_genes(
                reference_gene_names=reference_gene_names,
                query_gene_names=query)


    if len(expected['reference']) > 0:
        np.testing.assert_array_equal(actual['reference'],
                                      expected['reference'])
        np.testing.assert_array_equal(actual['query'],
                                      expected['query'])
    else:
        assert len(actual['reference']) == 0
        assert len(actual['query']) == 0