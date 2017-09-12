from __future__ import division
import requests
import sys
import re
from bs4 import BeautifulSoup
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.stem import PorterStemmer
import operator
import nltk
import csv

__author__ = "Chris Mathew Dani"
__email__ = "cdani@hawk.iit.edu"

class PageSummary():
    def __init__(self, tags_of_importance,tags_to_ignore, classifiers):
        """
        Constructor that assigns the default values needed by the parser
        Input arguments:
            acceptedTags: List of tags whose content has to be analyzed
            unwantedTags: List of unwanted subtags that has to be ommited
        Variables set:
            relevant: Flag that denotes that the data in the tag is relevant and needs analyzis
            acceptedTags: List of tags whose content has to be analyzed
            unwantedTags: List of unwanted subtags that has to be ommited
            wordCount: Dictionary that stores the count of words
            stopwords: Set of stopwords from NLTK that shouldn't be considered
            retailer_url: Set of URLs that corespond to a retailer, can be updated to improve results
            
        """
        self.tags_of_importance = tags_of_importance
        self.tags_to_ignore = tags_to_ignore
        self.classifiers = classifiers
        self.retailer_url = []
        with open('retailer_list.csv','rb') as csvin:
            csvin = csv.reader(csvin, delimiter='\t')
            for row in csvin:
                self.retailer_url.append(row[0].lower())
                                                  
    '''
    get the page soup based on the url, if not possible returns None
    parameter: url, to get data from
    '''
    def get_page_soup(self, url):
        try:
            content = requests.get(url)
            if content.status_code != 200:
                try:
                    page = urllib2.urlopen(url).read()
                    soup = BeautifulSoup(page)
                except:
                    print "Page not reachable"
                    #sys.exit(0) 
            else:
                page = content.text
            soup = BeautifulSoup(page, "html.parser")
            self.soup = soup
            return soup
        except:
            return None

    '''
    clean the souped data based on the tags that needed to be removed
    parameters: soup, that contains page data in soup format
                tags_to_remove, a list that contains the list of
                                tags that should be removed from the soup
    returns: cleaned soup
    '''            
    def clean_soup(self, soup):
        for i in soup.findAll(tags_to_ignore):
            temp = i.extract()
        return soup


    '''
    generate one word and two word fequency from the souped data
    parameter: soup, contains page data in soup format
                tag_dict, contains the tag and list of data for that tag
                tags_of_importance, contains the tags that are looked for from the website

    return: dictionary containing word(s) and frequency
    '''
    def generate_word_frequency(self, soup, tag_dict):
        word_frequency = {}
        len_dict = {}
        for tag in tag_dict:
            weight = self.get_tag_weight(soup, tag,  len_dict)
            for element in tag_dict[tag]:
                words = element.split(" ")
                for i in range(0,len(words)):
                    words[i] = words[i].lower().encode('ascii','ignore').strip()
                    
                    if words[i] in word_frequency:
                        word_frequency[words[i]] += 1*weight
                    else:
                        word_frequency[words[i]] = 1*weight
                    #read two words together
                    if(i < len(words)-1):
                        words[i+1] = words[i+1].lower().encode('ascii','ignore').strip()
                        if words[i] == '':
                            continue
                        two_words = words[i] + ' ' + words[i+1]
                        if two_words in word_frequency:
                            word_frequency[two_words] += 2*weight
                        else:
                            word_frequency[two_words] = 2*weight           
        return word_frequency

    '''
    generate dictionary of tags and list of wordlines assiciated with that tag
    parameters: soup, of the page
                tags_of_interest, from where interested tags are taken
    return: dictionary of tag with corresponding lines of words
    '''
    def generate_tag_group_from_soup(self, soup):
        tag_map = {}
        for tag in tags_of_importance:
            for element in soup.findAll(tag):
                if tag not in tag_map:
                    tag_map[tag] = list()
                #clean line and then append it to list of tags
                line = element.text.strip().replace("\n","")
                if(line != "" and line != " "):
                    tag_map[tag].append(line)
        return tag_map

    '''
    function to remove the stop words
    parameters: word_count, which is the dictionary of words and their freuquency
                language, the language where the stop words need to be removed
                list_to_ignore, a list that has words that have to be ignored
                        those not covered by the stopwords package
    '''
    def remove_stop_words(self, word_count, language, list_to_ignore):
        keys = word_count.keys()
        stopwords = nltk.corpus.stopwords.words(language)
        for word in keys:
            #if the word was a single character, remove it
            if len(word) < 2:
                word_count.pop(word)
                continue
            if word in stopwords:# or (word in list_to_ignore):
                word_count.pop(word)
            elif word in list_to_ignore:
                word_count.pop(word)
            split_words = word.split(" ")
            #if it was a two word key, then remove it as well
            if(len(split_words) > 1):
                for individual_word in split_words:
                    if individual_word in stopwords:
                        try:
                            word_count.pop(word)
                        except:
                            pass
                        
    '''
    returns the tag weight of the tags to be factored into when doing the word frequency
    parameters: soup, containing the page in soup format
                tag, containing the tag which weight has to be computed
                len_dict, a dictionary of tags and the length of data for each
    returns: weight for the tag relative to the page
    '''
    def get_tag_weight(self, soup, tag, len_dict):
        if "all_tags" not in len_dict.keys():
            total_len = 0
            for cur_tag in tags_of_importance:
                total_len = total_len+ self.get_len_tag_data(soup, cur_tag, len_dict)
            len_dict["all_tags"] = total_len

        val = float((self.get_len_tag_data(soup,tag,len_dict))/len_dict["all_tags"])
        weight = float(1-(val))
        return weight

    '''
    returns the tag length within the page in soup format
    parameters: soup, containing the page in soup format
                tag, containing the tag which weight has to be computed
                len_dict, a dictionary of tags and the length of data for each
    returns: length for the tag data in the page
    '''
    def get_len_tag_data(self, soup, tag, len_dict):
        if tag in len_dict.keys():
            return len_dict[tag]
        else:
            cur_len = 0
            for i in soup.findAll(tag):
                cur_len = cur_len + len(i.text.strip())
            len_dict[tag] = cur_len
            return cur_len
        
    '''
    returns if the given url is a retailer website
    parameters: url, the url to be checked in string format
    returns: true for retailer, false if not
    '''
    def check_retailer(self, url):
        for cur_url in self.retailer_url:
            clean_url = cur_url.replace("https://","").replace("http://","")
            if(clean_url.find("/") >= 0):
                clean_url = clean_url[:clean_url.find("/")-1]
            clean_url = clean_url[clean_url.find('.')+1:]
            if url.find(clean_url) >= 0:
                return True
        return False
    
    '''
    returns the lemmatized word frequency given the normal word frequency
    parameters: word_count, the word and its frequencies
    returns: the lemmatized word frequency
    '''
    def generate_lemm_frequency_from_word_freq(self, word_count):
        lemm_count = {}
        lemm = WordNetLemmatizer()
        for word in word_count:
            lemm_word = lemm.lemmatize(word)
            if lemm_word in lemm_count:
                lemm_count[lemm_word] = lemm_count[lemm_word] + word_count[word]
            else:
                lemm_count[lemm_word] = word_count[word]
        return lemm_count

    '''
    returns the lemmatized word frequency given the normal word frequency
    parameters: word_count, the word and its frequencies
    returns: the lemmatized word frequency
    '''
    def classify_on_url(self, url):
        for name in classifiers:
            if(url.lower().find(name) >= 0):
                return classifiers[name]
        url_split_element = self.split_url(url)
        for element in url_split_element:
            for name in classifiers:
                if(element.lower().find(name) >= 0):
                    return classifiers[name]
        if(self.check_retailer(url) is True):
            return "retailer"
        return None

    '''
    returns the words from the url
    parameters: URL
    returns: words in the url
    '''
    def split_url(self, url):
        pos_slash = url.find("/")
        words = url[:pos_slash].split(".")
        words.extend(url[pos_slash+1:].split("/"))
        words_list = []
        for i in range(0,len(words)):
            if(words[i].find("%20") >= 0):
                words_list.extend(words[i].split("%20"))
            if(words[i].find("=") >= 0):
                words_list.extend(words[i].split("="))
            if(words[i].find("?") >= 0):
                words_list.extend(words[i].split("?"))
            if(words[i].find("-") >= 0):
                words_list.extend(words[i].split("-"))
            if(words[i].find("_") >= 0):
                words_list.extend(words[i].split("_"))
        return words_list

    '''
    returns the classification based on page keywords
    parameters: URL and keywords
    returns: the classification
    '''    
    def classify_on_page(self, url, keywords ):
        if keywords is None:
            return None
        for word in keywords:
            for name in classifiers:
                if(word.lower().find(name) >= 0):
                    return classifiers[name]
            
#tags of interest
tags_of_importance = ["h6", "h5", "h4", "h3", "h2", "h1", "title", "meta","div"]
tags_to_ignore = ["script", "style"]

#categories to consider
press_release = "PRESS RELEASE"
store_locator = "STORE LOCATOR"
white_paper = "WHITEPAPER"
product_detail = "PRODUCT DETAIL"
documentation = "DOCUMENTATION"
infographic = "INFOGRAPHIC"
product_comparison = "PRODUCT COMPARISON"
product_category = "PRODUCT CATEGORY"

#dictionary to map keywords to categories for direct keyword matches
classifiers = {"news":press_release, "release" : press_release, "press": press_release, "archive": press_release, "pressrelease": press_release,
               "whitepaper": white_paper , "whitepaper":white_paper, "library":white_paper,
               "doc":documentation, "manual": documentation,
               "store":store_locator, "locator": store_locator, "location" : store_locator,
               "infographic": infographic, "graphic": infographic,
               "vs": product_comparison, "compariso": product_comparison, "compar": product_comparison
               }

#initialize pagesummary object
mypage = PageSummary(tags_of_importance, tags_to_ignore, classifiers)

'''
returns the top words based on its frequency 
parameters: URL, and page object , and the count of words to return
returns: the top keywords that represent a page
'''
def get_top_keywords(url, mypage, count):

    #clean url to ensure it can be accessed
    if(url.find("http://") >= 0 or url.find("https://") >= 0 ):
        pass
    else:
        if url.find("www") != 0:
            url = "www." + url
        url = "https://" + url

    #return none , effectively skipping page, else use chrome/firefox webdriver and get page(not implemented)
    if(url.find(".jsp") >= 0):
        return None, None

    #read the soup version of the page
    soup = mypage.get_page_soup(url)

    #error checking
    if soup == None:
        return None, None
    
    #clean soup to remove tags
    soup = mypage.clean_soup(soup)

    #generate tags
    tag_dict = mypage.generate_tag_group_from_soup(soup)

    #list of extra words to ignore
    ignore_words = [""," ","  "]

    #generate word frequency
    word_count = mypage.generate_word_frequency(soup, tag_dict)

    #word frequency count that has been lemmatized
    lemm_count = mypage.generate_lemm_frequency_from_word_freq(word_count)

    #removing any stop words
    mypage.remove_stop_words(lemm_count, "english",ignore_words)

    #sort the list
    sorted_lemm_count = sorted(lemm_count.items(), key=operator.itemgetter(1), reverse=True)
    
    keyword_list = []
    for i in range(0, min(count, len(sorted_lemm_count))):
        keyword_list.append(sorted_lemm_count[i][0])
    return keyword_list, soup
    

'''
classifier starts here
read urls from file and classify
'''
url_num = 1
with open('sample_urls.tsv','rb') as tsvin, open('classified_urls.tsv', 'wb') as csvout:

    #input to read file with URLs
    tsvin = csv.reader(tsvin, delimiter='\t')
    
    #output file to write results
    csvout = csv.writer(csvout, delimiter='\t')
    csvout.writerows([["Number", "Classification", "URL"]])
    for row in tsvin:
        #read the url
        cur_url = row[0]
        print "URL Number " , url_num , " Processing: " , cur_url

        #classify based on URL
        classification = mypage.classify_on_url(cur_url)

        #second page level classification if it as a retailer 
        if classification == "retailer":
            keywords, soup = get_top_keywords(cur_url, mypage, 30)
            if(soup is not None and keywords is not None):
                classification = product_category
                for i in soup:
                    try:
                        i = i.text
                    except:
                        pass
                    i = i.lower()

                    if(i.find('specification') >= 0 or i.find('description') >= 0):
                        classification = product_detail
                        break
            if classification == "retailer":
                classification = product_detail

        #if no classification, attempt to classify based on keywords on the page content
        elif classification is None:
            try:
                classification = mypage.classify_on_page(cur_url, keywords)
            except:
                pass
            
        #write result to the file
        csvout.writerows([[url_num, classification, cur_url]])
        url_num = url_num + 1
        print "Done , Classification ", classification

