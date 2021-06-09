"""
Processor for names that are imported into the database based on the
ICU library.
"""
import json
import itertools

from icu import Transliterator
import datrie

from nominatim.db.properties import set_property, get_property

DBCFG_IMPORT_NORM_RULES = "tokenizer_import_normalisation"
DBCFG_IMPORT_TRANS_RULES = "tokenizer_import_transliteration"
DBCFG_IMPORT_REPLACEMENTS = "tokenizer_import_replacements"
DBCFG_SEARCH_STD_RULES = "tokenizer_search_standardization"


class ICUNameProcessorRules:
    """ Data object that saves the rules needed for the name processor.

        The rules can either be initialised through an ICURuleLoader or
        be loaded from a database when a connection is given.
    """
    def __init__(self, loader=None, conn=None):
        if loader is not None:
            self.norm_rules = loader.get_normalization_rules()
            self.trans_rules = loader.get_transliteration_rules()
            self.replacements = loader.get_replacement_pairs()
            self.search_rules = loader.get_search_rules()
        elif conn is not None:
            self.norm_rules = get_property(conn, DBCFG_IMPORT_NORM_RULES)
            self.trans_rules = get_property(conn, DBCFG_IMPORT_TRANS_RULES)
            self.replacements = json.loads(get_property(conn, DBCFG_IMPORT_REPLACEMENTS))
            self.search_rules = get_property(conn, DBCFG_SEARCH_STD_RULES)
        else:
            assert False, "Parameter loader or conn required."

        # Compute the set of characters used in the replacement list.
        # We need this later when computing the tree.
        chars = set()
        for full, repl in self.replacements:
            chars.update(full)
            for word in repl:
                chars.update(word)
        self.replacement_charset = ''.join(chars)


    def save_rules(self, conn):
        """ Save the rules in the property table of the given database.
            the rules can be loaded again by handing in a connection into
            the constructor of the class.
        """
        set_property(conn, DBCFG_IMPORT_NORM_RULES, self.norm_rules)
        set_property(conn, DBCFG_IMPORT_TRANS_RULES, self.trans_rules)
        set_property(conn, DBCFG_IMPORT_REPLACEMENTS, json.dumps(self.replacements))
        set_property(conn, DBCFG_SEARCH_STD_RULES, self.search_rules)


class ICUNameProcessor:
    """ Collects the different transformation rules for normalisation of names
        and provides the functions to aply the transformations.
    """

    def __init__(self, rules):
        self.normalizer = Transliterator.createFromRules("icu_normalization",
                                                         rules.norm_rules)
        self.to_ascii = Transliterator.createFromRules("icu_to_ascii",
                                                       rules.trans_rules)
        self.search = Transliterator.createFromRules("icu_search",
                                                     rules.search_rules)

        self.replacements = datrie.Trie(rules.replacement_charset)
        for full, repl in rules.replacements:
            self.replacements[full] = repl


    def get_normalized(self, name):
        """ Normalize the given name, i.e. remove all elements not relevant
            for search.
        """
        return self.normalizer.transliterate(name).strip()

    def get_variants_ascii(self, norm_name):
        """ Compute the spelling variants for the given normalized name
            and transliterate the result.
        """
        baseform = ' ' + norm_name + ' '
        variants = ['']

        startpos = 0
        pos = 0
        while pos < len(baseform):
            full, repl = self.replacements.longest_prefix_item(baseform[pos:],
                                                               (None, None))
            if full is not None:
                done = baseform[startpos:pos]
                variants = [v + done + r for v, r in itertools.product(variants, repl)]
                startpos = pos + len(full)
                pos = startpos
            else:
                pos += 1

        if startpos == 0:
            return [self.to_ascii.transliterate(norm_name)]

        return [self.to_ascii.transliterate(v + baseform[startpos:pos]).strip() for v in variants]


    def get_search_normalized(self, name):
        """ Return the normalized version of the name (including transliteration)
            to be applied at search time.
        """
        return self.search.transliterate(' ' + name + ' ').strip()
