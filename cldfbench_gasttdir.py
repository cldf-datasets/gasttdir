import pathlib
import re
import unicodedata

from cldfbench import CLDFSpec, Dataset as BaseDataset


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

    analysed_word = [
        word for word in example['original'].split('\t')]
    glosses = [
        word for word in example['gloss'].split('\t')]

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

        langid_by_name = {
            row['Original_Name'].lower(): row['ID']
            for row in language_table}
        example_table = [
            make_example_row(langid_by_name, example)
            for example in example_table
            if example['language'] != 'xxx']

        value_table = [
            {
                'ID': '{}-{}'.format(value['sil'], param['ID']),
                'Language_ID': value['sil'],
                'Parameter_ID': param['ID'],
                'Value': value[param['ID']].strip(),
            }
            for value in original_values
            for param in parameter_table
            if value.get(param['ID'], '').strip()]

        args.writer.cldf.add_component('LanguageTable')
        args.writer.cldf.add_component('ParameterTable')
        args.writer.cldf.add_component(
            'ExampleTable',
            'POV',
            'Citation')

        args.writer.objects['LanguageTable'] = language_table
        args.writer.objects['ParameterTable'] = parameter_table
        args.writer.objects['ValueTable'] = value_table
        args.writer.objects['ExampleTable'] = example_table
