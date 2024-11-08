from django import forms


class LoadDataForm(forms.Form):
    url = forms.URLField(label='URL для загрузки данных', required=True)
