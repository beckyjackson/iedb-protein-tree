#!/usr/bin/env python3

import csv

parents = "build/parent-proteins.csv"
ttl = "build/iedb-proteins.ttl"

lines = []
with open(parents, mode='r') as f:
	reader = csv.DictReader(f, delimiter=',')
	# skip headers
	next(reader)
	# use rows to create ttl
	for row in reader:
		# create an IRI from Accession and Database cells
		iri = "http://iedb.org/taxon-protein/{0}_{1}".format(row["Database"], row["Accession"])
		# label may be empty
		label = row["Name"]
		# assign 'protein' parent for missing parents
		if row["Proteome ID"] is "":
			parent = "http://purl.obolibrary.org/obo/PRO_000000001"
		else:
			parent = "http://purl.obolibrary.org/obo/NCBITaxon_{0}".format(row["Proteome ID"])
		
		if label is "":
			stanza = "\n<{0}> rdf:type owl:Class ;\n\trdfs:subClassOf <{1}> .\n".format(iri, parent)
		else:
			stanza = "\n<{0}> rdf:type owl:Class ;\n\trdfs:subClassOf <{1}> ;\n\trdfs:label \"{2}\" .\n".format(iri, parent, label)
		lines.append(stanza)

with open(ttl, 'w') as f:
	f.write("""@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n
[ rdf:type owl:Ontology
 ] .\n
""")
	for l in lines:
		f.write(l)
