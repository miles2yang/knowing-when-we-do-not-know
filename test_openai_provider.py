import os
from unittest.mock import patch
import unittest
from openai_provider import configuration,extract_text,call

class ProviderTests(unittest.TestCase):
    def test_configuration_only_reports_missing_names(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'private-value'},clear=True):
            s=configuration();self.assertFalse(s['ready']);self.assertNotIn('private-value',str(s))
    def test_mixed_output_items_are_extracted(self):
        r={'output':[{'type':'reasoning'},{'type':'message','content':[{'type':'output_text','text':'a'},{'type':'refusal','refusal':'no'}]},{'type':'message','content':[{'type':'output_text','text':'b'}]}]}
        self.assertEqual(extract_text(r),'ab')
    def test_missing_configuration_cannot_call_network(self):
        with patch.dict(os.environ,{},clear=True),patch('urllib.request.urlopen') as urlopen:
            with self.assertRaises(RuntimeError):call({})
            urlopen.assert_not_called()

if __name__=='__main__':unittest.main()
