python -m cell_type_mapper.cli.precompute_stats_abc \
--hierarchy '["class", "subclass", "cluster"]' \
--output_path '/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/temp' \
--h5ad_path_list '[ \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10XMulti/20230830/WMB-10XMulti-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv2/20230630/WMB-10Xv2-CTXsp-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv2/20230630/WMB-10Xv2-HPF-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv2/20230630/WMB-10Xv2-HY-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-1-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-2-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-3-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv2/20230630/WMB-10Xv2-Isocortex-4-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv2/20230630/WMB-10Xv2-MB-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv2/20230630/WMB-10Xv2-OLF-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv2/20230630/WMB-10Xv2-TH-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-CB-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-CTXsp-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-HPF-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-HY-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-Isocortex-1-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-Isocortex-2-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-MB-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-MY-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-OLF-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-PAL-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-P-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-STR-raw.h5ad", \
"/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/expression_matrices/WMB-10Xv3/20230630/WMB-10Xv3-TH-raw.h5ad", \
]' \
--cell_metadata_path '/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/metadata/WMB-10X/20230830/cell_metadata.csv' \
--cluster_annotation_path '/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/metadata/WMB-taxonomy/20230830/cluster_annotation_term.csv' \
--cluster_membership_path '/home/david/data/sc-rna-seq/data_atlas/mus_musculus/allen-brain-cell-atlas/metadata/WMB-taxonomy/20230830/cluster_to_cluster_annotation_membership.csv'
