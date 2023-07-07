import copy
import json
import pathlib

from hierarchical_mapping.utils.utils import (
    json_clean_dict,
    get_timestamp)

from hierarchical_mapping.taxonomy.utils import (
    validate_taxonomy_tree,
    get_all_leaf_pairs,
    get_taxonomy_tree_from_h5ad,
    convert_tree_to_leaves,
    get_all_pairs,
    get_child_to_parent)

from hierarchical_mapping.taxonomy.data_release_utils import (
    get_tree_above_leaves,
    get_label_to_name,
    get_cell_to_cluster_alias,
    get_term_set_map)


class TaxonomyTree(object):

    def __init__(
            self,
            data):
        """
        data is a dict encoding the taxonomy tree.
        Probably, users will not instantiate this class
        directly, instead using one of the classmethods
        """
        self._data = copy.deepcopy(data)
        validate_taxonomy_tree(self._data)
        self._child_to_parent = get_child_to_parent(self._data)

    def __eq__(self, other):
        """
        Ignore keys 'metadata' and 'alias_mapping'
        """
        these_keys = set(self._data.keys())
        other_keys = set(other._data.keys())

        bad_keys = {'metadata',
                    'name_mapper',
                    'hierarchy_mapper'}

        these_keys -= bad_keys
        other_keys -= bad_keys
        if these_keys != other_keys:
            return False
        for k in these_keys:
            if self._data[k] != other._data[k]:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def from_h5ad(cls, h5ad_path, column_hierarchy):
        """
        Instantiate from the obs dataframe of an h5ad file.

        Parameters
        ----------
        h5ad_path:
            path to the h5ad file
        column_hierarchy:
            ordered list of levels in the taxonomy (columns in the
            obs dataframe to be read in)
        """
        h5ad_path = pathlib.Path(h5ad_path)
        data = get_taxonomy_tree_from_h5ad(
            h5ad_path=h5ad_path,
            column_hierarchy=column_hierarchy)

        data['metadata'] = {
            'factory': 'from_h5ad',
            'timestamp': get_timestamp(),
            'params': {
                'h5ad_path': str(h5ad_path.resolve().absolute()),
                'column_hierarchy': column_hierarchy}}

        return cls(data=data)

    @classmethod
    def from_str(cls, serialized_dict):
        """
        Instantiate from a JSON serialized dict
        """
        return cls(
            data=json.loads(serialized_dict))

    @classmethod
    def from_json_file(cls, json_path):
        """
        Instantiate from a file containing the JSON-serialized
        tree
        """
        return cls(
            data=json.load(open(json_path, 'rb')))

    @classmethod
    def from_data_release(
            cls,
            cell_metadata_path,
            cluster_annotation_path,
            cluster_membership_path,
            hierarchy):
        """
        Construct a TaxonomyTree from the canonical CSV files
        encoding a taxonomy for a data release

        Parameters
        ----------
        cell_metadata_path:
            path to cell_metadata.csv; the file mapping cells to clusters
        cluster_annotation_path:
            path to cluster_annotation_term.csv; the file containing
            parent-child relationships
        cluster_membership_path:
            path to cluster_to_cluster_annotation_membership.csv;
            the file containing the mapping between cluster labels
            and aliases
        hierarchy:
            list of term_set labels (*not* aliases) in the hierarchy
            from most gross to most fine
        """
        cell_metadata_path = pathlib.Path(cell_metadata_path)
        cluster_annotation_path = pathlib.Path(cluster_annotation_path)
        cluster_membership_path = pathlib.Path(cluster_membership_path)

        data = dict()
        data['metadata'] = {
            'factory': 'from_data_release',
            'timestamp': get_timestamp(),
            'params': {
                'cell_metadata_path':
                    str(cell_metadata_path.resolve().absolute()),
                'cluster_annotation_path':
                    str(cluster_annotation_path.resolve().absolute()),
                'cluster_membership_path':
                    str(cluster_membership_path.resolve().absolute()),
                'hierarchy': hierarchy}}

        leaf_level = hierarchy[-1]

        cell_to_alias = get_cell_to_cluster_alias(
            csv_path=cell_metadata_path)

        rough_tree = get_tree_above_leaves(
            csv_path=cluster_annotation_path,
            hierarchy=hierarchy)

        hierarchy_level_map = get_term_set_map(
            csv_path=cluster_membership_path)

        data['hierarchy_mapper'] = hierarchy_level_map

        data['hierarchy'] = copy.deepcopy(hierarchy)
        for parent_level, child_level in zip(hierarchy[:-1], hierarchy[1:]):
            data[parent_level] = dict()
            for node in rough_tree[parent_level]:
                data[parent_level][node] = []
                for child in rough_tree[parent_level][node]:
                    data[parent_level][node].append(child)
            for node in data[parent_level]:
                data[parent_level][node].sort()

        # get mappings between labels and other ways
        # of referring to taxons
        cluster_to_alias = get_label_to_name(
            csv_path=cluster_membership_path,
            valid_term_set_labels=(leaf_level,),
            name_column='cluster_alias')

        alias_to_cluster_label = dict()
        for k in cluster_to_alias:
            label = k[1]
            alias = cluster_to_alias[k]
            if alias in alias_to_cluster_label:
                raise RuntimeError(
                    f"alias {alias} maps to clusters "
                    f"{label} and {alias_to_cluster_label[alias]}")
            alias_to_cluster_label[alias] = label

        label_to_name = get_label_to_name(
            csv_path=cluster_membership_path,
            valid_term_set_labels=hierarchy,
            name_column='cluster_annotation_term_name')

        # now add leaves (referring to them by their labels)
        leaves = dict()
        for cell in cell_to_alias:
            alias = cell_to_alias[cell]
            leaf = alias_to_cluster_label[alias]
            if leaf not in leaves:
                leaves[leaf] = []
            leaves[leaf].append(cell)
        for leaf in leaves:
            leaves[leaf].sort()

        data[hierarchy[-1]] = leaves

        # create a mapp from [level][node] to all
        # alternative naming schemes
        final_name_map = dict()
        for k in label_to_name:
            level = k[0]
            label = k[1]
            name = label_to_name[k]
            if level not in final_name_map:
                final_name_map[level] = dict()
            if label not in final_name_map[level]:
                final_name_map[level][label] = dict()
            if 'name' in final_name_map[level][label]:
                if final_name_map[level][label]['name'] != name:
                    raise RuntimeError(
                        f"level {level}, label {label} has at least "
                        f"two names: {name} and "
                        f"{final_name_map[level][label]['name']}")
            final_name_map[level][label]['name'] = name

        # add cluster aliases to final_name_map
        for k in cluster_to_alias:
            final_name_map[k[0]][k[1]]['alias'] = cluster_to_alias[k]
        data['name_mapper'] = final_name_map

        return cls(data=data)

    def to_str(self, indent=None, drop_cells=False):
        """
        Return JSON-serialized dict of this taxonomy

        If drop_cells == True, then do not serialize the mapping
        from leaf node to cells
        """
        if drop_cells:
            out_dict = copy.deepcopy(self._data)
            for leaf in out_dict[self.leaf_level]:
                out_dict[self.leaf_level][leaf] = []
        else:
            out_dict = self._data

        return json.dumps(json_clean_dict(out_dict), indent=indent)

    def flatten(self):
        """
        Return a 'flattened' (i.e. 1-level) version of the taxonomy tree.
        """
        new_data = copy.deepcopy(self._data)
        if 'metadata' in new_data:
            new_data['metadata']['flattened'] = True
        new_data['hierarchy'] = [self._data['hierarchy'][-1]]
        for level in self._data['hierarchy'][:-1]:
            new_data.pop(level)
        return TaxonomyTree(data=new_data)

    def drop_level(self, level_to_drop):
        """
        Return a new taxonomy tree which has dropped the specified
        level from its hierarchy.

        Will not drop leaf levels from tree.
        """

        if len(self.hierarchy) == 1:
            raise RuntimeError(
                "Cannot drop a level from this tree. "
                f"It is flat. hierarchy={self.hierarchy}")

        if level_to_drop not in self.hierarchy:
            raise RuntimeError(
                f"Cannot drop level '{level_to_drop}' from this tree. "
                "That level is not in the hierarchy\n"
                f"hierarchy={self.hierarchy}")

        if level_to_drop == self.leaf_level:
            raise RuntimeError(
                f"Cannot drop level '{level_to_drop}' from this tree. "
                "That is the leaf level.")

        new_data = copy.deepcopy(self._data)
        if 'metadata' in new_data:
            if 'dropped_levels' not in new_data['metadata']:
                new_data['metadata']['dropped_levels'] = []
            new_data['metadata']['dropped_levels'].append(level_to_drop)

        level_idx = -1
        for idx, level in enumerate(self.hierarchy):
            if level == level_to_drop:
                level_idx = idx
                break

        if level_idx == 0:
            new_data['hierarchy'].pop(0)
            new_data.pop(level_to_drop)
            return TaxonomyTree(data=new_data)

        parent_idx = level_idx - 1
        parent_level = self.hierarchy[parent_idx]

        new_parent = dict()
        for node in new_data[parent_level]:
            new_parent[node] = []
            for child in self.children(parent_level, node):
                new_parent[node] += self.children(level_to_drop, child)

        new_data.pop(level_to_drop)
        new_data[parent_level] = new_parent
        new_data['hierarchy'].pop(level_idx)
        return TaxonomyTree(data=new_data)

    @property
    def hierarchy(self):
        return copy.deepcopy(self._data['hierarchy'])

    def nodes_at_level(self, this_level):
        """
        Return a list of all valid nodes at the specified level
        """
        if this_level not in self._data:
            raise RuntimeError(
                f"{this_level} is not a valid level in this taxonomy;\n"
                f"valid levels are:\n {self.valid_levels}")
        return list(self._data[this_level].keys())

    def parents(self, level, node):
        """
        return a dict listing all the ancestors of
        (level, node)
        """
        this = dict()
        hierarchy_idx = None
        for idx in range(len(self.hierarchy)):
            if self.hierarchy[idx] == level:
                hierarchy_idx = idx
                break
        for parent_level_idx in range(hierarchy_idx-1, -1, -1):
            current = self.hierarchy[parent_level_idx]
            if len(this) == 0:
                this[current] = self._child_to_parent[level][node]
            else:
                prev = self.hierarchy[parent_level_idx+1]
                prev_node = this[prev]
                this[current] = self._child_to_parent[prev][prev_node]
        return this

    def children(self, level, node):
        """
        Return the immediate children of the specified node
        """
        if level is None and node is None:
            return list(self._data[self.hierarchy[0]].keys())
        if level not in self._data.keys():
            raise RuntimeError(
                f"{level} is not a valid level\ntry {self.valid_levels}")
        if node not in self._data[level]:
            raise RuntimeError(f"{node} not a valid node at level {level}")
        return list(self._data[level][node])

    @property
    def leaf_level(self):
        """
        Return the leaf level of this taxonomy
        """
        return self._data['hierarchy'][-1]

    @property
    def all_leaves(self):
        """
        List of valid leaf names
        """
        return list(self._data[self.leaf_level].keys())

    @property
    def n_leaves(self):
        return len(self.all_leaves)

    @property
    def as_leaves(self):
        """
        Return a Dict structured like
            level ('class', 'subclass', 'cluster', etc.)
                -> node1 (a node on that level of the tree)
                    -> list of leaf nodes making up that node
        """
        return convert_tree_to_leaves(self._data)

    @property
    def siblings(self):
        """
        Return all pairs of nodes that are on the same level
        """
        return get_all_pairs(self._data)

    @property
    def leaf_to_cells(self):
        """
        Return the lookup from leaf name to cells in the
        cell by gene file
        """
        return copy.deepcopy(self._data[self.leaf_level])

    @property
    def all_parents(self):
        """
        Return a list of all (level, node) tuples indicating
        valid parents in this taxonomy
        """
        parent_list = [None]
        for level in self._data['hierarchy'][:-1]:
            for node in self._data[level]:
                parent = (level, node)
                parent_list.append(parent)
        return parent_list

    def rows_for_leaf(self, leaf_node):
        """
        Return the list of rows associated with the specified
        leaf node.
        """
        if leaf_node not in self._data[self.leaf_level]:
            raise RuntimeError(
                f"{leaf_node} is not a valid {self.leaf_level} "
                "in this taxonomy")
        return self._data[self.leaf_level][leaf_node]

    def label_to_name(self, level, label, name_key='name'):
        """
        Parameters
        ----------
        level:
            the level in the hierarchy
        label:
            the machine readable label of the node
        name_key:
            the alternative name to return (e.g. 'name' or 'alias')

        Returns
        -------
        The human readable name

        Note
        ----
        if mapping is impossible, just return label
        """
        if 'name_mapper' not in self._data:
            return label
        name_mapper = self._data['name_mapper']
        if level not in name_mapper:
            return label
        if label not in name_mapper[level]:
            return label
        if name_key not in name_mapper[level][label]:
            return label
        return name_mapper[level][label][name_key]

    def level_to_name(self, level_label):
        """
        Map the label for a hierarchy level to its name.
        If no mapper exists (or the level_label is unknown)
        just return level_label
        """
        if 'hierarchy_mapper' not in self._data:
            return level_label
        if level_label not in self._data['hierarchy_mapper']:
            return level_label
        return self._data['hierarchy_mapper'][level_label]

    def leaves_to_compare(
            self,
            parent_node):
        """
        Find all of the leaf nodes that need to be compared
        under a given parent.

        i.e., if I know I am a member of node A, find all of the
        children (B1, B2, B3) and then finda all of the pairs
        (B1.L1, B2.L1), (B1.L1, B2.L2)...(B1.LN, B2.L1)...(B1.N, BN.LN)
        where B.LN are the leaf nodes that descend from B1, B2.LN are
        the leaf nodes that descend from B2, etc.

        Parameters
        ----------
        parent_node:
           Either None or a (level, node) tuple specifying
           the parent whose children we are choosing between
           (None means we are at the root level)

        Returns
        -------
        A list of (level, leaf_node1, leaf_node2) tuples indicating
        the leaf nodes that need to be compared.
        """
        if parent_node is not None:
            this_level = parent_node[0]
            this_node = parent_node[1]
            if this_level not in self._data['hierarchy']:
                raise RuntimeError(
                    f"{this_level} is not a valid level in this "
                    "taxonomy\n valid levels are:\n"
                    f"{self._data['hierarchy']}")
            this_level_lookup = self._data[this_level]
            if this_node not in this_level_lookup:
                raise RuntimeError(
                    f"{this_node} is not a valid node at level "
                    f"{this_level} of this taxonomy\nvalid nodes ")

        result = get_all_leaf_pairs(
            taxonomy_tree=self._data,
            parent_node=parent_node)
        return result
