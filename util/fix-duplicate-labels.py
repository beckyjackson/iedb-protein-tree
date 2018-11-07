#!/usr/bin/env python3

import sys

pattern = r'"([A-Za-z0-9_\./\\-]*)"'
pattern_2 = r'>([A-Za-z0-9_\./\\-]*)<'

# iri : { label : '', parent: '', accession: '', source: '', loc: x }
class_map = {}
# iri : parent
child_parent_map = {}
# iri : label
iri_label_map = {}

iris = []
lines = []

def main(args):
	'''Run the fix. Expects: input ontology file, output ontology file.'''
	global class_map, child_parent_map, iri_label_map, iris, lines

	in_file = args[1]
	out_file = args[2]

	parse_input(in_file)
	matches = get_matches()
	updates = get_updates(matches)
	add_updates(out_file, updates)

def parse_input(file):
	'''Parse an input ontology to create the class_map, child_parent_map, 
	iri_label_map, a list of all iris, and a list of all lines.'''
	global class_map, child_parent_map, iri_label_map, iris, lines

	print('parsing input file %s' % file)
	with open(file, 'r') as f:
		line_num = 1
		iri = ''
		parent = ''
		label = ''
		accession = ''
		source = ''
		include = False
		reset = False
		for line in f:
			lines.append(line)
			# skip the source proteins and taxon proteins
			if not include:
				if '<!-- https://www.uniprot.org/uniprot/' in line:
					include = True
				line_num += 1
				continue

			# reset for each new protein class
			if reset:
				iri = ''
				parent = ''
				label = ''
				accession = ''
				source = ''
				loc = 0
				reset = False

			# parse the attributes of the protein class
			if iri == '' and 'owl:Class rdf:about' in line:
				iri = line.split('"')[1]
			elif parent == '' and 'rdfs:subClassOf' in line:
				parent = line.split('"')[1]
			elif accession == '' and 'iedb:has-accession' in line:
				accession = line.split('>')[1].split('<')[0]
			elif source == '' and 'iedb:has-source-database' in line:
				source = line.split('>')[1].split('<')[0]
			elif label == '' and 'rdfs:label' in line:
				label = line.split('>')[1].split('<')[0]
				loc = line_num
			
			if iri != '' and parent != '' and label != '' and accession != '' \
			and source != '':
				# add to the map
				this_map = { 'parent': parent, 
							 'label': label, 
							 'accession': accession, 
							 'source': source, 
							 'loc': loc }
				class_map[iri] = this_map
				child_parent_map[iri] = parent
				iri_label_map[iri] = label
				iris.append(iri)
				reset = True
			if parent != '' and label != '' and accession == '' \
			and source == '':
				# this isn't from a database
				reset = True
			line_num += 1

def get_matches():
	'''Get a map of key (parent plus child label) value (iri) pairs where the 
	IRIs have both the same parent and same label.'''
	global iris, child_parent_map, iri_label_map

	matches = {}
	print('finding matching labels')
	for iri in iris:
		parent = child_parent_map[iri]
		label = iri_label_map[iri]
		key = parent + ' ' + label.lower()
		if key in matches:
			others = matches[key]
			others.append(iri)
		else:
			others = []
			others.append(iri)
			matches[key] = others

	return matches

def get_updates(matches):
	'''Get a map of updates (line number and new label) based on the matching 
	labels.'''
	global class_map

	print('creating new labels')
	updates = {}
	for k,v in matches.items():
		if len(v) > 1:
			# update all labels of each IRI
			for iri in v:
				this_map = class_map[iri]
				loc = this_map['loc']
				label = this_map['label']
				source = this_map['source']
				accession = this_map['accession']
				new_label = '%s (%s %s)' % (label, source, accession)
				updates[loc] = new_label
	return updates

def add_updates(file, updates):
	'''Add the updated lines (line number and new label from updates map) to 
	the output file.'''
	global lines

	print('writing new labels to %s' % file)
	with open(file, 'w') as f:
		line_num = 1
		for line in lines:
			if line_num in updates:
				new_label = updates[line_num]
				line = '\t\t<rdfs:label>%s</rdfs:label>\n' % new_label
			f.write(line)
			line_num += 1

if __name__ == '__main__':
	main(sys.argv)
