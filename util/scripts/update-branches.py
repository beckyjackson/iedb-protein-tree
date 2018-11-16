#!/usr/bin/env python3

import atexit, csv, gzip, os, rdflib, shutil, sys, subprocess, urllib.request
from rdflib import URIRef, BNode, Literal, RDF, RDFS, XSD, OWL

def main(args):
	'''Usage:
	update-branches.py <active_proteins> <proteomes> <source_parents>'''
	global active_proteins, proteome_id_map, progress, complete, \
	remaining, query_template, proteomes, synonym_map

	active_proteins_file = args[1]
	proteomes_file = args[2]
	source_parents_file = args[3]

	proteome_id_map = {}
	active_proteins = get_active_proteins(active_proteins_file)
	if active_proteins is None:
		print('Could not parse active proteins')
		return
	proteomes = get_proteomes(active_proteins, proteomes_file)
	if proteomes is None:
		print('Could not parse proteomes')
		return
	query_template = get_query_template('util/build-branch.rq')
	synonym_map = get_synonyms(source_parents_file)
	if synonym_map is None:
		print('Could not parse source parents')
		return

	total = len(proteomes.keys())
	complete = 0
	progress = 0
	remaining = total

	print('| % DONE | # TO DO | CURRENT SPECIES ')
	print('|--------|---------|-----------------')

	for k in proteomes.keys():
		print_progress(k)
		process_species(k)
		complete += 1
		remaining -= 1
		progress = (complete / total) * 100

def process_species(species_key):
	'''Process a species from proteomes.tsv. First, fetch the proteome files 
	from UniProt. Then, generate a TTL file representing the species branch. 
	Also generate a set of protein synonyms and merge this into the branch. 
	Finally, filter the branch proteins to only include active proteins in the 
	IEDB.'''
	global active_proteins, proteomes

	if not species_key in proteomes:
		errors.append("MISSING: %s" % species_key)
		return
	group = proteomes[species_key]['Group']
	group_dir = 'build/%s' % (group)
	if not os.path.exists(group_dir):
		os.mkdir(group_dir)
	build_dir = '%s/%s' % (group_dir, species_key)
	if not os.path.exists(build_dir):
		os.mkdir(build_dir)
	result = fetch_proteome(species_key, build_dir)
	if not result:
		errors.append("Could not download proteome for %s" % species_key)
		return

	species_id = species_key.split('-')[0]
	species_proteins = active_proteins[species_id]

	result = generate_branch(species_key, build_dir)
	if not result:
		return
	#result = generate_synonyms(species_key, build_dir)
	#if result:
		#merge_branch_synonyms(species_key, build_dir)
	trim_branch(species_key, build_dir, species_proteins)

def fetch_proteome(species_key, build_dir):
	'''Fetch the proteome files as RDF and FASTA from UniProt for a species.'''
	proteome = proteomes[species_key]
	uniprot_id = proteome['Proteome ID']
	rdf_out_file = '%s/proteome.rdf.gz' % (build_dir)
	if os.path.exists(rdf_out_file):
		return True
	if not os.path.exists(rdf_out_file):
		rdf_url = uniprot % (uniprot_id, 'rdf')
		urllib.request.urlretrieve(rdf_url, rdf_out_file)
	if not os.path.exists(rdf_out_file):
		return None
	return True

def generate_branch(species_key, build_dir):
	'''Unzip the RDF proteome and build a CONSTRUCT query from a template. 
	Query the RDF using ROBOT to build a branch.ttl file. Each protein of the 
	species is a node under a 'species protein' root. Proteins with 'features' 
	will have those features as children.'''
	global query_template

	out_file = '%s/branch.ttl' % build_dir
	# skip if exists
	if os.path.exists(out_file):
		return True

	gz_proteome_file = '%s/proteome.rdf.gz' % build_dir
	if not os.path.exists(gz_proteome_file):
		errors.append('%s proteome file does not exists' % species_key)
		return False
	proteome_file = '%s/proteome.rdf' % build_dir

	# unzip the proteome and remove the import statement
	try:
		if not os.path.exists(proteome_file):
			with gzip.open(gz_proteome_file, 'rb') as f_in:
				with open(proteome_file, 'wb') as f_out:
					shutil.copyfileobj(f_in, f_out)
	except Exception as e:
		errors.append(
			'Unable to unzip proteome for %s\nCAUSE: %s' % (species_key, e))
		return False

	# if the unzipped file is empty, it does not exist
	if os.stat(proteome_file).st_size == 0:
		errors.append('%s proteome file does not exist' % species_key)
		return False

	proteome  = proteomes[species_key]
	species_label = proteome['Species Label']
	species_id = proteome['Species ID']

	# build the query from template
	query_file = '%s/build-branch.rq' % build_dir
	with open(query_file, 'w') as f:
		for line in query_template:
			if '[TAXON_ID]' in line:
				line = line.replace('[TAXON_ID]', species_id)
			elif '[TAXON_LABEL]' in line:
				if '"' in species_label:
					species_label = species_label.replace('"', "\\\"")
				line = line.replace('[TAXON_LABEL]', species_label)
			f.write(line)

	# query with ROBOT
	cmd = query_cmd.format(build_dir)
	try:
		code = subprocess.call(cmd, shell=True)
		if code is not 0:
			# retry and throw error if not 0
			subprocess.check_call(cmd, shell=True)
	except Exception as e:
		errors.append(
			'Unable to construct branch for %s\nCAUSE: %s' % (species_key, e))
		os.remove(proteome_file)
		return False

	lines = []
	with open(out_file, 'r') as f:
		for line in f:
			lines.append(line)

	with open(out_file, 'w') as f:
		for line in lines:
			if 'purl.uniprot' in line:
				line = line.replace('purl.uniprot', 'www.uniprot')
			f.write(line)

	# delete the unzipped proteome file and the query
	os.remove(proteome_file)
	os.remove(query_file)

	if not os.path.exists(out_file):
		errors.append(
			'Unable to construct branch for %s' % (species_key))
		return False
	return True

def generate_synonyms(species_key, build_dir):
	'''Add protein synonyms from the source_parent table to the branch. This 
	constructs a 'synonyms.ttl' file for the branch, which is merged into the 
	branch.ttl file.'''
	global synonym_map

	if species_key not in synonym_map:
		return True

	out_file = '%s/synonyms.ttl' % build_dir
	# skip if exists
	if os.path.exists(out_file):
		return True

	gout = rdflib.Graph()
	gout.bind('owl', owl)
	gout.bind('obo', obo)
	gout.bind('iedb', iedb)

	proteins = synonym_map[species_key]
	for iri,synonyms in proteins.items():
		if 'other' in iri:
			try:
				add_other_protein_node(gout, iri, species_key, synonyms)
			except Exception as e:
				errors.append(
					'Unable to add "other protein" node for %s\nCAUSE: %s' 
					% (species_key, e))
		else:
			for s in synonyms:
				# add declaration
				gout.add((URIRef(iri), 
					URIRef(rdf + 'type'), 
					URIRef(owl + 'Class')))
				# add synonym
				gout.add((URIRef(iri), 
					URIRef(iedb + 'protein-synonym'), 
					Literal(s, datatype=XSD.string)))

	with open(out_file, 'wb') as f:
		gout.serialize(f, format='ttl')

	if not os.path.exists(out_file):
		return False
	return True

def add_other_protein_node(gout, other_id, species_key, synonyms):
	'''For proteins that do not have UniProt parents, add an 'Other X protein' 
	node and assert those as children.'''
	# create the "Other X protein" parent class
	parent_species = proteomes[species_key]['Species Label']
	label = 'Other %s protein' % parent_species
	species_id = iedb + 'taxon-protein/' + proteome['Species ID']
	# add subclass statement
	gout.add((URIRef(other_id), 
		URIRef(rdfs + 'subClassOf'), 
		URIRef(species_id)))
	# add label
	gout.add((URIRef(other_id), 
		URIRef(rdfs + 'label'), 
		Literal(label, datatype=XSD.string)))
	for s in synonyms:
		attrs = s.split('|')
		sid = attrs[0]
		label = attrs[1]
		database = attrs[2]
		accession = attrs[3]
		iri = iedb + 'source/' + sid
		# create accession IRI based on source DB
		if source == 'GenPept':
			accession_iri = 'https://www.ncbi.nlm.nih.gov/protein/' \
				+ accession
		elif source == 'UniProt':
			accession_iri = 'https://www.uniprot.org/uniprot/' + accession
		else:
			errors.append('Unknown source for "%s": %s' % (label, source))
			continue
		# add subclass statement
		gout.add((URIRef(iri), URIRef(rdfs + 'subClassOf'), URIRef(other_id)))
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

def merge_branch_synonyms(species_key, build_dir):
	'''Merge the base branch.ttl file with the synonyms.ttl file.'''
	# synonyms will not exist if the species isn't in the map
	if species_key not in synonym_map:
		return

	cmd = merge_cmd.format(build_dir)
	try:
		code = subprocess.call(cmd, shell=True)
		if code is not 0:
			# retry and throw error if not 0
			subprocess.check_call(cmd, shell=True)
	except Exception as e:
		errors.append(
			'Unable to merge synonyms for %s\nCAUSE: %s' % (species_key, e))
		return

def trim_branch(species_key, build_dir, proteins):
	'''Filter the branch.ttl file to include only active proteins.'''
	active_proteins = '%s/active-proteins.txt' % build_dir
	with open(active_proteins, 'w') as f:
		for p in proteins:
			f.write(p + '\n')
	cmd = filter_cmd.format(build_dir)
	try:
		code = subprocess.call(cmd, shell=True)
		if code is not 0:
			# retry and throw error if not 0
			subprocess.check_call(cmd, shell=True)
	except Exception as e:
		errors.append(
			'Unable to trim branch for %s\nCAUSE: %s' % (species_key, e))
		return
	#os.remove(active_proteins)

def print_progress(species_key):
	'''Print the current status of the process.'''
	global progress, remaining

	if progress < 10:
		print("| %s%%  |   %d   | %s"
			% (" {0:.0f}  ".format(progress), 
				remaining,  
				species_key), end='\r')
	else:
		print("| %s%%  |   %d   | %s"
			% (" {0:.0f} ".format(progress), 
				remaining,  
				species_key), end='\r')
	sys.stdout.write("\033[K")

def get_proteomes(active_proteins, proteomes_file):
	''''''
	global proteome_id_map

	if '.tsv' in proteomes_file:
		delim = '\t'
	elif '.csv' in proteomes_file:
		delim = ','
	else:
		print('Cannot parse file "%s" (unknown format)' % proteomes_file)
		return None

	proteomes = {}
	with open(proteomes_file, 'r') as f:
		reader = csv.DictReader(f, delimiter=delim)
		for row in reader:
			key = row.pop('Species Key', None)
			species_id = row['Species ID']
			if species_id in active_proteins.keys():
				proteomes[key] = row
				proteome_id_map[species_id] = key
	return proteomes

def get_query_template(branch_query_template):
	'''Read in the query template file to return it as a string.'''
	with open(branch_query_template, 'r') as f:
		return f.readlines()

def get_active_proteins(active_proteins_table):
	'''Generate a map of species ID -> list of active proteins based on the 
	active proteins table.'''
	active_proteins = {}
	with open(active_proteins_table, 'r') as f:
		next(f)
		reader = csv.reader(f)
		for row in reader:
			species_id = row[4]
			protein_id = row[0]
			database = row[1]
			if species_id in active_proteins:
				proteins = active_proteins[species_id]
			else:
				proteins = []
			proteins.append('%s:%s' % (database, protein_id))
			active_proteins[species_id] = proteins
	return active_proteins

def get_synonyms(source_parents_file):
	'''Generate a map of species ID -> proteins and synonyms based on the 
	source-parents table.'''
	global proteome_id_map, update_species

	if '.tsv' in source_parents_file:
		delim = '\t'
	elif '.csv' in source_parents_file:
		delim = ','
	else:
		print('Cannot parse file "%s" (unknown format)' % source_parents_file)
		return None

	synonym_map = {}
	with open(source_parents_file, 'r') as f:
		reader = csv.DictReader(f, delimiter=delim)
		for row in reader:
			species = row['Proteome Label'].strip()
			protein = row['Parent IRI'].strip()
			# convert HTTPS to HTTP
			if 'https' in protein:
				protein = protein.replace('https', 'http')
			protein_synonym = row['Name'].strip()

			if 'other' in protein:
				other_id = protein.split('/')[4].split('-')[0]
				if other_id not in proteome_id_map:
					continue
				species = proteome_id_map[other_id]
			
			if species in synonym_map:
				proteins = synonym_map[species]
			else:
				proteins = {}
			if protein in proteins:
				synonyms = proteins[protein]
			else:
				synonyms = []

			if 'other' in protein:
				protein_synonym = '%s|%s|%s|%s' % \
					(row['Source ID'], 
				     protein_synonym, 
					 row['Database'], 
					 row['Accession'])

			synonyms.append(protein_synonym)
			proteins[protein] = synonyms
			synonym_map[species] = proteins

	return synonym_map

# Track all errors
errors = []

# Namespaces
uniprot = 'http://www.uniprot.org/uniprot/?query=proteome:%s\
&compress=yes&force=true&format=%s'
obo = 'http://purl.obolibrary.org/obo/'
iedb = 'http://iedb.org/'
rdfs = 'http://www.w3.org/2000/01/rdf-schema#'
rdf = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
owl = 'http://www.w3.org/2002/07/owl#'

# ROBOT commands
query_cmd = 'java -Xmx8G -jar util/robot.jar query \
 --tdb true --input {0}/proteome.rdf \
 --query {0}/build-branch.rq {0}/branch.ttl'
merge_cmd = 'java -Xmx8G -jar util/robot.jar merge \
 --input {0}/branch.ttl --input {0}/synonyms.ttl --output {0}/branch.ttl'
filter_cmd = 'java -Xmx8G -jar util/robot.jar \
 --prefix \'UniProt: http://www.uniprot.org/uniprot/"\' filter \
 --input {0}/branch.ttl --term-file {0}/active-proteins.txt \
 --select "self ancestors descendants annotations" --output {0}/branch.ttl'

 # Queries
annotation_synonyms_query = """
SELECT *
WHERE {
  ?protein
    uc:annotation ?annotation ;
    uc:component ?component .
  ?annotation
    rdfs:comment ?fullName .
  ?component
    uc:recommendedName / uc:fullName ?fullName .
  OPTIONAL {
    ?component uc:recommendedName / uc:shortName ?synonym .
  }
  OPTIONAL {
    ?component uc:alternativeName / (uc:fullName | uc:shortName) ?synonym .
  }
}"""
annotations_query = """
SELECT *
WHERE {
	VALUES ?type { uc:Chain_Annotation uc:Propeptide_Annotation }
	?annotation
		^uc:annotation ?protein ;
		rdf:type ?type ;
		rdfs:comment ?name ;
		uc:range / faldo:begin / faldo:position ?begin ;
		uc:range / faldo:end / faldo:position ?end .
	?protein
		uc:sequence / rdf:value ?sequence .
}
ORDER BY ?begin ?end"""
proteins_query = """
SELECT *
WHERE {
	?protein
		a uc:Protein ;
		uc:recommendedName / uc:fullName ?name ;
		uc:reviewed ?reviewed ;
		uc:sequence / rdf:value ?sequence .
}"""
protein_synonyms_query = """
SELECT DISTINCT *
WHERE {
	?protein
		a uc:Protein ;
		uc:component /
		 (uc:recommendedName | uc:alternativeName ) /
		 (uc:fullName | uc:shortName) ?name .
}"""

# Setting for large tables
csv.field_size_limit(sys.maxsize)

def on_exit():
	'''Write any errors on exit.'''
	if len(errors) > 0:
		with open('errors.txt', 'w') as f:
			for e in errors:
				f.write(e + '\n')
	print('%d errors' % len(errors))

# execute
if __name__ == '__main__':
	atexit.register(on_exit)
	main(sys.argv)	


