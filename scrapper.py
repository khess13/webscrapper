import re, os, json, csv
import urllib.request, urllib.error, urllib.parse
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from nltk.tokenize import word_tokenize
from pathlib import Path

def get_files_from_dir(filepath, ext = '.html') -> list:
    filesindir = os.listdir(filepath)
    #tilda indicates open temp file, excluding these
    xlsxfiles = [f for f in filesindir if ext in f and not 'Procurement Services' in f]
    if len(xlsxfiles) == 0:
        print('No files found, try checking the extension.')
    else:
        return xlsxfiles

def souper(filepath) -> 'soup':
    with open(filepath, 'r', encoding='utf8') as page:
        soup = BeautifulSoup(page, 'html.parser')
        return soup

def text_extract(soupCommand, reCompile, switch) -> list:
    # switch for just text extraction, no further capture
    listName = []
    for v in soupCommand:
        if switch == True:
            return v.get_text()
        else:
            extract = v.get_text()
            search = re.search(reCompile, extract)
        if search:
            listName.append(search.group())
    return listName

def webpage_to_file(key, url):
    response = urllib.request.urlopen(url)
    responseRead = response.read()
    with open(key+'.html', 'wb') as file:
        file.write(responseRead)

root = os.getcwd()
root_parent = str(Path(os.getcwd()).parents[0]) + "\\"
mainPage = root + '\\Procurement Services.html'

links = {}
domain = 'https://procurement.sc.gov'
#parent page
pPage = 'https://procurement.sc.gov/contracts/search?b=9918-0-0'

#soup = BeautifulSoup(mainPage.content, 'html.parser')
refresh = input('Refresh webpages? Y/N')
if refresh.lower() == 'y':
    webpage_to_file('Procurement Services', pPage)
    print('Retrieved new main page')
    soup = souper(mainPage)
    #retrieve links
    print('Finding links')

    for a in soup.find_all('a')[23:]:
        extract = a.get_text()
        #replace slashes,etc
        extract = extract.replace('/','-')
        extract = extract.replace(':', '')
        extract = extract.strip()
        key = extract
        if re.search('contracts', a['href']):
            #fix line with the same name, diff urls
            key = extract+a['href'][20:]
            links[key] = (a['href'])
    #spider the links
    for key, url in links.items():
        print(url)
        webpage_to_file(key, domain + url)
else:
    print('Skipped refresh')

#rebuild
filesindir = get_files_from_dir(root)
print('Processing new pages')

all_dfs_list = []
stopwords = ['.',',','LLC','US','Corporation','Incorporated','Corp','Inc']
df = pd.DataFrame(columns=['VendorNo','VendorName','ContractNo',
                           'SolicitationName','SolicitationNo',
                           'URL'])
for file in filesindir:
    print(f'Processing {file}')
    #clear lists
    vendorNoList = []
    vendorNameList = []
    solicitationNoList = []
    contractNoList = []

    soup = souper(file)
    brandPattern = re.compile('.+(?=\.html)')
    brandSearch = re.search(brandPattern, file)
    if brandSearch:
        brandSelect = brandSearch.group().upper()
    #make patterns for search
    vendorNameSearch = re.compile(r'(?<=Vendor:\s).+')
    vendorNoSearch = re.compile(r'7[0-9]{9}')
    solicitationNoSearch = re.compile(r'(?<=Solicitation#:\s).+')
    contractNoSearch = re.compile(r'(?<=Contract#:\s).+')
    #not needed, but leaving for no reason
    contractNameSearch = re.compile(r'(\w+\W*)')

    #subset soup
    vendorName = soup.find_all('td', class_='dta100 gry spc3a')
    vendorNo = soup.find_all('td', class_='dta100 spc3')
    solicitationNo = soup.find_all('td', class_='dta100 spc3')
    contractNo = soup.find_all('td', class_='dta100 spc3')
    #contractName =  soup.find_all('td', class_='dta100 cblu spc6')
    #soliciation_name
    contractName =  soup.find_all('td', class_='dta100 spc2 txt2')

    #extract from soup
    vendorNoList = text_extract(vendorNo, vendorNoSearch, False)
    vendorNameList = text_extract(vendorName, vendorNameSearch, False)
    solicitationNoList = text_extract(solicitationNo, solicitationNoSearch, False)
    contractNoList = text_extract(contractNo, contractNoSearch, False)
    contractNameList = text_extract(contractName, contractNameSearch, True)

    #check for missing values
    if len(solicitationNoList) == 0:
        solicitationNoList = ['N/A']
    #make frame
    for venno,venna,conno in zip(vendorNoList,vendorNameList,contractNoList):
        #TODO - fix contract name, soliciation No
        next_entry = pd.Series([venno,venna,conno,contractNameList,
                                solicitationNoList[0].strip(),domain+'/'+file],
                                index=df.columns)
        df = df.append(next_entry, ignore_index=True)

with pd.ExcelWriter('export.xlsx') as writer:
    df.to_excel(writer, index=False)

print('Processing Complete!')
