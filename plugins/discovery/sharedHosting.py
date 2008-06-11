'''
sharedHosting.py

Copyright 2006 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''

import core.controllers.outputManager as om
# options
from core.data.options.option import option
from core.data.options.optionList import optionList

from core.controllers.w3afException import w3afException
import core.data.kb.knowledgeBase as kb
import core.data.kb.vuln as vuln
from core.data.searchEngines.msn import msn as msn
from core.controllers.basePlugin.baseDiscoveryPlugin import baseDiscoveryPlugin
import core.data.parsers.urlParser as urlParser
import socket
from core.controllers.w3afException import w3afRunOnce
import core.data.constants.severity as severity

class sharedHosting(baseDiscoveryPlugin):
    '''
    Use MSN search to determine if the website is in a shared hosting.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        self._run = True
        
        # User variables
        self._resultLimit = 300

        
    def discover(self, fuzzableRequest ):
        '''
        @parameter fuzzableRequest: A fuzzableRequest instance that contains (among other things) the URL to test.
        '''
        if not self._run:
            # This will remove the plugin from the discovery plugins to be runned.
            raise w3afRunOnce()
        else:
            # I will only run this one time. All calls to sharedHosting return the same url's
            self._run = False
            
            self._msn = msn( self._urlOpener )
            
            domain = urlParser.getDomain( fuzzableRequest.getURL() )
            if self._msn.isPrivate( domain ):
                
                om.out.debug('sharedHosting plugin is not checking for subdomains for domain: ' + domain + ' because its a private address.' )
                
            else:
                # Get the ip and do the search
                addrinfo = None
                try:
                    addrinfo = socket.getaddrinfo(domain, 0)
                except:
                    raise w3afException('Could not resolve hostname: ' + domain )
                ips = [info[4][0] for info in addrinfo]
                
                # Selecting the first IP address of the dns response
                ip = ips[0]
                results = self._msn.getNResults('ip:'+ ip, self._resultLimit )
                
                results = [ urlParser.baseUrl( r.URL ) for r in results ]
                results = list( set( results ) )
                
                # not vuln by default
                isVulnerable = False
                
                if len(results) > 1:
                    # We may have something...
                    isVulnerable = True
                    
                    if len(results) == 2:
                        # Maybe we have this case:
                        # [Mon 09 Jun 2008 01:08:26 PM ART] - http://216.244.147.14/
                        # [Mon 09 Jun 2008 01:08:26 PM ART] - http://www.business.com/
                        # Where www.business.com resolves to 216.244.147.14; so we don't really
                        # have more than one domain in the same server.
                        res0 = socket.gethostbyname( urlParser.getDomain( results[0] ) )
                        res1 = socket.gethostbyname( urlParser.getDomain( results[1] ) )
                        if res0 == res1:
                            isVulnerable = False
                
                if isVulnerable:
                    v = vuln.vuln()
                    v.setURL( fuzzableRequest.getURL() )
                    v.setId( 0 )
                    v['alsoInHosting'] = results
                    v.setDesc( 'The web application under test seems to be in a shared hosting.' )
                    v.setName( 'Shared hosting' )
                    v.setSeverity(severity.MEDIUM)
                    
                    kb.kb.append( self, 'sharedHosting', v )
                    om.out.vulnerability( v.getDesc(), severity=v.getSeverity() )
                    
                    om.out.vulnerability('This list of domains, and the domain of the web application under test, all point to the same IP address (%s):' % ip, severity=severity.MEDIUM )
                    for url in results:
                        om.out.vulnerability('- ' + url , severity=severity.MEDIUM)
                        kb.kb.append( self, 'domains', urlParser.getDomain(url) )
                
        return []
    
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''
        d2 = 'Fetch the first "resultLimit" results from the MSN search'
        o2 = option('resultLimit', self._resultLimit, d2, 'integer')

        ol = optionList()
        ol.add(o2)
        return ol
        
    def setOptions( self, optionsMap ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        self._resultLimit = optionsMap['resultLimit'].getValue()
    
    def getPluginDeps( self ):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return []
    
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin tries to find out if the web application under test is stored in a shared hosting.
        The procedure is pretty simple, using MSN search engine, the plugin searches for "ip:1.2.3.4"
        where 1.2.3.4 is the IP address of the webserver.
        
        One configurable option exists:
            - resultLimit
            
        Fetch the first "resultLimit" results from the "ip:" MSN search.
        '''
