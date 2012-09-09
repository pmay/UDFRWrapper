#!python
# -*- coding: utf-8 -*-
# Format Identification for Digital Objects

# MdR: 'reload(sys)' and 'setdefaultencoding("utf-8")' needed to fix utf-8 encoding errors
# when converting from PRONOM to FIDO format
import sys
reload(sys)
#sys.setdefaultencoding("utf-8")
import cStringIO, os
from xml.etree import ElementTree as ET

# needed for debug
# print_r: https://github.com/marcbelmont/python-print_r
# from print_r import print_r
import udfr_wrapper
import re

def _callback(matches):
    id = matches.group(1)
    try:
        return unichr(int(id))
    except:
        return id

def decode_unicode_references(data):
    return re.sub("&#(\d+)(;|(?=\s))", _callback, data)

class FormatInfo:
    def __init__(self, format_list=[]):
        self.info = {}
        self.formats = []
        self.udfrwrapper = udfr_wrapper.UDFRWrapper()
        self.udfrdict = self.udfrwrapper.getAllFileFormats()
                             
    def save(self, dst):
        """Write the fido XML format definitions to @param dst
        """
        tree = ET.ElementTree(ET.Element('formats', {'version':'0.3',
                                                     'xmlns:xsi' : "http://www.w3.org/2001/XMLSchema-instance",
                                                     'xsi:noNamespaceSchemaLocation': "fido-formats-0.3.xsd",
                                                     'xmlns:dc': "http://purl.org/dc/elements/1.1/",
                                                     'xmlns:dcterms': "http://purl.org/dc/terms/"}))
        root = tree.getroot()
        for f in self.formats:
            # MdR: this skipped puids without sig, but we want them ALL
            # because puid might be matched on extension
            #if f.find('signature'):
            root.append(f)
        self.indent(root)
        with open(dst, 'wb') as out:
                #print >>out, ET.tostring(root,encoding='utf-8')     
                print >>out, ET.tostring(root)     

    def indent(self, elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
                
    def load_udfr_data(self):
        formats = []
        print "Number formats: ",len(self.udfrdict['results']['bindings'])
        for fdict in self.udfrdict['results']['bindings']:
            format = self.parse_udfr_xml(fdict)
            if format != None:
                formats.append(format)
                
        self._sort_formats(formats)
        self.formats = formats

    
    def parse_udfr_xml(self, eldict):
        fido_format = ET.Element('format')
        
        # eldict should contain PUID
        puid = eldict['puid']['value']
        ET.SubElement(fido_format, 'puid').text = puid
        
        # name
        name = eldict['format']['value']
        ET.SubElement(fido_format, 'name').text = name
        
        # signature
        fido_sig = ET.SubElement(fido_format, 'signature')
        
        # get all signatures
        sigdict = self.udfrwrapper.getSignaturesForFileFormat(eldict['siguri']['value'])['results']['bindings']
        
        ET.SubElement(fido_sig, 'name').text = sigdict[0]['name']['value']
        
        for pattern in sigdict:
            fido_pat   = ET.SubElement(fido_sig, 'pattern')
            sigbytes   = decode_unicode_references(pattern['bsv']['value'])
            pos        = pattern['pos']['value']
            
            offset     = ''
            if 'offset' in pattern:
                offset     = pattern['off']['value']
                
            max_offset = ''
            if 'maxoff' in pattern:
                max_offset = pattern['maxoff']['value']


            regex = convert_to_regex(sigbytes, 'Little', pos, offset, max_offset)
            ET.SubElement(fido_pat, 'position').text = fido_position(pos)
            ET.SubElement(fido_pat, 'regex').text = regex
        
        # details
        fido_details = ET.SubElement(fido_format,'details')
        return fido_format
           
    #FIXME: I don't think that this quite works yet!
    def _sort_formats(self, formatlist):
        """Sort the format list based on their priority relationships so higher priority
           formats appear earlier in the list.
        """
        def compare_formats(f1, f2):
            f1ID = f1.find('puid').text
            f2ID = f2.find('puid').text
            for worse in f1.findall('has_priority_over'):
                if worse.text == f2ID:
                    return - 1
            for worse in f2.findall('has_priority_over'):
                if worse.text == f1ID:
                    return 1
            if f1ID < f2ID:
                return - 1
            elif f1ID == f2ID:
                return 0
            else:
                return 1
        return sorted(formatlist, cmp=compare_formats)

def fido_position(udfr_position):
    """translate the UDFR position URIs to BOF/EOF/VAR
    """
    if udfr_position == 'http://udfr.org/onto#BOF':
        return 'BOF'
    elif udfr_position == 'http://udfr.org/onto#EOF':
        return 'EOF'
    elif udfr_position == 'http://udfr.org/onto#VariablePosition':
        return 'VAR'
    else:
        sys.stderr.write("Unknown UDFR PositionType:" + udfr_position)    
        return 'VAR'

def _convert_err_msg(msg, c, i, chars):
    return "Conversion: {0}: char='{1}', at pos {2} in \n  {3}\n  {4}^\nBuffer = {5}".format(msg, c, i, chars, i * ' ', buf.getvalue())

def doByte(chars, i, littleendian):
    """Convert two chars[i] and chars[i+1] into a byte.  
       @return a tuple (byte, 2) 
    """
    c1 = '0123456789ABCDEF'.find(chars[i].upper())
    c2 = '0123456789ABCDEF'.find(chars[i + 1].upper())
    if (c1 < 0 or c2 < 0):
        raise Exception(_convert_err_msg('bad byte sequence', chars[i:i + 2], i, chars))
    if littleendian:
        val = chr(16 * c1 + c2)
    else:
        val = chr(c1 + 16 * c2)
    return (escape(val), 2)

# \a\b\n\r\t\v
# MdR: took out '<' and '>' out of _ordinary because they were converted to entities &lt;&gt;
# MdR: moved '!' from _ordinary to _special because it means "NOT" in the regex world. At this time no regex in any sig has a negate set, did this to be on the safe side
_ordinary = frozenset(' "#%&\',-/0123456789:;=@ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz~')
_special = '$()*+.?![]^\\{|}'
_hex = '0123456789abcdef'
def _escape_char(c):
    if c in '\n':
        return '\\n'
    elif c == '\r':
        return '\\r'
    elif c in _special:
        return '\\' + c
    else:
        (high, low) = divmod(ord(c), 16)
        return '\\x' + _hex[high] + _hex[low]

def escape(string):
    "Escape characters in pattern that are non-printable, non-ascii, or special for regexes."
    return ''.join(c if c in _ordinary else _escape_char(c) for c in string)

def calculate_repetition(char, pos, offset, maxoffset):
    """
    Recursively calculates offset/maxoffset repetition,
    when one or both offsets is greater than 65535 bytes (64KB)
    see: bugs.python.org/issue13169
    Otherwise it returns the {offset,maxoffset}
    """
    calcbuf = cStringIO.StringIO()
    
    calcremain = False
    offsetremain = 0
    maxoffsetremain = 0
    
    if offset != None and offset != '':
        if int(offset) > 65535:
            offsetremain = str(int(offset) - 65535)
            offset = '65535'
            calcremain = True
    if maxoffset != None and maxoffset != '':
        if int(maxoffset) > 65535:
            maxoffsetremain = str(int(maxoffset) - 65535)
            maxoffset = '65535'
            calcremain = True
    
    if pos == "BOF" or pos == "EOF":
        if offset != '0':
            calcbuf.write(char + '{' + str(offset))
            if maxoffset != None:
                calcbuf.write(',' + maxoffset)
            calcbuf.write('}')
        elif maxoffset != None:
            calcbuf.write(char + '{0,' + maxoffset + '}')

    if pos == "IFB":
        if offset != '0':
            calcbuf.write(char + '{' + str(offset))
            if maxoffset != None:
                calcbuf.write(',' + maxoffset)
            calcbuf.write('}')
            if maxoffset == None:
                calcbuf.write(',}')
        elif maxoffset != None:
            calcbuf.write(char + '{0,' + maxoffset + '}')

    if calcremain: # recursion happens here
        calcbuf.write(calculate_repetition(char, pos, offsetremain, maxoffsetremain))
    
    val = calcbuf.getvalue()
    calcbuf.close()
    return val

def convert_to_regex(chars, endianness='', pos='BOF', offset='0', maxoffset=''):
    """Convert 
       @param chars, a pronom bytesequence, into a 
       @return regular expression.
       Endianness is not used.
    """

    if 'Big' in endianness:
        littleendian = False
    else:
        littleendian = True
    if len(offset) == 0:
        offset = '0'
    if len(maxoffset) == 0:
        maxoffset = None
    # make buf global so we can print it @'_convert_err_msg' while debugging (MdR)
    global buf
    buf = cStringIO.StringIO()
    buf.write("(?s)")   #If a regex starts with (?s), it is equivalent to DOTALL.   
    i = 0
    state = 'start'
    if 'BOF' in pos:
        buf.write('\\A') # start of regex
        buf.write(calculate_repetition('.', pos, offset, maxoffset))
            
    if 'IFB' in pos:
        buf.write('\\A')
        buf.write(calculate_repetition('.', pos, offset, maxoffset))
            
    while True:
        if i == len(chars):
            break
        #print _convert_err_msg(state,chars[i],i,chars)
        if state == 'start':
            if chars[i].isalnum():
                state = 'bytes'
            elif chars[i] == '[' and chars[i + 1] == '!':
                state = 'non-match'
            elif chars[i] == '[':
                state = 'bracket'
            elif chars[i] == '{':
                state = 'curly'
            elif chars[i] == '(':
                state = 'paren'
            elif chars[i] in '*+?':
                state = 'specials'
            else:
                raise Exception(_convert_err_msg('Illegal character in start', chars[i], i, chars))
        elif state == 'bytes':
            (byt, inc) = doByte(chars, i, littleendian)
            buf.write(byt)
            i += inc
            state = 'start'
        elif state == 'non-match':
            buf.write('(!')
            i += 2
            while True:
                if chars[i].isalnum():
                    (byt, inc) = doByte(chars, i, littleendian)
                    buf.write(byt)
                    i += inc
                elif chars[i] == ']':
                    break
                else:
                    raise Exception(_convert_err_msg('Illegal character in non-match', chars[i], i, chars))
            buf.write(')')
            i += 1
            state = 'start'

        elif state == 'bracket':
            try:
                buf.write('[')
                i += 1
                (byt, inc) = doByte(chars, i, littleendian)
                buf.write(byt)
                i += inc
                #assert(chars[i] == ':')
                if chars[i] != ':':
                    return "__INCOMPATIBLE_SIG__"
                buf.write('-')
                i += 1
                (byt, inc) = doByte(chars, i, littleendian)
                buf.write(byt)
                i += inc
                #assert(chars[i] == ']')
                if chars[i] != ']':
                    return "__INCOMPATIBLE_SIG__"
                buf.write(']')
                i += 1
            except Exception:
                print _convert_err_msg('Illegal character in bracket', chars[i], i, chars)
                raise
            if i < len(chars) and chars[i] == '{':
                state = 'curly-after-bracket'
            else:
                state = 'start'
        elif state == 'paren':
            buf.write('(?:')
            i += 1
            while True:
                if chars[i].isalnum():
                    (byt, inc) = doByte(chars, i, littleendian)
                    buf.write(byt)
                    i += inc
                elif chars[i] == '|':
                    buf.write('|')
                    i += 1
                elif chars[i] == ')':
                    break
                # START fix FIDO-20
                elif chars[i] == '[':
                    buf.write('[')
                    i += 1
                    (byt, inc) = doByte(chars, i, littleendian)
                    buf.write(byt)
                    i += inc
                    #assert(chars[i] == ':')
                    if chars[i] != ':':
                        return "__INCOMPATIBLE_SIG__"
                    buf.write('-')
                    i += 1
                    (byt, inc) = doByte(chars, i, littleendian)
                    buf.write(byt)
                    i += inc
    
                    #assert(chars[i] == ']')
                    if chars[i] != ']':
                        return "__INCOMPATIBLE_SIG__"
                    buf.write(']')
                    i += 1
                else:
                    raise Exception(_convert_err_msg(('Current state = \'{0}\' : Illegal character in paren').format(state), chars[i], i, chars))
            buf.write(')')
            i += 1
            state = 'start'
            # END fix FIDO-20
        elif state in ['curly', 'curly-after-bracket']:
            # {nnnn} or {nnn-nnn} or {nnn-*}
            # {nnn} or {nnn,nnn} or {nnn,}
            # when there is a curly-after-bracket, then the {m,n} applies to the bracketed item
            # The above, while sensible, appears to be incorrect.  A '.' is always needed.
            # for droid equiv behavior
            #if state == 'curly':
            buf.write('.')
            buf.write('{')
            i += 1                # skip the (
            while True:
                if chars[i].isalnum():
                    buf.write(chars[i])
                    i += 1
                elif chars[i] == '-':
                    buf.write(',')
                    i += 1
                elif chars[i] == '*': # skip the *
                    i += 1
                elif chars[i] == '}':
                    break
                else:
                    raise Exception(_convert_err_msg('Illegal character in curly', chars[i], i, chars))
            buf.write('}')
            i += 1                # skip the )
            state = 'start'
        elif state == 'specials':
            if chars[i] == '*':
                buf.write('.*')
                i += 1
            elif chars[i] == '+':
                buf.write('.+')
                i += 1
            elif chars[i] == '?':
                if chars[i + 1] != '?':
                    raise Exception(_convert_err_msg('Illegal character after ?', chars[i + 1], i + 1, chars))
                buf.write('.?')
                i += 2
            state = 'start'
        else:
            raise Exception('Illegal state {0}'.format(state))

    if 'EOF' in pos:
        buf.write(calculate_repetition('.', pos, offset, maxoffset))
        buf.write('\\Z')

    val = buf.getvalue()
    buf.close()
    return val

def main(arg=None):
    import sys

    mydir = os.path.abspath(os.path.dirname(__file__))
    print(mydir)

    xml_signature = os.path.join(mydir, 'conf', 'udfr_formats.xml')
    info = FormatInfo()
    info.load_udfr_data()
    info.save(xml_signature)
    print >> sys.stderr, 'Converted {0} UDFR formats to FIDO signatures'.format(len(info.formats))
    
if __name__ == '__main__':
    main()    
