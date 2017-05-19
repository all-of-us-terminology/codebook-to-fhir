import click
import csv
import datetime
import json
import os
import subprocess
import sys

from collections import namedtuple

SHEET_URL = 'https://docs.google.com/spreadsheets/d/%(sid)s/export?format=csv&gid=%(gid)s'
OUTPUT_FILE = 'dist/CodeSystem/'

Coding = namedtuple('Coding', ['system', 'code'])

class CodebookEntry(object):
    issues = []

    def __init__(self, term):
        for k in term:
            term[k] = term[k].strip()
            if not term[k]: term[k] = None
        self._dict = term
        self.make_valid(term)

    def make_valid(self, term):
        if not term['PMI Code']:
            self.issues.append("PMI Code is not defined in: %s"%term)
        if "'" in (term['PMI Code'] or ""):
            self.issues.append("Invalid character in code '%s'"%term['PMI Code'])
        if term['Parent code'] and ' ' in term['Parent code']:
            self.issues.append("unexpected space in parent code '%s' of code '%s'"%(term['Parent code'], term['PMI Code']))
            term['Parent code'] = term['Parent code'].replace(" ", "")
        if term['PMI Code'] and ' ' in term['PMI Code']:
            self.issues.append("unexpected space in code  '%s'"%term['PMI Code'])
            term['PMI Code'] = term['PMI Code'].replace(" ", "")
        if 'Type' not in term:
            self.issues.append("No type is defined for code '%s'"%term['PMI Code'])
            term['Type'] = 'Unknown'
        if 'Topic' not in term and not self.coding.code.startswith("PMI"):
            self.issues.append("No topic is defined for '%s'"%term['PMI Code'])
            term['Topic'] = 'Unknown'

    @property
    def concept_type(self):
        return self._dict['Type']

    @property
    def answer_type(self):
        return self._dict.get('Answer Type', '')

    @property
    def concept_topic(self):
        return self._dict['Topic']

    @property
    def display(self):
        return self._dict['Display']

    @property
    def coding(self):
        return Coding(self._dict['PMI System'], self._dict["PMI Code"])

    @property
    def parent_coding(self):
        return Coding(self._dict['PMI System'], self._dict["Parent code"])

def strip_empty_concepts(concept):
    if concept['concept'] == None:
        concept.pop('concept')
    return concept

class SheetProcessor(object):
    def __init__(self, config):
        self.config = config
        self.download_sheets()
        self.process_sheets()
        with open('./dist/version', 'w') as outfile:
            outfile.write(self.version + '\n')
        print "# terms:", len(self.terms_by_coding)
        print "# issues:", len(CodebookEntry.issues)
        print "Top-level concepts", "\n  ".join([str(t.coding) for t in self.terms_by_parent[Coding(self.config['system'],None)]])
        self.output_fhir()

    @property
    def output_file(self):
        return OUTPUT_FILE+self.config['id']

    def ancestor_terms(self, term):
        if not term.coding.code:
            return [term]

        parent_term = self.terms_by_coding.get(term.parent_coding, None)
        if term.coding.code and parent_term and parent_term != term:
            return self.ancestor_terms(parent_term) + [term]
        else:
            return [term]

    def is_ancestor_exception(self, term):
        return term.coding.code and term.coding.code.startswith("PMI_")

    def download_sheets(self):
        for name, gid in list(self.config['sheets'].iteritems()) + [("version", self.config['versionSheet'])]:
            target = SHEET_URL%{"sid": self.config['sheetId'], "gid": gid}
            subprocess.call(["mkdir", "-p", "dist/sheets"])
            subprocess.call(["mkdir", "-p", "dist/CodeSystem"])
            subprocess.call(["wget", target, "-O", "dist/sheets/%s.csv"%name])

    def process_sheets(self):
        with open("dist/sheets/version.csv", "rb") as csvfile:
            reader = csv.DictReader(csvfile)
            row = list(reader)[0]
            self.version = row['Current Codebook Version']
            self.changeDate = row['Date of Version Update']

        CodebookEntry.issues = []
        terms = []
        for name in self.config['sheets']:
            with open("dist/sheets/%s.csv"%name, "rb") as csvfile:
                rownum = 0
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if "".join(row.values()):
                        terms += [row]
                        terms[-1]['source'] = name
                        terms[-1]['row'] = str(rownum)
                        rownum += 1

        self.terms_by_coding = {}
        self.terms_by_parent = {}

        for term in terms:
            assert 'Parent code' in term
            assert 'PMI Code' in term
            entry = CodebookEntry(term)
            if entry.coding in self.terms_by_coding:
                CodebookEntry.issues.append("Redefined! %s : %s"%entry.coding)
            if not term['PMI Code']:
                CodebookEntry.issues.append("Missing code for: %s"%entry._dict)
            else:
                self.terms_by_coding[entry.coding] = entry

        for term in self.terms_by_coding.values():
            """ # this isn't specific enough to produce helpful output right now
            if term.concept_type == 'Question'and '?' not in term.display:
                    CodebookEntry.issues.append("Term '%s' is a question but does not include '?' (%s)"%
                            (term._dict['PMI Code'], term.display))
                            """
            if not term.display:
                CodebookEntry.issues.append("Term '%s' has display value"%term._dict['PMI Code'])
                print("no display for", term._dict)
            if term.concept_type != 'Question'and term.display and '?' in term.display:
                    CodebookEntry.issues.append("Term '%s' has type '%s' but includes a '?' (%s)"%
                            (term._dict['PMI Code'], term.concept_type, term.display))
            if term.concept_type == 'Answer' and term.parent_coding and term.parent_coding in self.terms_by_coding:
                ancestor_terms =  self.ancestor_terms(term)
                if 'Question' not in [t.concept_type for t in ancestor_terms] and not self.is_ancestor_exception(term):
                    CodebookEntry.issues.append("Ancestors of '%s' don't include a 'Question', but this term is an 'Answer' %s"%
                            (term._dict['PMI Code'],
                                ["%s: %s"%(t.coding.code, t.concept_type) for t in ancestor_terms]))
            if term.parent_coding and term.parent_coding not in self.terms_by_coding:
                if term.coding.code not in self.config['sheets']:
                    CodebookEntry.issues.append("Parent of '%s' is '%s' but does not exist"%(
                            term._dict['PMI Code'], term._dict['Parent code']))

                term._dict['Parent code'] = None
            if term.parent_coding not in self.terms_by_parent:
                self.terms_by_parent[term.parent_coding] = []
            if term.parent_coding == term.coding:
                CodebookEntry.issues.append("Parent of '%s' is '%s'"%(
                        term._dict['PMI Code'], term._dict['Parent code']))
            else:
                self.terms_by_parent[term.parent_coding].append(term)

        for term in self.terms_by_coding.values():
            ancestor_terms = self.ancestor_terms(term)
            answer_types = [t.answer_type for t in ancestor_terms if t.answer_type]
            is_choice_type = (set(['open-choice', 'choice']) & set(answer_types))
            if term.concept_type == "Question" and is_choice_type and term.coding not in self.terms_by_parent:
                CodebookEntry.issues.append("Term '%s' has type=Question which is a choice type, but no answers associated with it. Hierarchy: %s"%(
                    term._dict['PMI Code'], ["%s: %s"%(t.coding.code, t.answer_type) for t in ancestor_terms]))
            parent_term = self.terms_by_coding.get(term.parent_coding, None)
            if parent_term == term:
                CodebookEntry.issues.append("Term has itself as a parent: of '%s'"%
                        term._dict['PMI Code'])


    def concepts_with_parent(self, parent=None):
        return [strip_empty_concepts({
                'code': t.coding.code,
                'display': t.display,
                'property': [{
                    'code': 'concept-type',
                    'valueCode': t.concept_type
                },{
                    'code': 'concept-topic',
                    'valueCode': t.concept_topic
                }],
                'concept': self.concepts_with_parent(t.coding.code) or None
            }) for t in self.terms_by_parent.get(Coding(self.config['system'], parent), [])]

    def make_pmi_codesystem(self):
        return {
        'resourceType': 'CodeSystem',
        'url': self.config['system'],
        'version': self.version,
        'name': 'pmi-codebook',
        'title': "Codebook for PMI's All of Us Research Program Participant-Provided Information",
        'status': 'draft',
        'date': self.changeDate,
        'publisher': self.config['publisher'],
        'description': """
    # PMI Codebook
    This `CodeSystem` defines the concepts used in PPI modules.
    TODO: add detail here...
        """.strip(),
        'caseSensitive': True,
        'hierarchyMeaning': 'grouped-by',
        'compositional': False,
        'content': 'complete',
        'count': len(self.terms_by_coding),
        'property': [{
            'code': 'concept-type',
            'description': 'indicates whether this PPI concept is a Topic, Question, or Answer',
            'type': 'string'
        },{
            'code': 'concept-topic',
            'description': 'indicates the topic for this PPI concept',
            'type': 'string'
        }],
        'concept': self.concepts_with_parent()
    }

    def make_include_for(self, codebook_terms):
        assert len(set([t.coding.system for t in codebook_terms])) == 1
        return {
            'system': codebook_terms[0].coding.system,
            'concept': [{
                'code': t.coding.code,
                'display': t.display
            } for t in codebook_terms]
        }

    def make_pmi_valueset(self, question_entry):
        return {
            'resourceType': 'ValueSet',
            'url': self.config['valueSetBase']%question_entry.coding.code,
            'version': self.version,
            'name': 'values-for-%s'%question_entry.coding.code,
            'title': 'Values for %s'%question_entry.display,
            'status': 'draft',
            'date': self.changeDate,
            'publisher': self.config['publisher'],
            'compose': {
                'include': [
                    self.make_include_for(self.terms_by_parent[question_entry.coding]),
                    self.make_include_for(self.terms_by_parent[Coding(self.config['system'], "PMI")]),
                ]
            }
        }

    def output_fhir(self):
        with open(self.output_file+".json", "wb") as json_file:
            json.dump(self.make_pmi_codesystem(), json_file, indent=2)

        with open(self.output_file+".issues.json", "wb") as json_file:
            json.dump(CodebookEntry.issues, json_file, indent=2)

        valuesets = [
            self.make_pmi_valueset(term)
            for coding, term in self.terms_by_coding.iteritems()
            if term.concept_type == "Question" and term.coding in self.terms_by_parent
        ]

        bundle = {
            'resourceType': "Bundle",
            'entry': [{
                    'resource': r
                } for r in [self.make_pmi_codesystem()] + valuesets]
        }

        with open(self.output_file+".bundle.json", "wb") as json_file:
            json.dump(bundle, json_file, indent=2)

@click.command()
@click.option('--config', default='config/ppi-codebook.json', help='Path to config file')
def run(config):
    config = json.load(open(config, 'r'))
    SheetProcessor(config)

if __name__ == '__main__':
    run()
