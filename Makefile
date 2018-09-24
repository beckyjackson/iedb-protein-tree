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
ORG_TREE = dependencies/organism-tree.owl
SUB_TREE = dependencies/subspecies-tree.owl
PROTEIN_TABLE = dependencies/parent-proteins.csv

# ----------------------------------------
# PROTEIN TREE
# ----------------------------------------

all: protein-tree.owl clean

# The protein tree is a product of:
# - taxon-proteins: NCBITaxon classes as proteins
# - upper: top-level structure (material entity & protein)
# - iedb-proteins: bottom-level proteins used in IEDB
.PRECIOUS: protein-tree.owl
protein-tree.owl: build/taxon-proteins.owl build/upper.ttl \
 build/iedb-proteins.ttl
	robot merge --input $< --input $(word 2,$^) --input $(word 3,$^) \
	query --update util/fix-species.ru \
	annotate --ontology-iri $(BASE)/$@\
	 --version-iri $(BASE)/$(TODAY)/$@  --output $@ && \
	sed -i .bak 's/$(NCBIT)/$(IEDB)/g' $@ && \
	rm -f $@.bak

clean: protein-tree.owl
	rm -rf build

# only use this to reset the dependencies
clean_all:
	rm -rf build dependencies

# ----------------------------------------
# DEPENDENCIES
# ----------------------------------------

init: build dependencies
build dependencies:
	mkdir -p $@

$(PROTEIN_TABLE): | init
	curl -LkO https://10.0.7.92/arborist/results/parent-proteins.csv.zip && \
	unzip parent-proteins.csv.zip && \
	mv results/parent-proteins.csv $@ && \
	rm -rf results parent-proteins.csv.zip

$(SUB_TREE): | init
	curl -Lk https://10.0.7.92/organisms/latest/build/subspecies-tree.owl > $@

$(ORG_TREE): | init
	curl -Lk https://10.0.7.92/organisms/latest/build/organism-tree.owl > $@

# ----------------------------------------
# INTERMEDIATES
# ----------------------------------------

# organism-proteins file contains 'protein' classes from organism tree
.INTERMEDIATE: build/organism-proteins.ttl
build/organism-proteins.ttl: $(ORG_TREE) | init
	robot filter --input $< --term OBI:0100026\
	 --select "descendants annotations" \
	query --update util/rename.ru --output $@

# upper file is just top-level structure for the protein tree
.INTERMEDIATE: build/upper.ttl
build/upper.ttl: build/organism-proteins.ttl
	robot query --input $< --query util/construct-upper.rq $@

# IEDB proteins created from parent-proteins table
# links the proteins to their organisms
.INTERMEDIATE: build/iedb-proteins.ttl
build/iedb-proteins.ttl: $(PROTEIN_TABLE)| init
	python util/parse-parents.py

# get a list of the NCBITaxon classes used by IEDB proteins as Proteome IDs
.INTERMEDIATE: build/ncbi-classes.tsv
build/ncbi-classes.tsv: build/iedb-proteins.ttl
	robot query --input $< --query util/ncbi-classes.rq $@

# the following targets are used to fill in gaps between the organism-tree
# level proteins and the proteins used in the IEDB.

# get a list of NCBITaxon classes already in organism-based tree
.INTERMEDIATE: build/included-classes.tsv
build/included-classes.tsv: build/organism-proteins.ttl
	robot query --input $< --query util/included-classes.rq $@

# create a list of classes MISSING from organism-based tree
.INTERMEDIATE: build/missing-classes.txt
build/missing-classes.txt: build/included-classes.tsv build/ncbi-classes.tsv
	diff -w $< $(word 2,$^) | awk -F'"' '{print $$2}' | sed '/^$$/d' > $@

# fill in the missing classes from the subspecies tree
.INTERMEDIATE: build/taxon-proteins.owl
build/taxon-proteins.owl: $(SUB_TREE) build/missing-classes.txt \
 build/organism-proteins.ttl
	robot filter --input $< --term-file $(word 2,$^)\
	 --term rdfs:subClassOf --select "self ancestors annotations" \
	remove --term NCBITaxon:1 --term OBI:0100026 --term NCBITaxon:28384\
	 --term NCBITaxon:32644 --trim true \
	query --update util/rename.ru merge --input $(word 3,$^) --output $@
