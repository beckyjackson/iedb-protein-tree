#!/usr/bin/env python3

import csv, os, sys

build_dirs = ['build/archeobacterium', 
			  'build/bacterium', 
			  'build/other-eukaryote', 
			  'build/plant', 
			  'build/vertebrate',
			  'build/virus']

def main(args):
	'''Usage:
	get-active-species.py <active-proteins> <proteins-current> <proteins-last> 
	Compares the current protein table to the last protein table to build a 
	table containing only the updated proteins (active proteins).'''
	protein_table_current = args[2]
	protein_table_last = args[3]
	active_proteins_table = args[1]

	# { species_id : { protein_id : line } }
	current_proteins = read_proteins(protein_table_current)
	last_proteins = read_proteins(protein_table_last)

	existing_species = get_existing_species()

	active_proteins = get_active_proteins(
		current_proteins, last_proteins, existing_species)

	write_active_proteins(active_proteins, active_proteins_table)

def read_proteins(table_file):
	'''Read in a parent-proteins CSV file to generate a map of the species IDs 
	to all their proteins.'''
	proteins = {}
	# if the file is empty, just return the empty map
	if os.path.getsize(table_file) is 0:
		return proteins
	with open(table_file, 'r') as f:
		next(f)
		reader = csv.reader(f)
		for row in reader:
			species_id = row[4]
			protein_id = row[0]
			if protein_id == '':
				continue
			if species_id in proteins:
				species_proteins = proteins[species_id]
			else:
				species_proteins = {}
			if protein_id in species_proteins:
				# ERROR!
				print('Duplicate protein %s for %s' % (protein_id, row[5]))
				continue
			species_proteins[protein_id] = row
			proteins[species_id] = species_proteins
	return proteins

def get_existing_species():
	'''Get a list of the species that have a fully-generated branch. If the 
	branch file does not exist, the species is not included. If the build-
	branch query still exists, the species is not included as the branch was 
	not built successfully.'''
	species = []
	for d in build_dirs:
		if os.path.exists(d) and os.path.isdir(d):
			for subdir in os.listdir(d):
				if os.path.isdir('%s/%s' % (d, subdir)):
					files = os.listdir('%s/%s' % (d, subdir))
					if 'branch.ttl' not in files:
						continue
					if 'build-branch.rq' in files:
						continue
					sid = subdir.split('-')[0]
					species.append(sid)
	return species

def get_active_proteins(current_proteins, last_proteins, existing_species):
	'''Compare the current proteins to the last proteins to get a map of active
	proteins. Also check if the species is NOT in the built branches.'''
	active_proteins = {}
	for species, species_proteins in current_proteins.items():
		if species not in last_proteins:
			active_proteins[species] = species_proteins
			continue
		if species not in existing_species:
			active_proteins[species] = species_proteins
			continue
		last_species_proteins = last_proteins[species]
		update = False
		for protein, row in species_proteins.items():
			if protein not in last_species_proteins:
				update = True
				break
			last_row = last_species_proteins[protein]
			diff = list(set(row) - set(last_row))
			if len(diff) > 0:
				update = True
				break
		if update:
			active_proteins[species] = species_proteins
	return active_proteins

def write_active_proteins(active_proteins, active_proteins_table):
	'''Write the active proteins to a new table.'''
	with open(active_proteins_table, 'w') as f:
		f.write(
			'Accession,Database,Name,Title,'
			'Proteome ID,Proteome Label,Sequence\n')
		writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
		for species, species_proteins in active_proteins.items():
			for protein, row in species_proteins.items():
				writer.writerow(row)

if __name__ == '__main__':
	main(sys.argv)
