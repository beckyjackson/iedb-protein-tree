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

ROBOT = java $(ROBOT_JAVA_ARGS) -jar util/robot.jar

# IRI bases
NCBIT = http:\/\/purl\.obolibrary\.org\/obo\/NCBITaxon_
IEDB = http:\/\/iedb\.org\/taxon-protein\/
BAD_IEDB = http:\/\/iedb\.org\/taxon\/

# IEDB files
ORG_TREE = dependencies/organism-tree.owl
SUB_TREE = dependencies/subspecies-tree.owl
NP_TREE = dependencies/non-peptide-tree.owl
PROTEIN_TABLE = dependencies/parent-proteins.tsv
ACTIVE_TABLE = dependencies/active-species.tsv
PROTEOME_TABLE = dependencies/proteomes.tsv

all: protein-tree.owl.gz molecule-tree.owl.gz branches clean

# ----------------------------------------
# PROTEIN TREE
# ----------------------------------------

# compress files at the end
protein-tree.owl.gz: protein-tree.owl | molecule-tree.owl
	gzip $<

molecule-tree.owl.gz: molecule-tree.owl
	gzip $<

# The protein tree is a product of:
# - taxon-proteins: NCBITaxon classes as proteins
# - upper: top-level structure (material entity & protein)
# - iedb-proteins: bottom-level proteins used in IEDB
.PRECIOUS: protein-tree.owl
protein-tree.owl: temp/taxon-proteins.owl temp/upper.ttl \
 temp/iedb-proteins.ttl
	$(ROBOT) merge --input $< --input $(word 2,$^)\
	 --input $(word 3,$^) --output temp/protein-tree.ttl && \
	$(ROBOT) query --input temp/protein-tree.ttl --tdb true\
	 --update util/fix-species.ru --output temp/protein-tree.ttl && \
	$(ROBOT) annotate --input temp/protein-tree.ttl --ontology-iri $(BASE)/$@\
	 --version-iri $(BASE)/$(TODAY)/$@  --output $@ && \
	sed -i .bak 's/$(NCBIT)/$(IEDB)/g' $@ && \
	sed -i .bak 's/$(BAD_IEDB)/$(IEDB)/g' $@ && \
	rm -f $@.bak

.PRECIOUS: molecule-tree.owl
molecule-tree.owl: protein-tree.owl $(NP_TREE)
	$(ROBOT) merge --input $< --input $(word 2,$^) \
	annotate --ontology-iri $(BASE)/$@\
	 --version-iri $(BASE)/$(TODAY)/$@ --output $@

clean: protein-tree.owl.gz molecule-tree.owl.gz
	rm -rf temp

# ----------------------------------------
# PROTEOME BRANCHES
# ----------------------------------------

branches: build/branches.owl.gz

# create a dir for each species containing:
# - FASTA and RDF proteome files from UniProt
# - A TTL representation of the proteome
# - A parent-proteins table for the proteome
process-species: $(PROTEOME_TABLE) | build build/branches
	util/build-species-proteome.py $<

build/branches:
	mkdir -p $@

BRANCHES = build/branches/archeobacterium-branches.owl.gz \
build/branches/bacterium-branches.owl.gz \
build/branches/other-eukaryote-branches.owl.gz \
build/branches/plant-branches.owl.gz \
build/branches/vertebrate-branches.owl.gz \
build/branches/virus-branches.owl.gz

.PRECIOUS: build/branches/archeobacterium-branches.owl.gz
build/branches/archeobacterium-branches.owl.gz: build/archeobacterium | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

.PRECIOUS: build/branches/bacterium-branches.owl.gz
build/branches/bacterium-branches.owl.gz: build/bacterium | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

.PRECIOUS: build/branches/other-eukaryote-branches.owl.gz
build/branches/other-eukaryote-branches.owl.gz: build/other-eukaryote | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

.PRECIOUS: build/branches/plant-branches.owl.gz
build/branches/plant-branches.owl.gz: build/plant | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

.PRECIOUS: build/branches/vertebrate-branches.owl.gz
build/branches/vertebrate-branches.owl.gz: build/vertebrate | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

.PRECIOUS: build/branches/virus-branches.owl.gz
build/branches/virus-branches.owl.gz: build/virus | process-species build/branches
	$(eval INPUTS := $(foreach I,$(shell ls $</*/branch.ttl), --input $(I)))
	$(ROBOT) merge $(INPUTS) --output $@

.PRECIOUS: build/branches.owl.gz
build/branches.owl.gz: build/branches | $(BRANCHES)
	$(eval INPUTS := $(foreach I,$(shell ls $<), --input $</$(I)))
	$(eval ROBOT_JAVA_ARTS=-Xmx4G)
	$(ROBOT) merge $(INPUTS) --output $@

# ----------------------------------------
# DEPENDENCIES
# ----------------------------------------

build:
	mkdir -p $@

temp:
	mkdir -p $@

dependencies:
	mkdir -p $@

#$(PROTEIN_TABLE): | dependencies

$(ACTIVE_TABLE): | dependencies
	curl -Lk https://10.0.7.92/organisms/latest/temp/active-species.tsv > $@

$(SUB_TREE): | dependencies
	curl -Lk https://10.0.7.92/organisms/latest/temp/subspecies-tree.owl > $@

$(ORG_TREE): | dependencies
	curl -Lk https://10.0.7.92/organisms/latest/temp/organism-tree.owl > $@

$(NP_TREE): | dependencies
	curl -Lk https://10.0.7.92/arborist/results/non-peptide-tree.owl > $@

# build a table to link species and proteome IDs
$(PROTEOME_TABLE): $(PROTEIN_TABLE) $(ACTIVE_TABLE)
	util/build-proteome-table.py $^ $@

# ----------------------------------------
# PROTEIN-TREE INTERMEDIATES
# ----------------------------------------

# organism-proteins file contains 'protein' classes from organism tree
.INTERMEDIATE: temp/organism-proteins.ttl
temp/organism-proteins.ttl: $(ORG_TREE) | temp
	$(ROBOT) filter --input $< --term OBI:0100026\
	 --select "descendants annotations" \
	query --update util/rename.ru \
	remove --term oboInOwl:hasLabelSource --trim true --output $@

# upper file is just top-level structure for the protein tree
.INTERMEDIATE: temp/upper.ttl
temp/upper.ttl: temp/organism-proteins.ttl
	$(ROBOT) query --input $< --query util/construct-upper.rq $@

# IEDB proteins created from parent-proteins table
# links the proteins to their organisms
.INTERMEDIATE: temp/iedb-proteins.ttl
temp/iedb-proteins.ttl: $(PROTEIN_TABLE)| temp
	python util/parse-parents.py $< $@

# get a list of the NCBITaxon classes used by IEDB proteins as Proteome IDs
# use TDB on disk to speed up processing
.INTERMEDIATE: temp/ncbi-classes.tsv
temp/ncbi-classes.tsv: temp/iedb-proteins.ttl
	$(ROBOT) query --input $< --tdb true --query util/ncbi-classes.rq $@

# the following targets are used to fill in gaps between the organism-tree
# level proteins and the proteins used in the IEDB.

# get a list of NCBITaxon classes already in organism-based tree
.INTERMEDIATE: temp/included-classes.tsv
temp/included-classes.tsv: temp/organism-proteins.ttl
	$(ROBOT) query --input $< --query util/included-classes.rq $@

# create a list of classes MISSING from organism-based tree
.INTERMEDIATE: temp/missing-classes.txt
temp/missing-classes.txt: temp/included-classes.tsv temp/ncbi-classes.tsv
	diff -w $< $(word 2,$^) | awk -F'"' '{print $$2}' | sed '/^$$/d' > $@

# fill in the missing classes from the subspecies tree
.INTERMEDIATE: temp/taxon-proteins.owl
temp/taxon-proteins.owl: $(SUB_TREE) temp/missing-classes.txt \
 temp/organism-proteins.ttl
	$(ROBOT) filter --input $< --term-file $(word 2,$^)\
	 --term rdfs:subClassOf --select "self ancestors annotations" \
	remove --term NCBITaxon:1 --term OBI:0100026 --term NCBITaxon:28384\
	 --term NCBITaxon:32644 --trim true \
	query --update util/rename.ru merge --input $(word 3,$^) --output $@

