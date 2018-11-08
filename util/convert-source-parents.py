#!/usr/bin/env python3

import csv
import sys

columns = [
  'Source ID',
  'Accession',
  'Database',
  'Name',
  'Aliases',
  'Synonyms',
  'Taxon ID',
  'Taxon Name',
  'Species ID',
  'Species Label',
  'Proteome ID',
  'Proteome Label',
  'Protein Strategy',
  'Parent IRI',
  'Parent Protein Database',
  'Parent Protein Accession',
  'Parent Sequence Length',
  'Sequence'
]

ids = set()
dupes = set()

def main(args):
  with open(args[2], mode='w') as out:
    w = csv.writer(out, lineterminator='\n')
    w.writerow(columns)
    with open(args[1], mode='r') as r:
      rows = csv.DictReader(r, delimiter='\t')
      for row in rows:
        if not 'Source ID' in row:
          continue
        elif not row['Source ID']:
          continue
        row['Source ID'] = int(float(row['Source ID']))

        if 'Taxon ID' in row and row['Taxon ID']:
          row['Taxon ID'] = int(float(row['Taxon ID']))

        if row['Source ID'] in ids:
          dupes.add(row['Source ID'])
          print('Duplicate ID', row['Source ID'])
          continue
        else:
          ids.add(row['Source ID'])

        if 'Parent IRI' in row and row['Parent IRI']:
          row['Parent IRI'] = row['Parent IRI'].replace('https:', 'http:')

        result = []
        for column in columns:
          if column == 'Proteome ID':
            column = 'Species ID'
          value = ''
          if column in row:
            value = row[column]
          result.append(value)
        w.writerow(result)
  if len(dupes) > 0:
    print('Found duplicates:', len(dupes))


if __name__ == '__main__':
	main(sys.argv)
