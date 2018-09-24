PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

DELETE { ?s rdfs:label ?oldLabel }
INSERT { ?s rdfs:label ?newLabel }
WHERE {
	?s a owl:Class ;
	   rdfs:label ?oldLabel .
	BIND(CONCAT(STR(?oldLabel), " protein") AS ?newLabel)
}