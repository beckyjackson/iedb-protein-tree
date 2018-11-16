#!/usr/bin/env python3

import csv
import sys

columns = [
  'Accession',
  'Database',
  'Name',
  'Title',
  'Proteome ID',
  'Proteome Label',
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
        if not 'Accession' in row:
          continue
        elif not row['Accession']:
          continue

        if 'Proteome ID' in row and row['Proteome ID']:
          row['Proteome ID'] = int(float(row['Proteome ID']))

        if row['Accession'] in ids:
          dupes.add(row['Accession'])
          print('Duplicate ID', row['Accession'])
          continue
        else:
          ids.add(row['Accession'])

        row['Name'] = row['Name'].split('|')[-1]
        row['Title'] = format_title(row['Title'])

        result = []
        for column in columns:
          value = ''
          if column in row:
            value = row[column]
          result.append(value)
        w.writerow(result)
  if len(dupes) > 0:
    print('Found duplicates:', len(dupes))

def format_title(title):
  if title == "":
    return ""
  words = title.split(" ")
  label_words = []
  for w in words:
    if '|' in w:
      continue
    if '=' in w:
      break
    label_words.append(w)
  return " ".join(label_words)

if __name__ == '__main__':
	main(sys.argv)
