#!/usr/bin/env python3

import csv

# files to use
parents = "dependencies/parent-proteins.csv"
ttl_out = "build/iedb-proteins.ttl"

# protein database IRI bases
uniprot = "http://www.uniprot.org/uniprot/{0}"
genpept = "https://www.ncbi.nlm.nih.gov/protein/{0}"

# Turtle templates
ttl_header = """@prefix iedb: <http://iedb.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

[ rdf:type owl:Ontology
 ] .

"""

# expects: IRI, parent IRI, accession ID, database name
ttl_template_lite = """
<{0}> rdf:type owl:Class ;
	rdfs:subClassOf <{1}> ;
	iedb:has-accession \"{2}\" ;
	iedb:has-accession-iri <{0}> ;
	iedb:has-source-database \"{3}\" .
"""

# expects: IRI, parent IRI, label, accession ID, database name
ttl_template = """
<{0}> rdf:type owl:Class ;
	rdfs:subClassOf <{1}> ;
	rdfs:label \"{2}\" ;
	iedb:has-accession \"{3}\" ;
	iedb:has-accession-iri <{0}> ;
	iedb:has-source-database \"{4}\" .
"""

# expects: IRI, parent IRI, label, synonym, accession ID, database name
ttl_template_full = """
<{0}> rdf:type owl:Class ;
	rdfs:subClassOf <{1}> ;
	rdfs:label \"{2}\" ;
	iedb:protein-synonym \"{3}\" ;
	iedb:has-accession \"{4}\" ;
	iedb:has-accession-iri <{0}> ;
	iedb:has-source-database \"{5}\" .
"""

lines = []
with open(parents, mode='r') as f:
	reader = csv.DictReader(f, delimiter=',')
	# skip headers
	next(reader)
	# use rows to create ttl
	for row in reader:
		# create an IRI from Accession and Database cells
		database = row["Database"]
		id_num = row["Accession"]
		if database == "GenPept":
			iri = genpept.format(id_num)
		elif database == "UniProt":
			iri = uniprot.format(id_num)
		else:
			print "Unknown database: {0}".format(database)
			continue
		# build a class
		label = row["Title"]
		synonym = row["Name"]
		# assign 'protein' parent for missing parents
		if row["Proteome ID"] == "":
			parent = "http://purl.obolibrary.org/obo/PRO_000000001"
		else:
			parent = "http://purl.obolibrary.org/obo/NCBITaxon_{0}".format(
				row["Proteome ID"])
		if label == "":
			# missing label, check if there is a synonym
			if synonym == "":
				ttl = ttl_template_lite.format(iri, parent, id_num, database)
			else:
				ttl = ttl_template.format(iri, parent, synonym, id_num, database)
		elif synonym == "":
			# only label, no synonym
			ttl = ttl_template.format(iri, parent, label, id_num, database)
		else:
			# all fields present
			ttl = ttl_template_full.format(
				iri, parent, label, synonym, id_num, database)
		lines.append(ttl)

# write to file
with open(ttl_out, 'w') as f:
	f.write(ttl_header)
	for l in lines:
		f.write(l)
