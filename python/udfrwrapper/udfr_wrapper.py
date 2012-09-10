'''
Created on 29 Aug 2012

@author: Peter May
@contact: Peter.May@bl.uk
@organization: The British Library

'''

from SPARQLWrapper import SPARQLWrapper, JSON


class UDFRWrapper:

    QPREFIX = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX udfrs: <http://udfr.org/onto#>"""
    
    QUERY = QPREFIX + """
    
            SELECT ?uri ?format ?udfr ?sig
            WHERE { ?uri rdf:type udfrs:InternalSignature;
                    rdfs:label ?format;
                    udfrs:udfrIdentifier ?udfr;
                    udfrs:byteSequence ?sig .
            }
        """
        
    QUERY2 = QPREFIX + """
    
            SELECT ?uri ?format ?sig
            WHERE { ?uri rdf:type                udfrs:InternalSignature;
                         rdfs:label              ?format;
                         udfrs:udfrIdentifier    ?udfr;
                         udfrs:byteSequence      ?bs.
                    ?bs  rdf:type                udfrs:ByteSequence;
                         udfrs:byteSequenceValue ?sig .
            }
        """
        
    QUERY3 = QPREFIX + """
            SELECT ?puid ?format ?siguri ?mime
            WHERE { ?uri     rdf:type                         udfrs:FileFormat;
                             rdfs:label                       ?format;
                             udfrs:signature                  ?siguri;
							 udfrs:mimeType                   ?mimeT;
                             udfrs:aliasIdentifier            ?aid.
                    ?siguri  rdf:type                         udfrs:InternalSignature.
					?mimeT   rdf:type                         udfrs:MIME;
                             rdfs:label                       ?mime.
                    ?aid     udfrs:identifierNamespaceType    udfrs:PUID;
                             udfrs:identifierValue            ?puid.
            }
        """
        
    IntSigQuery = QPREFIX + """
            SELECT ?name ?bsv ?pos ?off ?maxoff
            WHERE {  <%s>    rdfs:label                ?name;
                             udfrs:byteSequence        ?bs.
                     ?bs     rdf:type                  udfrs:ByteSequence;
                             udfrs:byteSequenceValue   ?bsv;
                             udfrs:positionType        ?pos.
                    OPTIONAL { ?bs udfrs:signatureOffset     ?off } .
                    OPTIONAL { ?bs udfrs:signatureOffsetUpperBound ?maxoff }.                             
            }
        """

                     
    def __init__(self):
        self.sparql = SPARQLWrapper("http://udfr.org/ontowiki/sparql/")
        self.sparql.setReturnFormat(JSON)
        
    def getAllFileFormats(self):
        """Returns the PUID, format label, mime-type and UDFR Internal Signature URIs for all file formats"""
        self.sparql.setQuery(self.QUERY3)
        results = self.sparql.query().convert()
        return results
    
    def getSignaturesForFileFormat(self, siguri):
        """Returns the name, byte sequence, position, offset and maximum offset for the specified
           signature URI
        """
        q = self.IntSigQuery%(siguri,)
        self.sparql.setQuery(q)
        results = self.sparql.query().convert()
        return results
    
    def getAllByteSequence(self):
        """Returns the UDFR URI, format and byte sequence for all file formats"""
        self.sparql.setQuery(self.QUERY2)
        results = self.sparql.query().convert()
        return results

def main():
    udfrwrapper = UDFRWrapper()
    results = udfrwrapper.getAllByteSequence()
    
    print results.keys()
    print results["head"]
    print results["results"].keys()
    print results["results"]["bindings"][0]
    
    #for result in results["results"]["bindings"]:
    #    print result
    print len(results["results"]["bindings"])
    
    test = udfrwrapper.getSignaturesForFileFormat('http://udfr.org/udfr/u1r4197')['results']['bindings']
    print 'test: ',test


if __name__ == '__main__':
    main()