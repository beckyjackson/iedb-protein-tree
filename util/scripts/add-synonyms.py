#!/usr/bin/env python3

import csv, rdflib, sys
from rdflib import URIRef, BNode, Literal, RDF, RDFS, XSD, OWL

rdfs = 'http://www.w3.org/2000/01/rdf-schema#'
rdf = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
owl = 'http://www.w3.org/2002/07/owl#'
iedb = 'http://iedb.org/'

# global maps
parent_synonyms = {}
other_proteins = {}
other_protein_labels = {}

def main(args):
	'''Parse the source file into the two maps, then use the maps to create 
	protein synonym triples in an RDF graph. New classes will be created for 
	"other X protein" parents & children. Write the triples to the out file.'''
	global parent_synonyms, other_proteins, other_protein_labels

	source_file = args[1]
	active_proteins_file = args[2]
	out_file = args[3]

	active_proteins = get_active_proteins(active_proteins_file)
	parse_sources(source_file, active_proteins)

	gout = rdflib.Graph()
	gout.bind('owl', owl)
	gout.bind('obo', 'http://purl.obolibrary.org/obo/')
	gout.bind('iedb', iedb)

	add_protein_synonyms(gout)
	add_other_proteins(gout)

	with open(out_file, 'wb') as f:
		gout.serialize(f, format='ttl')

def add_other_proteins(gout):
	'''Add "other X protein" classes to the graph as subclass of "X protein". 
	For each child of that protein, create a child class instead of adding as a 
	synonym.'''
	global other_proteins, other_protein_labels

	for parent,children in other_proteins.items():
		# create the "Other X protein" parent class
		label = 'Other %s protein' % other_protein_labels[parent]
		# add subclass statement
		gout.add((URIRef(parent), 
			URIRef(rdfs + 'subClassOf'), 
			URIRef(parent[:-6])))
		# add label
		gout.add((URIRef(parent), 
			URIRef(rdfs + 'label'), 
			Literal(label, datatype=XSD.string)))
		# add the children
		for c in children:
			iri = c['iri']
			sid = c['source_id']
			source = c['source']
			accession = c['accession']
			label = '%s [%s]' % (c['label'], accession)
			# create accession IRI based on source DB
			if source == 'GenPept':
				accession_iri = 'http://www.ncbi.nlm.nih.gov/protein/' \
					+ accession
			elif source == 'UniProt':
				accession_iri = 'http://www.uniprot.org/uniprot/' + accession
			else:
				print('Unknown source for "%s": %s' % (label, source))
				continue
			# add subclass statement
			gout.add((URIRef(iri), URIRef(rdfs + 'subClassOf'), URIRef(parent)))
			# add label
			gout.add((URIRef(iri), 
				URIRef(rdfs + 'label'), 
				Literal(label, datatype=XSD.string)))
			# add accession
			gout.add((URIRef(iri), 
				URIRef(iedb + 'has-accession'), 
				Literal(accession, datatype=XSD.string)))
			# add accession IRI
			gout.add((URIRef(iri), 
				URIRef(iedb + 'has-accession-iri'), 
				URIRef(accession_iri)))
			# add source DB
			gout.add((URIRef(iri), 
				URIRef(iedb + 'has-source-database'), 
				Literal(source, datatype=XSD.string)))
			# add source ID
			gout.add((URIRef(iri), 
				URIRef(iedb + 'has-source-id'), 
				Literal(sid, datatype=XSD.string)))

def add_protein_synonyms(gout):
	'''Add child protein labels as synonyms to the parent proteins. Include a 
	declaration so it is properly loaded by OWLAPI.'''
	global parent_synonyms

	for iri,syns in parent_synonyms.items():
		for s in syns:
			# add declaration
			gout.add((URIRef(iri), URIRef(rdf + 'type'), URIRef(owl + 'Class')))
			# add synonym
			gout.add((URIRef(iri), 
				URIRef(iedb + 'protein-synonym'), 
				Literal(s, datatype=XSD.string)))

def parse_source_row(row):
	'''Parse a row from the source table. Use the IRI to find the parent to add 
	a synonym to. If the IRI references an "other" protein, add the IRI and 
	synonyms as children to the other_proteins map. Otherwise, add the IRI and 
	synonyms to the parent_synonyms map.'''
	global parent_synonyms, other_proteins, other_protein_labels

	# possibly - add code to ignore uniprot parents that aren't in tree

	iri = row['Parent IRI']
	# replace HTTPS with HTTP
	if 'https' in iri:
		iri = iri.replace('https', 'http')
	if 'other' in iri:
		# accession should be in brackets after label
		other_protein_labels[iri] = row['Species Label']
		if iri in other_proteins:
			children = other_proteins[iri]
		else:
			children = []
		label = row['Name']
		source = row['Database']
		accession = row['Accession']
		protein_iri = 'http://iedb.org/source/' + row['Source ID']
		child = {'iri': protein_iri, 
				 'source_id': row['Source ID'], 
				 'label': label, 
				 'source': source, 
				 'accession': accession}
		children.append(child)
		other_proteins[iri] = children

	else:
		if iri in parent_synonyms:
			synonyms = parent_synonyms[iri]
		else:
			synonyms = []
		synonyms.append(row['Name'])
		parent_synonyms[row['Parent IRI']] = synonyms

def get_active_proteins(active_proteins_file):
	''''''
	proteins = []
	with open(active_proteins_file, 'r') as f:
		rows = csv.DictReader(f)
		for row in rows:
			proteins.append(row['Accession'])
	return proteins

def parse_sources(source_file, active_proteins):
	'''Parse a source table into parent_synonym and other_proteins maps.'''
	global parent_synonyms, other_proteins

	with open(source_file, 'r') as f:
		rows = csv.DictReader(f)
		for row in rows:
			if (row['Parent Protein Accession'] == '')\
			 or (row['Parent Protein Accession'] in active_proteins):
				parse_source_row(row)

if __name__ == '__main__':
	main(sys.argv)
