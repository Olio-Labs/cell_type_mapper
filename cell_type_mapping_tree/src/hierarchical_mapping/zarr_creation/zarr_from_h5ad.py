import anndata
import json
import pathlib
import tempfile

from hierarchical_mapping.utils.utils import (
    _clean_up,
    json_clean_dict)

from hierarchical_mapping.utils.taxonomy_utils import (
    compute_row_order)

from hierarchical_mapping.utils.h5ad_remapper import (
    rearrange_sparse_h5ad_hunter_gather)


def contiguous_zarr_from_h5ad(
        h5ad_path,
        zarr_path,
        taxonomy_hierarchy,
        zarr_chunks=2000000,
        write_buffer_size=400000000,
        read_buffer_size=1000000000,
        tmp_dir=None,
        n_processors=4):
    """
    Read in an anndata h5ad file of cell x gene data.

    Write a zarr file in which cells that share a taxonomical
    assignment are stored in contiguous rows.

    Both the input h5ad file and the output zarr "file"
    are expected to contain cell x gene data in CSR format.

    Parameters
    ----------
    h5ad_path:
        Path to the input h5ad file

    zarr_path:
        Path to the zarr "file" to be written

    taxonomy_hierarchy:
        List of taxonomic column names ordered from root to leaf.

    zarr_chunks:
        Size of chunks in which zarr file is stored

    write_buffer_size:
        Number of floats/ints stored at a time by writer
        workers (see below)

    read_buffer_size:
        Number of floats/ints stored at a time by reader
        workers (see below)

    tmp_dir:
        Directory where temporary HDF5 files will be stored
        (see below)

    n_processors:
        Number of writer workers (see below)

    Notes
    -----
    This function works by determining the number of rows
    that need to be written to the zarr file and dividing
    them up among n_processors writer workers.

    A single process then reads the data from the h5ad file
    in the order it is stored natively and feeds that chunk
    to the writers, who each determine which chunk of data
    they need.

    Each writer writes a temporary HDF5 file containing its
    chunk of CSR data. These HDF5 files are finally concatenated
    into the zarr file and deleted.
    """

    h5ad_path = pathlib.Path(h5ad_path)
    zarr_path = pathlib.Path(zarr_path)

    adata_metadata = _get_adata_metadata(h5ad_path)
    results = compute_row_order(
                obs_records=adata_metadata['obs'],
                column_hierarchy=taxonomy_hierarchy)

    row_order = results["row_order"]
    tree = results["tree"]

    zarr_tmp_dir = pathlib.Path(
                    tempfile.mkdtemp(
                        dir=tmp_dir,
                        prefix='zarr_scratch_'))

    try:
        rearrange_sparse_h5ad_hunter_gather(
            h5ad_path=h5ad_path,
            output_path=zarr_path,
            row_order=row_order,
            output_chunks=zarr_chunks,
            n_row_collectors=n_processors,
            write_buffer_size=write_buffer_size,
            read_buffer_size=read_buffer_size,
            tmp_dir=zarr_tmp_dir)

        metadata_path = zarr_path / "metadata.json"
        metadata = dict()
        metadata["mapped_row_order"] = [int(ii) for ii in row_order]
        metadata["taxonomy_tree"] = json_clean_dict(tree)
        metadata["h5ad_path"] = str(h5ad_path.resolve().absolute())
        metadata["shape"] = adata_metadata["shape"]
        metadata["row_names"] = [adata_metadata["row_names"][ii]
                                 for ii in row_order]
        metadata["col_names"] = adata_metadata["col_names"]
        with open(metadata_path, "w") as out_file:
            out_file.write(json.dumps(metadata))

    finally:
        _clean_up(zarr_tmp_dir)


def _get_adata_metadata(h5ad_path):
    """
    Get list of records from the obs DataFrame of
    an anndata h5ad file

    Also shape of X matrix
    """
    a_data = anndata.read_h5ad(h5ad_path, backed='r')
    obs = a_data.obs
    shape = a_data.X.shape
    obs_names = a_data.obs_names
    var_names = a_data.var_names
    return {"obs": obs.to_dict(orient='records'),
            "shape": [int(ii) for ii in shape],
            "row_names": list(obs_names),
            "col_names": list(var_names)}