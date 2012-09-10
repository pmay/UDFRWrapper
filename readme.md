# UDFR Wrapper
I wanted to get an understanding of UDFR and SPARQL queries, so this code helps enable SPARQL queries on the UDFR registry. It is used by fido_prepare.

## Dependencies
The UDFR registry requires sparql-wrapper (http://sparql-wrapper.sourceforge.net/) and simplejson (http://pypi.python.org/pypi/simplejson).

Install via: python easy_install sparql-wrapper
This should install all the necessary dependencies.

# Generate Fido Signature File
This code generates a Fido signature file from the data in the UDFR registry. It is proof-of-concept code and has not been tested for completeness or correctness (i.e. it may not have all signatures or deliver all features Fido supports). It is based on the fido prepare.py code maintained by Maurice de Rooij.

## Generating a signature file
To generate a conf\udfr_formats.xml file run (the http proxy is optional):

    python fido_prepare.py http://username:password@proxyurl:port

The conf dir will be created in the same directory as the fido_prepare.py file.

## Using the signature file
The conf directory produced by fido_prepare.py should be copied (and replace) Fido's conf directory.

Some minor changes have to be made to Fido. Comment out the following lines:

1. line 57: self.load_container_signature(os.path.join(os.path.abspath(self.conf_dir), self.containersignature_file))
2. line 736: defaults['format_files'].append(defaults['xml_pronomSignature'])
3. line 737: defaults['format_files'].append(defaults['xml_fidoExtensionSignature'])

Then run Fido with the -loadformat argument:

    python fido -loadformat conf\udfr_formats.xml <file_to_identify>