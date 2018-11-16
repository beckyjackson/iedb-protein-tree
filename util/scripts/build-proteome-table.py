#!/usr/bin/env python3

import sys
import csv

def main(args):
	parent_proteins_file = args[1]
	active_species_file = args[2]
	proteomes_file = args[3]

	proteome_ids = {}
	with open(parent_proteins_file, 'r') as f:
		next(f)
		reader = csv.reader(f, delimiter='\t')
		# Accession, Database, Name, Title, Proteome ID, Proteome Label, Sequence
		for row in reader:
			key = row[5]
			if key.endswith(' Reference Proteome'):
				key = key[:-19]
			value = row[4]
			# There should only be one ID per species
			if key in proteome_ids:
				existing_value = proteome_ids[key]
				if value != existing_value:
					print('Different IDs for %s: %s, %s' % (key, existing_value, value))
			else:
				proteome_ids[key] = value

	active_species = {}
	with open(active_species_file, 'r') as f:
		next(f)
		reader = csv.reader(f, delimiter='\t')
		# Species Key, Species ID, Species Label, Active Taxa, Group
		for row in reader:
			key = row.pop(0)
			active_species[key] = row

	for key in proteome_ids.keys():
		if not key in active_species:
			print("MISSING: %s" % key)

	with open(proteomes_file, 'w') as f:
		f.write('Species Key\tSpecies ID\tSpecies Label\tActive Taxa\tGroup\tProteome ID\n')
		for key in active_species.keys():
			if not key in proteome_ids:
				continue
			row = []
			row.append(key)
			row.extend(active_species[key])
			row.append(proteome_ids[key])
			f.write('\t'.join(row)+'\n')

if __name__ == '__main__':
	main(sys.argv)