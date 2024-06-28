import pathlib
import re
import sys
import unicodedata
from itertools import zip_longest

from cldfbench import CLDFSpec, Dataset as BaseDataset
from pybtex.database import parse_string


def td_to_tab(cell):
    cell = cell.replace('\t', '\\t')
    cell = cell.replace('</td><td>', '\t')
    return cell


def html_cleanup(cell):
    cell = cell.strip()
    # TODO reenable html removal
    #cell = re.sub('<[^<>]*>', '', cell)
    #cell = cell.replace('&lt;', '<')
    #cell = cell.replace('&gt;', '>')
    cell = re.sub('&nbsp;?', ' ', cell)
    # some remnant of a non-utf encoding???
    cell = re.sub('&#146;?', '’', cell)
    cell = cell.replace('&Aring;', 'Å')
    cell = cell.replace('&auml;', 'ä')
    cell = cell.replace('&ccedil;', 'ç')
    cell = cell.replace('&ouml;', 'ö')
    cell = cell.replace('&uuml;', 'ö')
    cell = re.sub(r'&#(\d+);?', lambda m: chr(int(m.group(1))), cell)
    # why not..
    cell = unicodedata.normalize('NFC', cell)
    return cell


def make_example_row(langid_by_name, example):
    language_name = example['language'].lower()
    language_name = language_name.replace('nahuatlx', 'nahuatl')
    language_name = language_name.replace('zapo´tec', 'zapotec')
    language_name = language_name.replace('sewdish', 'swedish')

    analysed_word = example['original'].split('\t')
    glosses = example['gloss'].split('\t')

    if example['comments'] != '--':
        comment = example['comments']
    else:
        comment = ''

    return {
        'ID': example['Nr'],
        'Language_ID': langid_by_name[language_name],
        'Primary_Text': ' '.join(analysed_word),
        'Analyzed_Word': analysed_word,
        'Gloss': glosses,
        'Translated_Text': example['translation'],
        'Comment': comment,
        'POV': example['pov'],
        # TODO do sources properly
        'Citation': example['source'],
    }


def render_example(example):
    words = example['Analyzed_Word']
    glosses = example['Gloss']
    id_width = len(example['ID'])
    widths = [max(len(w), len(g)) for w, g in zip(words, glosses)]
    padded_words = [
        word.ljust(width)
        for word, width in zip_longest(words, widths, fillvalue=0)]
    padded_glosses = [
        gloss.ljust(width)
        for gloss, width in zip_longest(glosses, widths, fillvalue=0)]
    return '({})  {}\n{}    {}'.format(
        example['ID'],
        '  '.join(padded_words).rstrip(),
        ' ' * id_width,
        '  '.join(padded_glosses).rstrip())


def warn_about_glosses(example_table):
    mismatched_examples = [
        example
        for example in example_table
        if len(example['Analyzed_Word']) != len(example['Gloss'])]
    if mismatched_examples:
        print("ERROR: Misaligned glosses in examples:", file=sys.stderr)
        for example in mismatched_examples:
            print(file=sys.stderr)
            print(render_example(example), file=sys.stderr)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "gasttdir"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return CLDFSpec(
            dir=self.cldf_dir,
            module="StructureDataset",
            metadata_fname='cldf-metadata.json')

    def cmd_download(self, args):
        """
        Download files to the raw/ directory. You can use helpers methods of `self.raw_dir`, e.g.

        >>> self.raw_dir.download(url, fname)
        """
        # # note to self: both openpyxl and xlrd failed to read the spreadsheets
        # # because the files actually just contain an html table (based on
        # # some schema defined by ms?) instead of whatever these libraries
        # # actually expect an Excel sheet to contain…
        # # So, I just ended up converting the files manually in libreoffice…
        # self.raw_dir.xls2csv('tdir.examples.xls')
        # self.raw_dir.xls2csv('tdir.glosses.xls')
        # self.raw_dir.xls2csv('tdir.languages.xls')
        # self.raw_dir.xls2csv('tdir.references.xls')

    def cmd_makecldf(self, args):
        """
        Convert the raw data to a CLDF dataset.

        >>> args.writer.objects['LanguageTable'].append(...)
        """
        original_values = self.raw_dir.read_csv('tdir.languages.csv', dicts=True)
        original_values = [
            {html_cleanup(col): html_cleanup(cell) for col, cell in row.items()}
            for row in original_values]

        language_table = self.etc_dir.read_csv('languages.csv', dicts=True)
        parameter_table = self.etc_dir.read_csv('parameters.csv', dicts=True)

        example_table = self.raw_dir.read_csv('tdir.examples.csv', dicts=True)
        example_table = [
            {col: html_cleanup(td_to_tab(cell)) for col, cell in row.items()}
            for row in example_table]

        sources = parse_string(
            self.raw_dir.read('tdir.references.bib'), 'bibtex')

        language_sources = {
            row['Glottocode']: [
                trimmed
                for source in row.get('Source', '').split(';')
                if (trimmed := source.strip())]
            for row in original_values}
        for lg in language_table:
            lg['Source'] = language_sources.get(lg['Glottocode']) or []

        langid_by_name = {
            row['Original_Name'].lower(): row['ID']
            for row in language_table}
        example_table = [
            make_example_row(langid_by_name, example)
            for example in example_table
            if example['language'] != 'xxx']
        warn_about_glosses(example_table)

        langid_by_glottocode = {
            row['Glottocode']: row['ID'] for row in language_table}
        value_table = [
            {
                'ID': '{}-{}'.format(
                    langid_by_glottocode[value['Glottocode']],
                    param['ID']),
                'Language_ID': langid_by_glottocode[value['Glottocode']],
                'Parameter_ID': param['ID'],
                'Value': value[param['ID']].strip(),
                'Comment': value.get(param.get('Comment_Col')) or '',
            }
            for value in original_values
            for param in parameter_table
            if value.get(param['ID'], '').strip()]

        args.writer.cldf.add_component(
            'LanguageTable',
            'http://cldf.clld.org/v1.0/terms.rdf#source')
        args.writer.cldf.add_component('ParameterTable')
        args.writer.cldf.add_component('ExampleTable', 'POV', 'Citation')

        args.writer.objects['LanguageTable'] = language_table
        args.writer.objects['ParameterTable'] = parameter_table
        args.writer.objects['ValueTable'] = value_table
        args.writer.objects['ExampleTable'] = example_table

        args.writer.cldf.add_sources(sources)
