from django.test import TestCase
from backend.forms import LoadDataForm


class LoadDataFormTests(TestCase):
    def test_form_with_valid_url(self):
        """
        Тест на успешную валидацию формы при корректном URL.
        """
        form_data = {'url': 'https://example.com/data.yaml'}
        form = LoadDataForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_with_invalid_url(self):
        """
        Тест на неуспешную валидацию формы при некорректном URL.
        """
        form_data = {'url': 'not-a-valid-url'}
        form = LoadDataForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('url', form.errors)
        self.assertEqual(form.errors['url'][0], 'Enter a valid URL.')

    def test_form_with_empty_url(self):
        """
        Тест на неуспешную валидацию формы при пустом поле URL.
        """
        form_data = {'url': ''}
        form = LoadDataForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('url', form.errors)
        self.assertEqual(form.errors['url'][0], 'This field is required.')
