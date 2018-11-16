
# IEDB Protein Tree

James A. Overton [james@overton.ca](mailto:james@overton.ca)<br>
Rebecca Tauber [rctauber@gmail.com](mailto:rctauber@gmail.com)

The IEDB Molecule Finder includes all species and ancestors from the organism tree, plus proteins from their reference proteomes.

## Status

This code is a revised version of the protein tree, designed to replace the legacy protein tree code. 

It generates two different products:

* `protein-tree.owl.gz` proteins used in IEDB linked to their NCBITaxon organism species
* `molecule-tree.owl.gz` protein tree plus non-peptide tree

## Requirements

* a Unix system (Linux, macOS)
* GNU Make 3.81+
* Python 3.6 with the `rdflib` package
* Java 8 for running [ROBOT](http://robot.obolibrary.org/)

## Usage

To make all products, run:
```
make all
```
This will generate the gzipped versions of both trees, and then clean up the intermediate build files.

To create the protein and molecule trees without removing the intermediate build files, use:
```
make trees
```

### Protein and Molecule Trees

The process generates the protein tree from various tabular inputs and merges with the legacy non-peptide tree to create the molecule tree. The necessary dependencies that **must be manually added** are:

* `dependencies/parent_protein.tsv` assignments of proteins referenced in the IEDB and their parent proteomes
    * Used to generate `dependencides/parent-proteins.csv` 
* `dependencies/source_parent.tsv` assignments of all sources to reference proteins from the reference proteomes
    * Used to generate `dependencies/source-parents.csv`
* `dependencies/proteomes.tsv` assignments of proteome species to their proteome IDs

The other dependencies are automatically retrieved with `curl` (force update by deleting):

* `dependencies/organism-tree.owl` nodes for all taxa used by the IEDB
* `dependencies/subspecies-tree.owl` organism tree plus all ranks used by the IEDB
* `dependencies/non-peptide-tree.owl` non-peptide molecular entities

### Intermediate Products

All products here are generated in the `temp` directory.

* `organism-proteins.ttl` all classes from `organism-tree.owl` as proteins
* `upper.ttl` top-level structure for proteins including 'protein' and 'material entity'
* `source-synonyms.ttl` synonyms as annotations from `source-parents.csv`
* `iedb-proteins.ttl` proteins from `parent-proteins.csv` as subclasses of their species protein
* `ncbi-classes.tsv` all NCBITaxon classes used by IEDB proteins as proteome IDs
* `included-classes.tsv` table of NCBITaxon species included in `organism-proteins.ttl`
* `missing-classes.txt` list of NCBITaxon species NOT included in `organism-proteins.ttl`, but used in `iebd-proteins.ttl`
* `taxon-proteins.owl` missing subspecies (in `missing-classes.txt`) filtered from  `subspecies-tree.owl`
* `merged.owl` combination of `taxon-proteins.owl`, `upper.ttl`, `iedb-proteins.ttl`, `source-synonyms.ttl`, and `branches.owl.gz` (see below)

### Branches

The full `branches.owl.gz` file contains all species protein branches. These are build from their UniProt reference proteomes. This process works with any species that has a reference protein, specified by `dependencies/proteomes.tsv`. This file is merged into the protein tree to include all details about a species proteome.

Each time a new parent-protein table is used to run a build (`dependencies/parent_protein.tsv`), a new proteome for a species in the organism tree will be fetched only if its proteins in the parent-protein table have changed. If these proteins have changed, an updated reference proteome will be downloaded from UniProt and used to rebuild the branch node for that species.

After the build is over, the `dependencies/parent-proteins.csv` file is copied to `dependencies/parent-proteins-last.csv`. If this file *does not exist*, all proteomes will be re-downloaded. When a new parent-proteins table is generated or added, it is compared to the `-last` version to find differences in proteins.
