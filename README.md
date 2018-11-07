# IEDB Protein Tree

James A. Overton [james@overton.ca](mailto:james@overton.ca)
Rebecca Tauber [rctauber@gmail.com](mailto:rctauber@gmail.com)

The IEDB Molecule Finder includes all species and ancestors from the organism tree, plus proteins from their reference proteomes.

## Status

This code is a revised version of the protein tree, designed to replace the legacy protein tree code. 

It generates three different products:

* `protein-tree.owl.gz`
* `molecule-tree.owl.gz`
* `branches.owl.gz`

## Requirements

* a Unix system (Linux, macOS)
* GNU Make 3.81+
* Python 3.6 with the `rdflib` package
* Java 8 for running [ROBOT](http://robot.obolibrary.org/)

## Usage

To make all three products, run:
```
make all
```

### Protein and Molecule Trees

The process generates the protein tree from various tabular inputs and merges with the legacy non-peptide tree to create the molecule tree. The necessary dependencies that **must be manually added** are:

* `dependencies/parent_protein.tsv` assignments of proteins referenced in the IEDB and their parent proteomes
* `dependencies/source_parent.tsv` assignments of all sources to reference proteins from the reference proteomes
* `dependencies/proteome.tsv` assignments of proteome species to their proteome IDs

The other dependencies are automatically retrieved with `curl`:

* `dependencies/organism-tree.owl` nodes for all taxa used by the IEDB
* `dependencies/subspecies-tree.owl` organism tree plus all ranks used by the IEDB
* `dependencies/non-peptide-tree.owl` non-peptide molecular entities
<!-- * `dependencies/active-species.tsv` -->

The protein and molecule trees can be created with:
```
make trees
```

### Branches

The full `branches.owl` file contains all species protein branches. These are build from their UniProt reference proteomes. This process works with any species that has a reference protein, specified by `dependencies/proteomes.tsv`.
<!--
Each time a new parent-protein table is used to run a build (`dependencies/parent_protein.tsv`), a new proteome for a species in the organism tree will be fetched only if its proteins in the parent-protein table have changed. If these proteins have changed, an updated reference proteome will be downloaded from UniProt and used to rebuild the branch node for that species.
-->
An update for a specific branch can be forced by deleting the file corresponding with the proteome species label and running:
```
make branches
```

## To Do

* Support auto-update of branch nodes when they change in `parent_protein.tsv`
