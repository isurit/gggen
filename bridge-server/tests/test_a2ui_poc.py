import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import a2ui_poc as poc


class DeviceScreenTests(unittest.TestCase):
    def test_data_is_bound_and_component_references_exist(self):
        devices = [{'name': '거실 센서', 'kind': 'ZIGBEE', 'room': '', 'status': ''}]
        layout = {'title': '기기', 'direction': 'vertical',
                  'item': {'type': 'Card', 'children': [
                      {'type': 'Column', 'children': [
                          {'type': 'Text', 'field': 'name'},
                          {'type': 'Text', 'field': 'kind'}]}]}}
        messages = poc.messages_for(devices, layout, 'device-test')
        nodes = messages[2]['updateComponents']['components']
        identifiers = {node['id'] for node in nodes}
        for node in nodes:
            self.assertTrue(set(node.get('children', [])) <= identifiers)
            if 'child' in node:
                self.assertIn(node['child'], identifiers)
        self.assertEqual(messages[1]['updateDataModel']['value']['devices'], devices)
        self.assertIn({'path': '/devices/0/name'}, [node.get('text') for node in nodes])

    def test_card_background_applies_only_to_matching_device_type(self):
        devices = [{'name': 'Phone', 'kind': 'Phone display type', 'type': 'MOBILE'}, {'name': 'Hub', 'kind': 'HUB', 'type': 'HUB'}]
        layout = {'title': 'Devices', 'direction': 'vertical', 'item': {
            'type': 'Card', 'backgroundWhen': {'field': 'type', 'equals': 'MOBILE', 'color': '#1565C0'},
            'children': [{'type': 'Text', 'field': 'name'}]}}
        poc.validate_layout(layout['item'])
        messages = poc.messages_for(devices, layout, 'test')
        nodes = messages[2]['updateComponents']['components']
        colored = [node for node in nodes if node['component'] == 'ColoredCard']
        normal = [node for node in nodes if node['component'] == 'Card']
        self.assertEqual(len(colored), 1)
        self.assertEqual(len(normal), 1)
        self.assertEqual(colored[0]['backgroundColor'], '#1565C0')
        self.assertEqual(messages[0]['createSurface']['catalogId'], poc.CUSTOM_CATALOG)

    def test_figma_mode_uses_imported_layout_without_model_call(self):
        with patch.object(poc, 'generate_layout') as generate:
            layout, cached = poc.layout_for({'sourceMode': 'figma'})
        self.assertTrue(cached)
        self.assertEqual(layout['item']['backgroundColor'], '#FFFFFF')
        self.assertEqual(layout['item']['backgroundWhen']['field'], 'type')
        generate.assert_not_called()

    def test_empty_account_has_visible_empty_state(self):
        messages = poc.messages_for([], {'title': '기기', 'direction': 'vertical',
                                        'item': {'type': 'Text', 'field': 'name'}}, 'empty-test')
        nodes = messages[2]['updateComponents']['components']
        self.assertEqual(nodes[2]['children'], ['empty'])

    def test_unknown_fields_and_oversized_or_invalid_trees_are_rejected(self):
        for node in [{'type': 'Text', 'field': 'pat'},
                     {'type': 'Text', 'field': 'name', 'url': 'untrusted'},
                     {'type': 'Card', 'children': []},
                     {'type': 'WebView', 'children': []}]:
            with self.subTest(node=node), self.assertRaises(poc.PocError):
                poc.validate_layout(node)

    def test_pagination_never_forwards_pat_to_another_host(self):
        with patch.object(poc, 'remote_json', return_value={
            'items': [], '_links': {'next': {'href': 'https://other.invalid/v1/devices'}}}):
            with self.assertRaises(poc.PocError):
                poc.load_devices({'pat': 'test-secret'})

    def test_missing_pat_does_not_call_model(self):
        with patch.object(poc, 'configuration', return_value={'pat': ''}), patch.object(poc, 'generate_layout') as generate:
            with self.assertRaises(poc.PocError):
                poc.device_screen()
            generate.assert_not_called()

    def test_settings_hide_pat_and_concurrent_edits_do_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(poc, 'CONFIG_PATH', Path(directory) / 'settings.json'):
            config = poc.configuration()
            public = poc.update_configuration({'revision': config['revision'], 'prompt': '카드', 'pat': 'private-test-token'})
            self.assertTrue(public['hasPat'])
            self.assertNotIn('private-test-token', json.dumps(public))
            with self.assertRaises(poc.PocError) as error:
                poc.update_configuration({'revision': config['revision'], 'prompt': '리스트'})
            self.assertEqual(error.exception.status, 409)
            self.assertEqual(poc.configuration()['prompt'], '카드')


if __name__ == '__main__':
    unittest.main()
