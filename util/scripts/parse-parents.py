#!/usr/bin/env python3

import csv
import sys

# protein database IRI bases
uniprot = 'http://www.uniprot.org/uniprot/{0}'
genpept = 'http://www.ncbi.nlm.nih.gov/protein/{0}'

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

def main(args):
	in_file = args[1]
	out_file = args[2]
	lines = []
	with open(in_file, mode='r') as f:
		reader = csv.DictReader(f)
		# use rows to create ttl
		for row in reader:
			lines.append(parse_row(row))
	# write to file
	with open(out_file, 'w') as f:
		f.write(ttl_header)
		for l in lines:
			f.write(l)

def parse_row(row):
	# create an IRI from Accession and Database cells
	database = row['Database']
	id_num = row['Accession']
	proteome_label = row['Proteome Label']
	iri = format_iri(database, id_num, proteome_label)
	if iri is None:
		return ''
	# build a class
	label = row['Title']
	synonym = row['Name']
	parent = format_parent(row['Proteome ID'])
	if label == '':
		# missing label, check if there is a synonym
		if synonym == '':
			return ttl_template_lite.format(iri, parent, id_num, database)
		else:
			return ttl_template.format(iri, parent, synonym, id_num, database)
	elif synonym == '':
		# only label, no synonym
		return ttl_template.format(iri, parent, label, id_num, database)
	else:
		# all fields present
		return ttl_template_full.format(
			iri, parent, label, synonym, id_num, database)

def format_iri(database, id_num, proteome):
	if database == '':
		print('No proteins for {0}'.format(proteome))
		return None
	if database == 'GenPept':
		return genpept.format(id_num)
	elif database == 'UniProt':
		return uniprot.format(id_num)
	else:
		print('Unknown database: {0}'.format(database))
		return None

def format_parent(proteome_id):
	if proteome_id == '':
		return 'http://purl.obolibrary.org/obo/PRO_000000001'
	return 'http://purl.obolibrary.org/obo/NCBITaxon_{0}'.format(proteome_id)

if __name__ == '__main__':
	main(sys.argv)
