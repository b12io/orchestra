from django import forms


class ImportTodoListTemplateFromSpreadsheetForm(forms.Form):
    spreadsheet_url = forms.URLField(
        label='Spreadsheet URL')
