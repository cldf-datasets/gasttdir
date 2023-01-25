import pathlib
import re
import unicodedata

from cldfbench import CLDFSpec, Dataset as BaseDataset


def html_cleanup(cell):
    cell = cell.strip()
    # TODO reenable html removal
    #cell = re.sub('<[^<>]*>', '', cell)
    #cell = cell.replace('&lt;', '<')
    #cell = cell.replace('&gt;', '>')
    cell = re.sub('&nbsp;?', ' ', cell)
    # some remnant of a non-utf encoding???
    cell = re.sub('&#146;?', '’', cell)
    cell = cell.replace('&auml;', 'ä')
    cell = re.sub(r'&#(\d+);?', lambda m: chr(int(m.group(1))), cell)
    # why not..
    cell = unicodedata.normalize('NFC', cell)
    return cell


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "gasttdir"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return CLDFSpec(dir=self.cldf_dir, module="StructureDataset")

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

        value_table = [
            {
                'ID': '{}-{}'.format(value['sil'], param['ID']),
                'Language_ID': value['sil'],
                'Value': value[param['ID']].strip(),
            }
            for value in original_values
            for param in parameter_table
            if value.get(param['ID'], '').strip()]

        args.writer.cldf.add_component('LanguageTable')
        args.writer.cldf.add_component('ParameterTable')

        args.writer.objects['LanguageTable'] = language_table
        args.writer.objects['ParameterTable'] = parameter_table
        args.writer.objects['ValueTable'] = value_table
