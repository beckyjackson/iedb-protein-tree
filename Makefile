# ----------------------------------------
# Make configuration
# ----------------------------------------

MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
.SUFFIXES:
.SECONDARY:

TODAY = $(shell date +%Y-%m-%d)
BASE = https://ontology.iedb.org/ontology

# IRI bases
NCBIT = http:\/\/purl\.obolibrary\.org\/obo\/NCBITaxon_
IEDB = http:\/\/iedb\.org\/taxon-protein\/

# IEDB files
ORG_TREE = build/organism-tree.owl
SUB_TREE = build/subspecies-tree.owl
PROTEIN_TABLE = build/parent-proteins.csv

# ----------------------------------------
# PROTEIN TREE
# ----------------------------------------

all: protein-tree.owl clean

.PRECIOUS: protein-tree.owl
protein-tree.owl: build/all-classes.owl build/upper.ttl build/iedb-proteins.ttl
	robot merge --input $< --input $(word 2,$^) --input $(word 3,$^) \
	annotate --ontology-iri $(BASE)/$@\
	 --version-iri $(BASE)/$(TODAY)/$@  --output $@.tmp.owl && \
	sed 's/$(NCBIT)/$(IEDB)/g'\
	 $@.tmp.owl > $@ && rm $@.tmp.owl

clean: protein-tree.owl
	rm -rf build

# ----------------------------------------
# DEPENDENCIES
# ----------------------------------------

.PHONY: build
build:
	mkdir -p $@

$(PROTEIN_TABLE): | build
	curl -LkO https://10.0.7.92/arborist/results/parent-proteins.csv.zip && \
	unzip parent-proteins.csv.zip && \
	mv results/parent-proteins.csv $@ && \
	rm -rf results parent-proteins.csv.zip

$(SUB_TREE): | build
	curl -Lk https://10.0.7.92/organisms/latest/build/subspecies-tree.owl > $@

$(ORG_TREE): | build
	curl -Lk https://10.0.7.92/organisms/latest/build/organism-tree.owl > $@

# ----------------------------------------
# INTERMEDIATES
# ----------------------------------------

# org-proteins file contains 'protein' classes from organism tree
.INTERMEDIATE: build/org-proteins.ttl
build/org-proteins.ttl: $(ORG_TREE) | build
	robot filter --input $< --term OBI:0100026\
	 --select "descendants annotations" \
	query --update util/rename.ru --output $@

# upper file is just top-level structure for the protein tree
.INTERMEDIATE: build/upper.ttl
build/upper.ttl: build/org-proteins.ttl | build
	robot query --input $< --query util/construct-upper.rq $@

# IEDB proteins created from parent-proteins table
# links the proteins to their organisms
.INTERMEDIATE: build/iedb-proteins.ttl
build/iedb-proteins.ttl: | build
	python util/parse-parents.py

# get a list of the NCBITaxon classes used by IEDB proteins
.INTERMEDIATE: build/ncbi-classes.tsv
build/ncbi-classes.tsv: build/iedb-proteins.ttl util/ncbi-classes.rq | build
	robot query --input $< --query $(word 2,$^) $@

# get a list of NCBITaxon classes already in organism-based tree
.INTERMEDIATE: build/included-classes.tsv
build/included-classes.tsv: build/org-proteins.ttl util/included-classes.rq | build
	robot query --input $< --query $(word 2,$^) $@

# create a list of classes MISSING from organism-based tree
.INTERMEDIATE: build/missing-classes.txt
build/missing-classes.txt: build/included-classes.tsv build/ncbi-classes.tsv | build
	diff -w $< $(word 2,$^) | awk -F'"' '{print $$2}' | sed '/^$$/d' > $@

# fill in the missing classes from the subspecies tree
.INTERMEDIATE: build/all-classes.owl
build/all-classes.owl: $(SUB_TREE) build/missing-classes.txt build/org-proteins.ttl | build
	robot filter --input $< --term-file $(word 2,$^)\
	 --term rdfs:subClassOf --select "self ancestors annotations" \
	remove --term NCBITaxon:1 --term OBI:0100026 --term NCBITaxon:28384\
	 --term NCBITaxon:32644 --trim true \
	query --update util/rename.ru merge --input $(word 3,$^) --output $@
