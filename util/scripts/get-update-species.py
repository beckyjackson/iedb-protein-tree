#!/usr/bin/env python3

import csv, sys

def main(args):
	update_species_file = args[1]
	active_proteins_table = args[2]

	update_species = []
	with open(active_proteins_table, 'r') as f:
		next(f)
		reader = csv.reader(f)
		for row in reader:
			species_id = row[4]
			if species_id not in update_species:
				update_species.append(species_id)

	with open(update_species_file, 'w') as f:
		f.write(' '.join(update_species))

if __name__ == '__main__':
	main(sys.argv)