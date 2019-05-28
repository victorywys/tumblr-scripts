import pandas as pd
import re
import numpy as np
import pickle
import os, sys
from html.parser import HTMLParser
from bs4 import BeautifulSoup
from tqdm import tqdm
from nltk.corpus import words
import argparse
import pdb
import csv
import warnings
import spacy

nlp = spacy.load('en', disable=['tagger', 'parser', 'ner'])


# Settings
parser = argparse.ArgumentParser()
parser.add_argument('dataset', nargs='?', help='Dataset name')
parser.add_argument('--debug', dest='debug', action='store_true')
args = parser.parse_args()

input_format = 'dir' # {dir, tsv, pickle}
remove_usernames = False
save_text = False
save_final = True # might be such a big file that don't want to add to pickle
debug = args.debug

# I/O
#data_dirpath = '/usr2/mamille2/tumblr/data'
data_dirpath = '../data'
dataset = args.dataset
#posts_fpath = os.path.join(data_dirpath, 'textposts_recent100.pkl') # recent 100 posts, even if don't have 100
posts_path = os.path.join(data_dirpath, f'{dataset}_posts')
posts_outpath = os.path.join(data_dirpath, f'{dataset}_posts.pkl') 
text_outpath = posts_outpath[:-3] + 'txt'


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ' '.join(self.fed)

def clean_html(html):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        soup = BeautifulSoup(html, 'lxml')
        for s in soup(['script', 'style']):
            s.decompose()

    return ' '.join(soup.stripped_strings)

def strip_tags(html):
    s = MLStripper()
    text = clean_html(str(html)).strip()
    s.feed(text)
    return s.get_data()

def find_body(post_content):
    m = re.search(r'body=(.*), note_count', post_content)
    if not m: return ''
    body = m.group(1)
    return body

def preprocess_post_content(text):
    
    if not isinstance(text, str):
        return ''

    # Find post content
    text = find_body(text)
    if text == '': return text
	    
    # Strip html tags
    nohtml = strip_tags(text)
    
    # Tokenize with spaCy
    toks = [tok.text for tok in nlp.tokenizer(nohtml.lower())]
    
    # Remove whitespace tokens
    toks = [t for t in toks if not all(c==' ' for c in t)]
    
    return ' '.join(toks)

def remove_usernames_text(data):
    """ Removes usernames, saves in separate columns """
    blog_names = set(data['source_title'].unique()) # might not all be strings
    dict_wds = set(words.words())
    blog_names = blog_names - dict_wds
    data['body_toks_no_titles'] = list(map(lambda x: [t for t in x if not t in blog_names], tqdm(data['body_toks'].tolist(), ncols=50)))
    data['body_toks_str_no_titles'] = data['body_toks_no_titles'].map(lambda x: ' '.join(x))

def save_text_file(text_rows, outpath):
    with open(outpath, 'a') as f:
        for post in text_rows:
            f.write(post + '\n')

def read_dir(posts_dirpath, debug):
    
    posts = []
    tqdm.write('\nConcatenating files into dataframe...')
    if debug:
        fnames = os.listdir(posts_dirpath)[:1]
    else:
        fnames = os.listdir(posts_dirpath)

    for fname in tqdm(fnames, ncols=50):
        fpath = os.path.join(posts_dirpath, fname)
        try:
            part = pd.read_csv(fpath, sep='\t', low_memory=False)
        except:
            part = pd.read_csv(fpath, sep='\t', engine='python', quoting=csv.QUOTE_NONE, error_bad_lines=False, warn_bad_lines=False)
        posts.extend(part.values.tolist())

    data = pd.DataFrame(posts, columns=part.columns)
    data.drop_duplicates('post_id', inplace=True)
    data.dropna(subset=['post_id'], inplace=True)
    data = data[data['post_content'].map(lambda x: isinstance(x, str) and len(x) > 0)]

    if debug:
        return data.head(100)

    else:
        return data


def main():


    # Load posts
    print("Loading data...", end=' ')
    sys.stdout.flush()

    if input_format == 'dir':
        data = read_dir(posts_path, debug)

    if input_format == 'pickle':
        if debug:
            data = pd.read_pickle(posts_fpath).head(100)
        else:
            data = pd.read_pickle(posts_fpath)
        print('done')
        sys.stdout.flush()


    # Tokenize, preprocess all posts
    print("Preprocessing posts...")
    sys.stdout.flush()

    if input_format == 'pickle':    
        data['body_toks'] = list(map(preprocess_post, tqdm(data['body'].tolist())))
        data['body_str'] = data['body_toks'].map(lambda x: ' '.join(x))

    elif input_format == 'dir':
        data['post_body'] = list(map(preprocess_post_content, tqdm(data['post_content'], ncols=50)))
        data = data[data['post_body'].map(lambda x: len(x) > 0)]
        

    # Remove usernames
    if remove_usernames:
        remove_usernames_text(data)

    # Save text file (for eg training word embeddings)
    if save_text:
        print(f"Writing text file to {text_outpath}...", end=' ')
        sys.stdout.flush()
        save_text_file(data['body_str'].tolist(), text_outpath) 
        print("done")
        sys.stdout.flush()

    # Save data
    if save_final:
        print(f"Saving tokenized file to {posts_outpath}...", end=' ')
        sys.stdout.flush()
        data.to_pickle(posts_outpath)
        print("done")
        sys.stdout.flush()

if __name__ == '__main__':
    main()
