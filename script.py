###v0.2
###AlternativeOne

from flask import Flask, request, current_app, Response, jsonify, render_template, make_response, redirect
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'

app = Flask(__name__)

@app.route('/catalog')
def root():
    resp=Response("""
    <?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>urn:root</id>
  <link rel="self"  
        href="/catalog"
        type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
  <link rel="start"
        href="/catalog"
        type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
        
  <link rel="search"
      href="search.xml"
      type="application/opensearchdescription+xml"/>
  <title>AO3 to OPDS: Catalog</title>
  <updated>2023-04-28T23:50:00Z</updated>
  <author>
    <name>Archive of Our Own</name>
    <uri></uri>
  </author>

  <entry>
    <title>Books &amp; Literature</title>
    <link rel="subsection"
          href="/subcatalog/books"
          type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
    <updated>2023-04-28T23:50:00Z</updated>
    <id>urn:subroot:books</id>
    <content type="text">All Books &amp; Literature fandoms.</content>
  </entry>
</feed>
    """)
    
    resp.headers['Content-Type'] = 'text/xml'
    return resp
    
@app.route('/search.xml')
def search_description():
    resp=Response("""<?xml version="1.0" encoding="UTF-8"?>
           <OpenSearchDescription>
                <Url type="application/atom+xml;profile=opds-catalog"
                     xmlns:atom="http://www.w3.org/2005/Atom" 
                     template="/search?q={searchTerms}"/>
           </OpenSearchDescription>
         """)
         
    resp.headers['Content-Type'] = 'text/xml'
    return resp
    
@app.route('/search')
def search():
    query=''
    try:
        query=request.args.get('q')
    except:
        query=''
        
    page=1
    try:
        page=int(request.args.get('page'))
    except:
        page=1
        
    baseUrl='https://archiveofourown.org'
    searchUrl=baseUrl+'/works/search?page=%d&work_search[query]=%s'
    
    req=requests.get(searchUrl % (page, query), headers={'User-Agent' : USER_AGENT}).text
    
    worksEntries=''
    
    soup = BeautifulSoup(req, 'html.parser')
    works=soup.select('li.work')
    for work in works:
        try:
            title=work.select('.heading')[0].select('a')[0].get_text()
            author=''
            try:
                author=work.select('.heading')[0].select('a')[1].get_text()
            except:
                author='Anon.'
            authorUrl=''
            try:
                authorUrl=baseUrl+work.select('.heading')[0].select('a')[1]['href']
            except:
                authorUrl=''
            summary=''
            try:
                summary=work.select('.summary')[0].prettify()
                summary=summary.replace('</p><p>', '\n').replace('<p>', '').replace('</p>', '').replace('<br/>', '')
                summary=re.sub(r'<.*>', '', summary)
            except:
                try:
                    summary=work.select('.summary')[0].get_text()
                except:
                    summary=''
                
            try:
                tags=work.select('.tags')[0].select('.tag')
                tags=[tag.get_text() for tag in tags]
                summary=summary+'Tags:\n'+', '.join(tags)
            except Exception as e:
                print(format_exception(e))
                
            workId=work.select('.heading')[0].select('a')[0]['href'].split('/')[-1]
            
            lang=''
            try:
                lang=work.select('.language')[1]
            except:
                lang=''
                
            updated=work.select('.datetime')[0]
            try:
                updated=datetime.strptime(updated, '%d %b %Y')
                updated=datetime.strptime(updated, '%Y-%m-%dT%H:%M:%S.%fZ')
            except:
                updated=work.select('.datetime')[0]
        
            entry="""
        <entry>
    <title>%s</title>
    <id>urn:work:%s</id>
    <updated>%s</updated>
    <author>
      <name>%s</name>
      <uri>%s</uri>
    </author>
    <dc:language>%s</dc:language>
    <category scheme="http://www.bisg.org/standards/bisac_subject/index.html"
              term="FIC020000"
              label="FICTION"/>
    <summary type="text">%s</summary>
        
        <link rel="http://opds-spec.org/acquisition"
          href="/download/epub/%s"
          type="application/epub+zip"/>
 </entry>
        """ % (title, workId, updated, author, authorUrl, lang, summary, workId)
        
            worksEntries=worksEntries+entry
        except Exception as e:
            print(format_exception(e))
    
    now=datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    
    nextPageNavigation=''
    try:
        soup.select('.next')[0].select('a')[0]['href']
        
        nextPageNavigation="""
        <link rel="next"    
        href="/search?q=%s&page=%d"
        type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
        """ % (query, page+1)
    except:
        nextPageNavigation=''
    
    resp=Response("""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:dc="http://purl.org/dc/terms/"
      xmlns:opds="http://opds-spec.org/2010/catalog">
  <id>urn:search:%s</id>

<link rel="self"    
        href="/search?q=%s&page=%d"
        type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
  <link rel="start"  
        href="/catalog"
        type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
  <link rel="up"      
        href="/catalog"
        type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
  %s

  <title>Search: %s</title>
  <updated>%s</updated>
  <author>
    <name>Archive of Our Own</name>
    <uri></uri>
  </author>

  %s
</feed>
""" % (query, query, page, nextPageNavigation, query, now, worksEntries))

    resp.headers['Content-Type'] = 'text/xml'
    return resp
    
@app.route('/subcatalog/<id>')
def subroot(id):
    if id=='books':
        return current_app.send_static_file('books.xml')
    
@app.route('/fandom/<id>.xml')
def fandom_feed(id):
    page=1
    try:
        page=int(request.args.get('page'))
    except:
        page=1

    baseUrl='https://archiveofourown.org'

    reqUrl='https://archiveofourown.org/tags/%s/works?page=%d' % (id, page)
    req=requests.get(reqUrl, headers={'User-Agent' : USER_AGENT}).text
    
    worksEntries=''
    
    soup = BeautifulSoup(req, 'html.parser')
    works=soup.select('li.work')
    for work in works:
        try:
            title=work.select('.heading')[0].select('a')[0].get_text()
            author=''
            try:
                author=work.select('.heading')[0].select('a')[1].get_text()
            except:
                author='Anon.'
            authorUrl=''
            try:
                authorUrl=baseUrl+work.select('.heading')[0].select('a')[1]['href']
            except:
                authorUrl=''
            summary=''
            try:
                summary=work.select('.summary')[0].prettify()
                summary=summary.replace('</p><p>', '\n').replace('<p>', '').replace('</p>', '').replace('<br/>', '')
                summary=re.sub(r'<.*>', '', summary)
            except:
                try:
                    summary=work.select('.summary')[0].get_text()
                except:
                    summary=''
                
            try:
                tags=work.select('.tags')[0].select('.tag')
                tags=[tag.get_text() for tag in tags]
                summary=summary+'Tags:\n'+', '.join(tags)
            except Exception as e:
                print(format_exception(e))
                
            workId=work.select('.heading')[0].select('a')[0]['href'].split('/')[-1]
            
            lang=''
            try:
                lang=work.select('.language')[1]
            except:
                lang=''
                
            updated=work.select('.datetime')[0]
            try:
                updated=datetime.strptime(updated, '%d %b %Y')
                updated=datetime.strptime(updated, '%Y-%m-%dT%H:%M:%S.%fZ')
            except:
                updated=work.select('.datetime')[0]
        
            entry="""
        <entry>
    <title>%s</title>
    <id>urn:work:%s</id>
    <updated>%s</updated>
    <author>
      <name>%s</name>
      <uri>%s</uri>
    </author>
    <dc:language>%s</dc:language>
    <category scheme="http://www.bisg.org/standards/bisac_subject/index.html"
              term="FIC020000"
              label="FICTION"/>
    <summary type="text">%s</summary>
        
        <link rel="http://opds-spec.org/acquisition"
          href="/download/epub/%s"
          type="application/epub+zip"/>
 </entry>
        """ % (title, workId, updated, author, authorUrl, lang, summary, workId)
        
            worksEntries=worksEntries+entry
        except Exception as e:
            print(format_exception(e))
    
    now=datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    
    nextPageNavigation=''
    try:
        soup.select('.next')[0].select('a')[0]['href']
        
        nextPageNavigation="""
        <link rel="next"    
        href="/fandom/%s.xml?page=%d"
        type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
        """ % (id, page+1)
    except:
        nextPageNavigation=''
    
    resp=Response("""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:dc="http://purl.org/dc/terms/"
      xmlns:opds="http://opds-spec.org/2010/catalog">
  <id>urn:fandom:%s</id>

<link rel="self"    
        href="/fandom/%s.xml?page=%d"
        type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
  <link rel="start"  
        href="/catalog"
        type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
  <link rel="up"      
        href="/catalog"
        type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
  %s

  <title>%s - Latest Updated</title>
  <updated>%s</updated>
  <author>
    <name>Archive of Our Own</name>
    <uri></uri>
  </author>

  %s
</feed>
""" % (id, id, page, nextPageNavigation, id, now, worksEntries))

    resp.headers['Content-Type'] = 'text/xml'
    return resp
    
@app.route('/download/epub/<id>')
def downloadEpub(id):
    baseUrl='https://archiveofourown.org'
    
    work_req=requests.get(baseUrl+'/works/'+id, headers={'User-Agent' : USER_AGENT}).text
        
    work_soup = BeautifulSoup(work_req, 'html.parser')

    downloadEpubUrl=baseUrl+work_soup.select('li.download')[0].select('a')[1]['href']
    
    return redirect(downloadEpubUrl)

def format_exception(e):
    import traceback
    import sys

    exception_list = traceback.format_stack()
    exception_list = exception_list[:-2]
    exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
    exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))

    exception_str = "Traceback (most recent call last):\n"
    exception_str += "".join(exception_list)
    # Removing the last \n
    exception_str = exception_str[:-1]

    return exception_str

###app.run(host='localhost', port=8000, debug=True)
