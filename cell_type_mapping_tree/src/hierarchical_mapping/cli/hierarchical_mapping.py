import anndata
import argparse
import h5py
import json
import numpy as np
import os
import pathlib
import shutil
import tempfile
import time
import traceback

from hierarchical_mapping.utils.utils import (
    mkstemp_clean,
    _clean_up)

from hierarchical_mapping.cli.cli_log import (
    CommandLog)

from hierarchical_mapping.taxonomy.taxonomy_tree import (
    TaxonomyTree)

from hierarchical_mapping.diff_exp.precompute_from_anndata import (
    precompute_summary_stats_from_h5ad)

from hierarchical_mapping.diff_exp.markers import (
    find_markers_for_all_taxonomy_pairs)

from hierarchical_mapping.type_assignment.marker_cache_v2 import (
    create_marker_gene_cache_v2)

from hierarchical_mapping.type_assignment.election import (
    run_type_assignment_on_h5ad)


def run_mapping(config, output_path, log_path=None):

    log = CommandLog()

    if 'tmp_dir' not in config:
        raise RuntimeError("did not specify tmp_dir")

    tmp_dir = tempfile.mkdtemp(dir=config['tmp_dir'])

    output = dict()

    output_path = pathlib.Path(output_path)
    if log_path is not None:
        log_path = pathlib.Path(log_path)

    # check validity of output_path and log_path
    for pth in (output_path, log_path):
        if pth is not None:
            if not pth.exists():
                try:
                    with open(pth, 'w') as out_file:
                        out_file.write('junk')
                    pth.unlink()
                except FileNotFoundError:
                    raise RuntimeError(
                        "unable to write to "
                        f"{pth.resolve().absolute()}")

    try:
        type_assignment = _run_mapping(
            config=config,
            tmp_dir=tmp_dir,
            log=log)
        output["results"] = type_assignment["assignments"]
        output["marker_genes"] = type_assignment["marker_genes"]
        log.info("RAN SUCCESSFULLY")
    except Exception:
        traceback_msg = "an ERROR occurred ===="
        traceback_msg += f"\n{traceback.format_exc()}\n"
        log.add_msg(traceback_msg)
        raise
    finally:
        _clean_up(tmp_dir)
        log.info("CLEANING UP")
        if log_path is not None:
            log.write_log(log_path)
        output["config"] = config
        output["log"] = log.log
        with open(output_path, "w") as out_file:
            out_file.write(json.dumps(output, indent=2))


def _run_mapping(config, tmp_dir, log):

    t0 = time.time()
    validation_result = _validate_config(
            config=config,
            tmp_dir=tmp_dir,
            log=log)

    query_tmp = validation_result['query_tmp']
    precomputed_path = validation_result['precomputed_path']
    precomputed_tmp = validation_result['precomputed_tmp']
    precomputed_is_valid = validation_result['precomputed_is_valid']
    reference_marker_path = validation_result['reference_marker_path']
    reference_marker_tmp = validation_result['reference_marker_tmp']
    reference_marker_is_valid = validation_result['reference_marker_is_valid']

    reference_marker_config = config["reference_markers"]
    precomputed_config = config["precomputed_stats"]
    query_marker_config = config["query_markers"]
    type_assignment_config = config["type_assignment"]

    log.benchmark(msg="validating config and copying data",
                  duration=time.time()-t0)

    # ========= precomputed stats =========

    if precomputed_is_valid:
        log.info(f"using {precomputed_tmp} for precomputed_stats")
    else:
        log.info("creating precomputed stats file")

        reference_path = pathlib.Path(
            precomputed_config['reference_path'])

        ref_tmp = pathlib.Path(
            tempfile.mkdtemp(
                prefix='reference_data_',
                dir=tmp_dir))

        (reference_path,
         _) = _copy_over_file(file_path=reference_path,
                              tmp_dir=ref_tmp,
                              log=log)

        if 'column_hierarchy' in precomputed_config:
            column_hierarchy = precomputed_config['column_hierarchy']
            taxonomy_tree = None
        else:
            taxonomy_tree = TaxonomyTree.from_json_file(
                json_path=precomputed_config['taxonomy_tree'])
            column_hierarchy = None

        t0 = time.time()
        precompute_summary_stats_from_h5ad(
            data_path=reference_path,
            column_hierarchy=column_hierarchy,
            taxonomy_tree=taxonomy_tree,
            output_path=precomputed_tmp,
            rows_at_a_time=10000,
            normalization=precomputed_config['normalization'])
        log.benchmark(msg="precomputing stats",
                      duration=time.time()-t0)

        if precomputed_path is not None:
            log.info("copying precomputed stats from "
                     f"{precomputed_tmp} to {precomputed_path}")
            shutil.copy(
                src=precomputed_tmp,
                dst=precomputed_path)

        _clean_up(ref_tmp)

    log.info(f"reading taxonomy_tree from {precomputed_tmp}")
    with h5py.File(precomputed_tmp, "r") as in_file:
        taxonomy_tree = TaxonomyTree.from_str(
            serialized_dict=in_file["taxonomy_tree"][()].decode("utf-8"))

    # ========= reference marker cache =========

    if reference_marker_is_valid:
        log.info(f"using {reference_marker_tmp} for reference markers")
    else:
        log.info("creating reference marker file")

        marker_tmp = tempfile.mkdtemp(
            dir=tmp_dir,
            prefix='reference_marker_')

        t0 = time.time()
        find_markers_for_all_taxonomy_pairs(
            precomputed_stats_path=precomputed_tmp,
            taxonomy_tree=taxonomy_tree,
            output_path=reference_marker_tmp,
            tmp_dir=marker_tmp,
            n_processors=reference_marker_config['n_processors'],
            max_bytes=reference_marker_config['max_bytes'])

        log.benchmark(msg="finding reference markers",
                      duration=time.time()-t0)

        _clean_up(marker_tmp)
        if reference_marker_path is not None:
            log.info(f"copying reference markers from "
                     "{reference_marker_tmp} to "
                     f"{reference_marker_path}")
            shutil.copy(
                src=reference_marker_tmp,
                dst=reference_marker_path)

    # ========= query marker cache =========

    query_marker_tmp = pathlib.Path(
        mkstemp_clean(dir=tmp_dir,
                      prefix='query_marker_',
                      suffix='.h5'))

    t0 = time.time()
    create_marker_gene_cache_v2(
        output_cache_path=query_marker_tmp,
        input_cache_path=reference_marker_tmp,
        query_gene_names=_get_query_gene_names(query_tmp),
        taxonomy_tree=taxonomy_tree,
        n_per_utility=query_marker_config['n_per_utility'],
        n_processors=query_marker_config['n_processors'],
        behemoth_cutoff=5000000)
    log.benchmark(msg="creating query marker cache",
                  duration=time.time()-t0)

    # ========= type assignment =========

    t0 = time.time()
    rng = np.random.default_rng(type_assignment_config['rng_seed'])
    result = run_type_assignment_on_h5ad(
        query_h5ad_path=query_tmp,
        precomputed_stats_path=precomputed_tmp,
        marker_gene_cache_path=query_marker_tmp,
        taxonomy_tree=taxonomy_tree,
        n_processors=type_assignment_config['n_processors'],
        chunk_size=type_assignment_config['chunk_size'],
        bootstrap_factor=type_assignment_config['bootstrap_factor'],
        bootstrap_iteration=type_assignment_config['bootstrap_iteration'],
        rng=rng,
        normalization=type_assignment_config['normalization'])
    log.benchmark(msg="assigning cell types",
                  duration=time.time()-t0)

    # ========= copy marker gene lookup over to output file =========
    log.info("Writing marker genes to output file")
    marker_gene_lookup = dict()
    with h5py.File(query_marker_tmp, "r") as src:
        reference_gene_names = json.loads(
            src['reference_gene_names'][()].decode('utf-8'))
        for level in taxonomy_tree.hierarchy[:-1]:
            for node in taxonomy_tree.nodes_at_level(level):
                grp_key = f"{level}/{node}"
                ref_idx = src[grp_key]['reference'][()]
                marker_gene_lookup[grp_key] = [
                    str(reference_gene_names[ii]) for ii in ref_idx]

        grp_key = "None"
        ref_idx = src[grp_key]['reference'][()]
        marker_gene_lookup[grp_key] = [
            str(reference_gene_names[ii]) for ii in ref_idx]

    return {'assignments': result, 'marker_genes': marker_gene_lookup}


def _validate_config(
        config,
        tmp_dir,
        log):

    result = dict()

    if "query_path" not in config:
        log.error("'query_path' not in config")

    if "precomputed_stats" not in config:
        log.error("'precomputed_stats' not in config")

    if "reference_markers" not in config:
        log.error("'reference_markers' not in config")

    if "query_markers" not in config:
        log.error("'query_markers' not in config")

    if "type_assignment" not in config:
        log.error("'type_assignment' not in config")

    _check_config(
        config_dict=config["type_assignment"],
        config_name="type_assignment",
        key_name=['n_processors',
                  'chunk_size',
                  'bootstrap_factor',
                  'bootstrap_iteration',
                  'rng_seed',
                  'normalization'],
        log=log)

    (query_tmp,
     query_is_valid) = _copy_over_file(
         file_path=config["query_path"],
         tmp_dir=tmp_dir,
         log=log)

    if not query_is_valid:
        log.error(
            f"{config['query_path']} is not a valid file")

    result['query_tmp'] = query_tmp

    reference_marker_config = config["reference_markers"]

    precomputed_config = config["precomputed_stats"]
    lookup = _make_temp_path(
        config_dict=precomputed_config,
        tmp_dir=tmp_dir,
        log=log,
        prefix="precomputed_stats_",
        suffix=".h5")

    precomputed_path = lookup["path"]
    precomputed_tmp = lookup["tmp"]
    precomputed_is_valid = lookup["is_valid"]

    result['precomputed_path'] = precomputed_path
    result['precomputed_tmp'] = precomputed_tmp
    result['precomputed_is_valid'] = precomputed_is_valid

    if not precomputed_is_valid:
        _check_config(
            config_dict=precomputed_config,
            config_name='precomputed_config',
            key_name=['reference_path', 'normalization'],
            log=log)

        has_columns = 'column_hierarchy' in precomputed_config
        has_taxonomy = 'taxonomy_tree' in precomputed_config

        if has_columns and has_taxonomy:
            log.error(
                "Cannot specify both column_hierarchy and "
                "taxonomy_tree in precomputed_config")

        if not has_columns and not has_taxonomy:
            log.error(
                "Must specify one of column_hierarchy or "
                "taxonomy_tree in precomputed_config")

    reference_marker_config = config["reference_markers"]
    lookup = _make_temp_path(
        config_dict=reference_marker_config,
        tmp_dir=tmp_dir,
        log=log,
        prefix="reference_markers_",
        suffix=".h5")

    reference_marker_path = lookup["path"]
    reference_marker_tmp = lookup["tmp"]
    reference_marker_is_valid = lookup["is_valid"]
    result['reference_marker_path'] = reference_marker_path
    result['reference_marker_tmp'] = reference_marker_tmp
    result['reference_marker_is_valid'] = reference_marker_is_valid

    if not reference_marker_is_valid:
        _check_config(
            config_dict=reference_marker_config,
            config_name='reference_markers',
            key_name=['n_processors', 'max_bytes'],
            log=log)

    query_marker_config = config["query_markers"]
    _check_config(
        config_dict=query_marker_config,
        config_name="query_markers",
        key_name=['n_per_utility', 'n_processors'],
        log=log)

    return result


def _copy_over_file(file_path, tmp_dir, log):
    """
    If a file exists, copy it into the tmp_dir.

    Parameters
    ----------
    file_path:
        the path to the file we are considering
    tmp_dir:
        the path to the fast tmp_dir
    log:
        CommandLog to record actions

    Returns
    -------
    new_path:
        Where the file was copied (even if file was not copied,
        return a to a file in tmp_dir)

    valid:
        boolean indicating whether this file can be used (True)
        or if it is just a placeholder (False)
    """
    file_path = pathlib.Path(file_path)
    tmp_dir = pathlib.Path(tmp_dir)
    new_path = mkstemp_clean(
            dir=tmp_dir,
            prefix=f"{file_path.name.replace(file_path.suffix, '')}_",
            suffix=file_path.suffix)

    is_valid = False
    if file_path.exists():
        if not file_path.is_file():
            log.error(
                f"{file_path} exists but is not a file")
        else:
            t0 = time.time()
            log.info(f"copying {file_path}")
            shutil.copy(src=file_path, dst=new_path)
            duration = time.time()-t0
            log.info(f"copied {file_path} to {new_path} "
                     f"in {duration:.4e} seconds")
            is_valid = True
    else:
        # check that we can write the specified file
        try:
            with open(file_path, 'w') as out_file:
                out_file.write("junk")
            file_path.unlink()
        except FileNotFoundError:
            raise RuntimeError(
                "could not write to "
                f"{file_path.resolve().absolute()}")

    return new_path, is_valid


def _make_temp_path(
        config_dict,
        tmp_dir,
        log,
        suffix,
        prefix):
    """
    Create a temp path for an actual file.

    Returns
    -------
    {'tmp': tmp_path created
     'path': path in actual storage (can be None)
     'is_valid': True if 'path' exists; False if must be created}
    """

    if "path" in config_dict:
        file_path = pathlib.Path(
            config_dict["path"])
        (tmp_path,
         is_valid) = _copy_over_file(
                 file_path=file_path,
                 tmp_dir=tmp_dir,
                 log=log)
    else:
        tmp_path = pathlib.Path(
            mkstemp_clean(
                dir=tmp_dir,
                prefix=prefix,
                suffix=suffix))
        is_valid = False
        file_path = None

    return {'tmp': tmp_path,
            'path': file_path,
            'is_valid': is_valid}


def _check_config(config_dict, config_name, key_name, log):
    if isinstance(key_name, list):
        for el in key_name:
            _check_config(
                config_dict=config_dict,
                config_name=config_name,
                key_name=el,
                log=log)
    else:
        if key_name not in config_dict:
            log.error(f"'{config_name}' config missing key '{key_name}'")


def _get_query_gene_names(query_gene_path):
    a_data = anndata.read_h5ad(query_gene_path, backed='r')
    gene_names = list(a_data.var_names)
    return gene_names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_path', type=str, default=None)
    parser.add_argument('--result_path', type=str, default=None)
    parser.add_argument('--log_path', type=str, default=None)
    parser.add_argument('--local_tmp', default=False, action='store_true')
    args = parser.parse_args()

    with open(args.config_path, 'rb') as in_file:
        config = json.load(in_file)

    if args.local_tmp:
        config['tmp_dir'] = os.environ['TMPDIR']

    run_mapping(
        config=config,
        output_path=args.result_path,
        log_path=args.log_path)


if __name__ == "__main__":
    main()