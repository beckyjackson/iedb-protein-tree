PREFIX iedb: <http://iedb.org/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

DELETE { ?s iedb:has-species-iri ?oldIRI }
INSERT { ?s iedb:has-species-iri ?newIRI }
WHERE { ?s a owl:Class ;
					 iedb:has-species-iri ?oldIRI .
				BIND(CONCAT("http://purl.obolibrary.org/obo/NCBITaxon_", SUBSTR(STR(?oldIRI), 31)) AS ?newIRI)
}