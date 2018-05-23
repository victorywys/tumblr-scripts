import pandas as pd
import pickle
import numpy as np
import re
import os
import sys
import pdb
from tqdm import tqdm


class IdentityAnnotator():

    def __init__(self, data_dirpath):

        self.states_path = os.path.join(data_dirpath, 'states.csv')
        self.nationalities_path = os.path.join(data_dirpath, 'nationalities.txt')
        self.ethnicities_path = os.path.join(data_dirpath, 'ethnicities.txt')
        self.countries_path = os.path.join(data_dirpath, 'countries.txt')
        self.terms_path = os.path.join(data_dirpath, 'search_terms.pkl')
        self.excl_terms_path = os.path.join(data_dirpath, 'excl_terms.pkl')
        self.terms, self.excl_terms, self.terms_re = self._pattern()

    def _pattern(self):

        # Load US states
        states = [s.lower() for s in pd.read_csv(self.states_path)['State'].tolist()]

        # Load nationalities
        with open(self.nationalities_path) as f:
            nats = [nat.lower() for nat in f.read().splitlines() if (len(nat) > 3 and not nat in states)]

        # Load ethnicities
        outlist = states + ['coast']
        with open(self.ethnicities_path) as f:
            eths = [e.split()[0].lower() for e in f.read().splitlines() if (len(e.split()[0]) > 4 and not e.split()[0].lower() in outlist)]

        # Load countries
        with open(self.countries_path) as f:
            countries = [c.lower() for c in f.read().splitlines()]

        # Regex patterns
        terms = {
                'age': [r'(?:[^-+\w]|^)([1-5]{1}[0-9]{1})[^-+0-9]|^([1-5]{1}[0-9]{1})$',
                       r'twelve',
                       r'thirteen',
                       r'fourteen',
                       r'fifteen',
                       r'sixteen',
                       r'seventeen',
                       r'eighteen',
                       r'nineteen',
                        r'(twenty|thirty|forty|fifty)([ -](one|two|three|four|five|six|seven|eight|nine))?',
                        r'\bage\b',
                        r'\by\/o\b', r'\by\.o\b'
                        r'\bkid\b',
                        r'\bxvi{0-3}\b',
                        r'\bxix\b',
                        r'\bxxi{0-3}\b',
                        r'\bxxiv\b',
                        r'\bxxvi{0-3}\b',
                        r'\bxxix\b',
                       ],
                'location': [r'\b{}\b'.format(el) for el in countries + states] + [
                        r'\bu\.?k\.?\b', r'\busa\b', r'\bu\.s\.?', r'méxico', r'\baus\b', r'\bmx\b', r'\bnz\b',
                        r'\bca\b', r'\btx\b', r'\bfl\b', r'\bnc\b', r'\bpa\b', r'\bnj\b', r'\bnc\b', r'\bcali\b', r'\baz\b', r'\bal\b', r'\bsocal\b', r'\bwa\b', r'\bva\b', r'\bga\b', r'midwest',
                        r'london', r'chicago', r'\bdc\b', r'\bny\b', r'\bnyc\b', r'new york', r'\bsan\b', r'istanbul', r'toronto', r'\batl\b', r'\bpnw\b',
                        r'\bnorth\b', r'\bsouth\b', r'\beast\b', r'\bwest\b',
                        ],
                'gender': [r'male\b', r'female', 
                            r'trans', r'ftm', r'mtf', r'\bcis',
                            r'girl\b', r'boy\b', r'\bman\b', r'guy\b', r'woman', r'gu+rl', r'gii+rl',
                            r'non-binary', r'nonbinary', r'\bnb\b', r'agender', r'neutrois',
                            r'\bmom\b', r'mum', r'\bdad\b', r'wife', r'husband', r'\bbrother\b', r'\bson\b', r'\bsister\b',
                            r'bigender', r'lgbt', r'genderfluid', r'gender-fluid',
                            r'princess', r'queen', r'\blady\b', r'daughter', r'mommy', # added by bootstrapping
                            ],
                'sexual orientation': 
                             [r'gay', r'straight', r'lesbian', r'\bhomo',
                               r'bisexual', r'\bbi\b', r'pansexual', r'\bpan\b', r'\bwlw\b', r'\bmlm\b',
                               r'lgbt', r'queer',
                               r'\bace\b', r'\basexual', r'aro-ace', r'aro/ace',
                                r'demisexual', # added by bootstrapping
                             ],
                 'pronouns': [
                     r'(?:\W|\b)she(?:\W|\b)', r'(?:\W|\b)her(?:\W|\b)',
                     r'(?:\W|\b)he(?:\W|\b)', r'(?:\W|\b)him(?:\W|\b)',
                     r'(?:\W|\b)they(?:\W|\b)', r'(?:\W|\b)them(?:\W|\b)',
                     r'it/its',
                     r'pronouns'
                        ],
                'personality type': [
                    r'(?:i|e|a)(?:s|n)(?:t|f)(?:j|p)',
                    r'introvert',
                    r'extrovert', 
                    r'ambivert',
                    r'\b[0-9]w[0-9]\b',
                    r'\baries\b', r'\btaurus\b', r'\bgemini\b', r'\bcancer\b', r'\bleo\b', r'\bvirgo\b', r'\blibra\b', r'\bscorpius\b',
                    r'slytherin', r'ravenclaw', r'hufflepuff', r'gryffindor', # added by bootstrapping
                    r'neutral', r'chaotic', r'lawful', # added by bootstrapping
                    ],
                'ethnicity/nationality': [r'\b{}\b'.format(el) for el in eths + nats] + 
                        [r'latino', r'latina', r'cubana', r'cubano', r'chilena', r'chileno', r'mexicano', r'mexicana', r'filipina',
                        r'palestinian'],
                'relationship status': [
                    r'taken', r'married', r'single', r'engaged', r'husband', r'spouse', r'wife', r'newlywed',
                    r'in a rl', r'in rl', r'in a relationship',
                ],
                'roleplay': [
                    r'roleplay', r'\brp\b', r'selective', r'semi-selective', r'm!a', r'\boc\b', r'\bpenned\b', r'muse',
                ],
                'fandoms': [
                    r'\bfan\b', r'kpop', r'fandom', r'marvel', r'fandoms', r'\bstan\b', r'multi-fandom', r'multiship', r'multi-ship',
                    r'fanatic',
                    r'k-pop', r'bts', r'exo', r'army', r'got7', r'yuri', r'undertale', r'yaoi', r'riverdale', r'5sos', r'bnha',
                    r'star wars', r'\brey\b', r'\breylo', r'universe', r'multiverse', r'canon', r'verse',
                    r'voltron', r'otaku', r'\bshipper', r'\bships', r'sims', r'multiship', 'multi-ship', 'single-ship',
                    r'swiftie',
                    r'\bphan\b',
                    r'hamilton',
                    r'series',
                    r'potterhead', r'hp', r'harry potter',
                    r'pokemon',
                    r'sherlock',
                    r'disney',
                ],
                'interests': [
                    r'\barts?\b', r'music', r'anime', r'books', r'photography', r'fashion', r'memes', r'nature', r'food',
                    r'coffee', r'\bcats?\b', r'aesthetics?', r'games', r'draw', r'writing', r'book', r'travel',
                    r'tv', r'poetry', r'write', r'manga', r'pics', r'horror', r'design',
                    r'tattoos', r'movies', r'dogs?', r'\btea\b', r'bands', r'makeup', r'animals?', r'memes?', 
                    r'drawing', r'metal', r'fitness', r'history', r'science', r'film', r'gifs', r'photos', r'reading',
                    r'comics', r'lifestyle', r'weed', r'soccer', r'gaming', r'hair', r'family', r'pictures',
                    r'psychology', r'cosplay', r'theatre', r'\blaw\b', r'pizza',
                ],
                'weight': [
                    r'\b(?:c|g|s|h|l)w[1-3]?\b', r'\blbs?\b', r'\bkgs?\b', r'pounds', r'kilograms',
                    r'weight', r'\bfat\b', r'\bthin\b', r'\bana\b', r'anorexic', r'anorexia', r'bulimia', r'eating disorders?',
                ],
        }
        terms['sexuality/gender'] = terms['gender'] + terms['sexual orientation'] + terms['pronouns']

        with open(self.terms_path, 'wb') as f:
            pickle.dump(terms, f)

        excl_terms = {
            'age': ['nsfw 18', '18 nsfw', '18 only', 'only 18', '18\+', '18 \+', '18 or older', 'at least 18', 'under 18', '18×', '18 plus',
                '24 hours',
                r'(\d{1,2}|\d{4})[\/\.-](\d|[0-3][0-9])[\/\.-](\d{2}|\d{4})(\W|$)',
                r'(^|\D)\d{1,2}[\/\.-](\d{2}|\d{4})(\W|$)',
                r'\d* ?(jan\w*|feb\w*|mar\w*|apr\w*|may|jun|june|jul|july|aug\w*|sep\w*|oct\w*|nov\w*|dec\w*)[ ,.]\d*[ \W,.]*\d*',
                r'\d+[:.]',
                r'u?(c|g|s)w[1-3]?: ?\d*(kg|lb)?',
                r'\d* ?(kg|lb|kilograms|pounds|days?)',
                r'24[\/\* -]7',
                r'\$\d*|\d*\$',
                r'\d*(st|nd|rd|th)',
                '30 rock',
                '15 lat',
                'dragon age',
                r'of age',
                r'golden age',
                ],
            'gender': [
                'transylvania',
                'protect trans',
                'trans rights',
                'transgressions?',
                'transatlantic',
                'oitnb',
                'stanbul',
                'big brother',
                r'iron man',
                r'ironman',
                r"mommy's",
                ],
            'sexual orientation': [
                'ace maverick',
                r'straight into',
                r'straight from',
                r'straight out',
                r'straight outta',
                r'peter pan',
                ],
            'pronouns': [
                r'they live',
                r'they gathered',
                r'they stab',
                r'see them',
                r'for them',
                r"they'll",
                r'they will',
                r"they're",
                r'they are',
                r'they will',
                r"they don't",
                r'he managed',
                r's?he is',
                r'know them',
                r'chasing them',
                r'designing them',
                r"they won't",
                r'they never',
                r'let them',
                r'see him',
                r'love him',
                ],
            'ethnicity/nationality': [
                r'mission',
                'sioux falls',
                r'french it-girl',
                'black lives matter',
                'blacklivesmatter',
                r'black cat',
                r'black panther',
                'black socks',
                'karen',
                'upper',
                'white lies',
                'snow white',
                r'great white',
                'damara',
                r'creek',
                'wearing black',
                'black clothes',
                "it's black",
                'my english',
                '(english|spanish|french|german|italian) (professor|teacher|literature|major)',
                'study (english|spanish|french|german|italian)',
                'greek mythology',
                r'colou?red',
                ],
            'relationship status': [
                'single verse',
                'single-verse',
                'single song',
                'single ship',
                'single-ship',
                'single candle',
                'taken over',
                'taken part',
                'taken from',
                'taken on',
                'taken with',
                ],
            'fandoms': [
                r'reverse',
                r"i'm yuri",
                r"i am yuri",
                'audrey',
                'areyou',
                r'fantastic',
                r'us army',
                r'army vet',
                ],
            'location': [
                r'al-',
                r'tabarak wa',
                r'-san',
                ],
            'personality type': [
                r'bestpaper',
                ],
            'weight': [
                r"cw's",
                r'burn fat',
                r'pounds of stubborn body fat',
                ],
            'interests': [
                r'signature',
                ],
        }

        with open(self.excl_terms_path, 'wb') as f:
            pickle.dump(excl_terms, f)

        # Combine terms in regex
        terms_re = {}
        for cat in terms:
            terms_re[cat] = re.compile(r'|'.join(terms[cat]), re.IGNORECASE)

        return terms, excl_terms, terms_re

    def _has_category(self, cat, desc):
        """ Annotates a description for an identity category.
            Returns:
                (list of term matches, boolean whether category is present)
            """
        
        if isinstance(desc, list):
            desc = ' '.join(desc)
        elif not isinstance(desc, str):
            desc = str(desc)

        # First filter out excluded patterns
        if cat in self.excl_terms:
            for p in self.excl_terms[cat]:
                desc = re.sub(re.compile(p, re.IGNORECASE), ' ', desc)
            
        # Find pattern matches
        matches = [m for m in re.finditer(self.terms_re[cat], desc)]
        if len(matches) > 0:
            match_text = []
            for m in matches:
                if any(m.groups()):
                    gp_idx = np.nonzero(m.groups())[0][0] + 1
                    match_text.append(m.group(gp_idx).strip())
                else:
                    match_text.append(m.group().strip())
            matches = match_text

        presence = len(matches) > 0

        return matches, presence

    def annotate(self, descs, desc_colname):
        # Annotate for identity categories
        for i,cat in enumerate(sorted(self.terms)):
            print(f'{cat} ({i}/{len(self.terms)})')
            descs[f'{cat}_terms'], descs[cat] = list(zip(*list(map(lambda desc: self._has_category(cat, desc), tqdm(descs[desc_colname])))))
            descs[cat]

        return descs


def main():

    # I/O files
    data_dirpath = '/usr2/mamille2/tumblr/data'
    descs_path = os.path.join(data_dirpath, 'blog_descriptions_recent100_100posts.pkl')
    outpath = os.path.join(data_dirpath, 'blog_descriptions_recent100_100posts.pkl')

    # Settings
    desc_colname = 'parsed_blog_description'

    print("Loading blog descriptions...", end=' ')
    sys.stdout.flush()
    descs = pd.read_pickle(descs_path)
    print('done.')
    sys.stdout.flush()

    print("Annotating identity categories...")
    sys.stdout.flush()
    ia = IdentityAnnotator(data_dirpath)
    descs_annotated = ia.annotate(descs, desc_colname)
    print('done.')
    sys.stdout.flush()

    descs_annotated.to_pickle(outpath)
    print("Saved annotated data to {}".format(outpath))
    sys.stdout.flush()

if __name__=='__main__': main()
