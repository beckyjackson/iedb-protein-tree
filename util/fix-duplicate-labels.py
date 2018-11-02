#!/usr/bin/env python3

file = 'protein-tree.owl'
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

print('parsing input file')
with open(file, 'r') as f:
	line_num = 1
	iri = ''
	parent = ''
	label = ''
	accession = ''
	source = ''
	reset = False
	for line in f:
		lines.append(line)
		if reset:
			iri = ''
			parent = ''
			label = ''
			accession = ''
			source = ''
			loc = 0
			reset = False
		if iri == '' and 'owl:Class rdf:about' in line:
			iri = line.split('"')[1]
		if parent == '' and 'rdfs:subClassOf' in line:
			parent = line.split('"')[1]
		if label == '' and 'rdfs:label' in line:
			label = line.split('>')[1].split('<')[0]
			loc = line_num
		if accession == '' and 'iedb:has-accession' in line:
			accession = line.split('>')[1].split('<')[0]
		if source == '' and 'iedb:has-source-database' in line:
			source = line.split('>')[1].split('<')[0]
		if iri != '' and parent != '' and label != '' and accession != '' and source != '':
			# add to the map
			this_map = { 'parent': parent, 'label': label, 'accession': accession, 'source': source, 'loc': loc }
			class_map[iri] = this_map
			child_parent_map[iri] = parent
			iri_label_map[iri] = label
			iris.append(iri)
			reset = True
		if parent != '' and label != '' and accession == '' and source == '':
			# this isn't from a database
			reset = True
		line_num += 1

matches = {}

print('finding matching labels')
for iri in iris:
	parent = child_parent_map[iri]
	label = iri_label_map[iri]
	key = parent + ' ' + label
	if key in matches:
		others = matches[key]
		others.append(iri)
	else:
		others = []
		others.append(iri)
		matches[key] = others

iris.clear()
child_parent_map.clear()
iri_label_map.clear()

updates = {}

print('creating new labels')
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

matches.clear()
class_map.clear()

print('writing new labels')
with open(file, 'w') as f:
	line_num = 1
	for line in lines:
		if line_num in updates:
			new_label = updates[line_num]
			line = '\t\t<rdfs:label>%s</rdfs:label>' % new_label
		f.write(line)
		line_num += 1
