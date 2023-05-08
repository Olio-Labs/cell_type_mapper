import pytest
import copy
import numpy as np
import json
import itertools

from hierarchical_mapping.taxonomy.utils import (
    get_taxonomy_tree)

from hierarchical_mapping.taxonomy.taxonomy_tree import (
    TaxonomyTree)


@pytest.fixture
def taxonomy_tree_fixture(
        records_fixture,
        column_hierarchy):
    return TaxonomyTree(
        data=get_taxonomy_tree(
            obs_records=records_fixture,
            column_hierarchy=column_hierarchy))


def test_tree_as_leaves(
        records_fixture,
        column_hierarchy,
        parent_to_leaves,
        taxonomy_tree_fixture):

    as_leaves = taxonomy_tree_fixture.as_leaves

    for h in column_hierarchy:
        for this_node in parent_to_leaves[h]:
            expected = parent_to_leaves[h][this_node]
            actual = as_leaves[h][this_node]
            assert set(actual) == expected
            assert len(set(actual)) == len(actual)


def test_tree_get_all_pairs(
        records_fixture,
        column_hierarchy,
        l1_to_l2_fixture,
        l2_to_class_fixture,
        class_to_cluster_fixture,
        taxonomy_tree_fixture):

    siblings = taxonomy_tree_fixture.siblings
    ct = 0
    for level, lookup in zip(('level1', 'level2', 'class'),
                             (l1_to_l2_fixture[0],
                              l2_to_class_fixture[0],
                               class_to_cluster_fixture[0])):
        elements = list(lookup.keys())
        elements.sort()
        for i0 in range(len(elements)):
            for i1 in range(i0+1, len(elements), 1):
                test = (level, elements[i0], elements[i1])
                assert test in siblings
                ct += 1
    cluster_list = []
    for k in class_to_cluster_fixture[0]:
        cluster_list += list(class_to_cluster_fixture[0][k])
    cluster_list.sort()
    for i0 in range(len(cluster_list)):
        for i1 in range(i0+1, len(cluster_list), 1):
            test = ('cluster', cluster_list[i0], cluster_list[i1])
            assert test in siblings
            ct += 1
    assert len(siblings) == ct


def test_tree_get_all_leaf_pairs():

    tree_data = {
        'hierarchy': ['level1', 'level2', 'level3', 'leaf'],
        'level1': {'l1a': set(['l2b', 'l2d']),
                   'l1b': set(['l2a', 'l2c', 'l2e']),
                   'l1c': set(['l2f',])
                  },
        'level2': {'l2a': set(['l3b',]),
                   'l2b': set(['l3a', 'l3c']),
                   'l2c': set(['l3e',]),
                   'l2d': set(['l3d', 'l3f', 'l3h']),
                   'l2e': set(['l3g',]),
                   'l2f': set(['l3i',])},
        'level3': {'l3a': set([str(ii) for ii in range(3)]),
                   'l3b': set([str(ii) for ii in range(3, 7)]),
                   'l3c': set([str(ii) for ii in range(7, 9)]),
                   'l3d': set([str(ii) for ii in range(9, 13)]),
                   'l3e': set([str(ii) for ii in range(13, 15)]),
                   'l3f': set([str(ii) for ii in range(15, 19)]),
                   'l3g': set([str(ii) for ii in range(19, 21)]),
                   'l3h': set([str(ii) for ii in range(21, 23)]),
                   'l3i': set(['23',])},
        'leaf': {str(k): range(k,26*k, 26*(k+1))
                 for k in range(24)}}

    taxonomy_tree = TaxonomyTree(data=tree_data)

    # check non-None parent Node
    parent_node = ('level2', 'l2b')
    actual = taxonomy_tree.leaves_to_compare(parent_node)

    candidates0 = ['0', '1', '2']
    candidates1 = ['7', '8']
    expected = []
    for pair in itertools.product(candidates0, candidates1):
        expected.append(('leaf', pair[0], pair[1]))

    assert set(actual) == set(expected)

    # check case with parent_node = None
    parent_node = None
    candidates0 = ['0', '1', '2', '7', '8', '9', '10', '11', '12',
                   '15', '16', '17', '18', '21', '22']
    candidates1 = ['3', '4', '5', '6', '13', '14', '19', '20']
    candidates2 = ['23']

    actual = taxonomy_tree.leaves_to_compare(parent_node)

    expected = []
    for c0, c1 in itertools.combinations([candidates0,
                                          candidates1,
                                          candidates2], 2):
        for pair in itertools.product(c0, c1):
            if pair[0] < pair[1]:
                expected.append(('leaf', pair[0], pair[1]))
            else:
                expected.append(('leaf', pair[1], pair[0]))
    assert set(actual) == set(expected)

    # check case when there are no pairs to compare
    parent_node = ('level1', 'l1c')
    actual = taxonomy_tree.leaves_to_compare(parent_node)
    assert actual == []

    parent_node=('leaf', '15')
    actual = taxonomy_tree.leaves_to_compare(parent_node)
    assert actual == []