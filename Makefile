# ----------------------------------------
# Make configuration
# ----------------------------------------

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
.SUFFIXES:
.SECONDARY:

TODAY = $(shell date +%Y-%m-%d)
BASE = https://ontology.iedb.org/ontology

ROBOT = java -Xmx8G -jar util/robot.jar

# IRI bases
NCBIT = http:\/\/purl\.obolibrary\.org\/obo\/NCBITaxon_
DOUBLE_NCBIT = http:\/\/purl\.obolibrary\.org\/obo\/NCBITaxon_\/NCBITaxon_
IEDB = http:\/\/iedb\.org\/taxon-protein\/
BAD_IEDB = http:\/\/iedb\.org\/taxon\/

# IEDB files
ORG_TREE = dependencies/organism-tree.owl
SUB_TREE = dependencies/subspecies-tree.owl
NP_TREE = dependencies/non-peptide-tree.owl

# Other important files
SOURCES = dependencies/source-parents.csv
PROTEINS = dependencies/parent-proteins.csv
PROTEOMES = dependencies/proteomes.tsv
ACTIVE_PROTEINS = temp/active-proteins.csv

# Directories
SCRIPTS = util/scripts
QUERIES = util/queries

# 'clean' task removes temp files and zips the build files
all: trees clean
trees: protein-tree.owl.gz molecule-tree.owl.gz

# THE STEPS

# Get the species that need updating
# - fix the parent-proteins table (to CSV)
# - compare new parent-proteins with parent-proteins-last
# - any species that has a new/removed/changed protein needs to be updated
# - build a protein table with just the species & proteins we care about
# For each species to update:
# - get a list of the proteins we care about (active proteins)
# - download the UniProt proteome files (RDF and FASTA)
# - generate the branch from the RDF file
# - filter for the top-level node + the active proteins
# Merge ALL species in build to generate protein-tree
# - add labels from parent-proteins
# - add synonyms from source-parents
# - fix duplicate labels & gzip
# - generate molecule-tree
# Clean up
# - remove temp directory
# - copy parent-proteins table -> parent-proteins-last & gzip

build build/branches dependencies temp:
	mkdir -p $@

# If the parent-proteins-last file does not exist, create an empty one
dependencies/parent-proteins-last.csv:
	touch $@

# If parent proteins is not given to us in CSV format,
# convert the format and make sure the fields match what we want
.PRECIOUS: $(PROTEINS)
$(PROTEINS): dependencies/parent_protein.tsv
	$(SCRIPTS)/convert-parent-proteins.py $< $@

# Do the same with the source-parents table
.PRECIOUS: $(SOURCES)
$(SOURCES): dependencies/source_parent.tsv
	$(SCRIPTS)/convert-source-parents.py $< $@

# Create an "active proteins" table by comparing the 
# last used parent-proteins table to the current one
.INTERMEDIATE: $(ACTIVE_PROTEINS)
$(ACTIVE_PROTEINS): $(PROTEINS) dependencies/parent-proteins-last.csv | temp
	$(SCRIPTS)/get-active-proteins.py $@ $^

# ----------------------------------------
# PROTEIN TREE
# ----------------------------------------

protein-tree.owl.gz: protein-tree.owl
	gzip $<

# The protein tree is a product of:
# - taxon-proteins: NCBITaxon classes as proteins
# - upper: top-level structure (material entity & protein)
# - iedb-proteins: bottom-level proteins used in IEDB

# the last step is to append UniProt IDs to duplicate labels
.PRECIOUS: protein-tree.owl
protein-tree.owl: temp/merged.owl
	$(SCRIPTS)/fix-duplicate-labels.py $< $@

.PRECIOUS: molecule-tree.owl.gz
molecule-tree.owl.gz: protein-tree.owl.gz $(NP_TREE)
	$(ROBOT) merge --input $< --input $(word 2,$^) \
	annotate --ontology-iri $(BASE)/$@\
	 --version-iri $(BASE)/$(TODAY)/$@ --output $@

clean: protein-tree.owl.gz molecule-tree.owl.gz
	rm -rf temp && \
	cp $(PROTEINS) dependencies/parent-proteins-last.csv

# ----------------------------------------
# PROTEOME BRANCHES
# ----------------------------------------

# Using the active proteins table, update the branches for each changed species
process-species: $(ACTIVE_PROTEINS) $(PROTEOMES) | build build/branches
	$(SCRIPTS)/update-branches.py $^

# Merge all archeobacterium branches
.PRECIOUS: build/branches/archeobacterium-branches.owl.gz
build/branches/archeobacterium-branches.owl.gz: build/archeobacterium\
 | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

# Merge all bacterium branches
.PRECIOUS: build/branches/bacterium-branches.owl.gz
build/branches/bacterium-branches.owl.gz: build/bacterium\
 | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

# Merge all other-eukaryote branches
.PRECIOUS: build/branches/other-eukaryote-branches.owl.gz
build/branches/other-eukaryote-branches.owl.gz: build/other-eukaryote\
 | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

# Merge all plant branches
.PRECIOUS: build/branches/plant-branches.owl.gz
build/branches/plant-branches.owl.gz: build/plant\
 | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

# Merge all vertebrate branches
.PRECIOUS: build/branches/vertebrate-branches.owl.gz
build/branches/vertebrate-branches.owl.gz: build/vertebrate\
 | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

# Merge all virus branches
.PRECIOUS: build/branches/virus-branches.owl.gz
build/branches/virus-branches.owl.gz: build/virus\
 | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

BRANCHES = build/branches/archeobacterium-branches.owl.gz \
build/branches/bacterium-branches.owl.gz \
build/branches/other-eukaryote-branches.owl.gz \
build/branches/plant-branches.owl.gz \
build/branches/vertebrate-branches.owl.gz \
build/branches/virus-branches.owl.gz

# Merge the top-level branches into a master file
.PRECIOUS: build/branches.owl.gz
build/branches.owl.gz: build/branches | $(BRANCHES)
	$(eval INPUTS := $(foreach I,$(shell ls $<), --input $</$(I)))
	$(ROBOT) merge $(INPUTS) --output $@

# ----------------------------------------
# DEPENDENCIES
# ----------------------------------------

$(SUB_TREE): | dependencies
	curl -Lk https://10.0.7.92/organisms/latest/temp/subspecies-tree.owl > $@

$(ORG_TREE): | dependencies
	curl -Lk https://10.0.7.92/organisms/latest/temp/organism-tree.owl > $@

$(NP_TREE): | dependencies
	curl -Lk https://10.0.7.92/arborist/results/non-peptide-tree.owl > $@

# ----------------------------------------
# PROTEIN-TREE INTERMEDIATES
# ----------------------------------------

# organism-proteins file contains classes from org tree as proteins
# updates the labels to append 'protein' to all classes
# removes the extra labels annotated with oboInOwl:hasLabelSource
.INTERMEDIATE: temp/organism-proteins.ttl
temp/organism-proteins.ttl: $(ORG_TREE) | temp
	$(ROBOT) filter --input $< --term OBI:0100026\
	 --select "descendants annotations" \
	query --update $(QUERIES)/rename.ru \
	remove --term oboInOwl:hasLabelSource --trim true --output $@

# upper file is just top-level structure for the protein tree
# creates 'protein' and 'material entity' classes
# asserts the top-level organism protein classes as SC of 'protein'
.INTERMEDIATE: temp/upper.ttl
temp/upper.ttl: temp/organism-proteins.ttl
	$(ROBOT) query --input $< --query $(QUERIES)/construct-upper.rq $@

# create protein synonyms from the source table
.INTERMEDIATE: temp/source-synonyms.ttl
temp/source-synonyms.ttl: $(SOURCES) $(PROTEINS) | temp
	$(SCRIPTS)/add-synonyms.py $^ $@

# IEDB proteins created from parent_protein table
# links the proteins to their organisms
# (organisms in the organism-proteins file)
.INTERMEDIATE: temp/iedb-proteins.ttl
temp/iedb-proteins.ttl: $(PROTEINS)| temp
	$(SCRIPTS)/parse-parents.py $< $@

# finds all NCBITaxon classes used by IEDB proteins as Proteome IDs
# use TDB on disk to speed up processing
.INTERMEDIATE: temp/ncbi-classes.tsv
temp/ncbi-classes.tsv: temp/iedb-proteins.ttl | temp
	$(ROBOT) query --input $< --tdb true --query $(QUERIES)/ncbi-classes.rq $@

# the following targets are used to fill in gaps between the organism-tree
# level proteins and the proteins used in the IEDB.

# get a list of NCBITaxon classes already in organism-based tree
.INTERMEDIATE: temp/included-classes.tsv
temp/included-classes.tsv: temp/organism-proteins.ttl | temp
	$(ROBOT) query --input $< --query $(QUERIES)/included-classes.rq $@

# create a list of classes MISSING from organism-based tree
.INTERMEDIATE: temp/missing-classes.txt
temp/missing-classes.txt: temp/included-classes.tsv temp/ncbi-classes.tsv | temp
	diff -w $< $(word 2,$^) | awk -F'"' '{print $$2}' | sed '/^$$/d' > $@

# filter the missing classes from subspecies tree, including their ancestors
# remove upper-level 'organism', 'root', 'other sequences', and 'unidentified'
# update to append 'protein' to all taxon labels 
.INTERMEDIATE: temp/taxon-proteins.owl
temp/taxon-proteins.owl: $(SUB_TREE) temp/missing-classes.txt \
 temp/organism-proteins.ttl | temp
	$(ROBOT) filter --input $< --term-file $(word 2,$^)\
	 --term rdfs:subClassOf --select "self ancestors annotations" \
	remove --term NCBITaxon:1 --term OBI:0100026 --term NCBITaxon:28384\
	 --term NCBITaxon:32644 --trim true \
	query --update $(QUERIES)/rename.ru \
	remove --term oboInOwl:hasLabelSource --trim true \
	merge --input $(word 3,$^) --output $@

# the following targets are the final intermediates for the PT

# merge the major intermediate products to generate the PT
# generate the OWL output with ontology annotations
# replace any NCBITaxon_ IRIs with IEDB
# fix incorrect IEDB IRIs
.INTERMEDIATE: temp/merged.owl
temp/merged.owl: temp/taxon-proteins.owl temp/upper.ttl \
 temp/iedb-proteins.ttl temp/source-synonyms.ttl build/branches.owl.gz
	$(eval INPUTS := $(foreach I,$^, --input $(I)))
	$(ROBOT) merge $(INPUTS) \
	annotate --ontology-iri $(BASE)/protein-tree.owl\
	 --version-iri $(BASE)/$(TODAY)/protein-tree.owl  --output $@ && \
	sed -i .bak 's/$(DOUBLE_NCBIT)/$(IEDB)/g' $@ && \
	sed -i .bak 's/$(NCBIT)/$(IEDB)/g' $@ && \
	sed -i .bak 's/$(BAD_IEDB)/$(IEDB)/g' $@ && \
	rm -f $@.bak

