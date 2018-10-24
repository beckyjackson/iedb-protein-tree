PREFIX iedb: <http://iedb.org/>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

DELETE { ?s rdfs:label ?oldLabel ;
			obo:NCBITaxon_browser_link ?link }
INSERT { ?s rdfs:label ?newLabel ;
			iedb:browser-link ?link }
WHERE {
	?s a owl:Class ;
	   rdfs:label ?oldLabel .
	OPTIONAL { ?s obo:NCBITaxon_browser_link ?link }
	BIND(CONCAT(STR(?oldLabel), " protein") AS ?newLabel)
}