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

    def test_complex_figma_keeps_literal_text_styles_and_row_layout(self):
        layout, _ = poc.layout_for({'sourceMode': 'figma', 'figmaSampleId': '2'})
        messages = poc.messages_for([{'name': 'Phone', 'kind': 'Mobile phone', 'type': 'MOBILE'}], layout, 'complex')
        nodes = messages[2]['updateComponents']['components']
        self.assertTrue(any(n.get('justify') == 'stretch' for n in nodes))
        self.assertTrue(any(n.get('text') == '읽기 전용' for n in nodes))
        self.assertTrue(any(n.get('variant') == 'h3' and isinstance(n.get('text'), dict) for n in nodes))
        self.assertGreater(len(nodes), 15)
        self.assertEqual(messages[0]['createSurface']['catalogId'], poc.CUSTOM_CATALOG)

    def test_figma_selection_rejects_unknown_ids(self):
        with self.assertRaises(poc.PocError):
            poc.figma_sample('../settings')

    def test_air_care_selection_returns_two_pages_without_smartthings(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            poc, 'CONFIG_PATH', Path(directory) / 'settings.json'
        ), patch.object(poc, 'load_devices') as load_devices:
            config = poc.configuration()
            poc.select_figma_design({'revision': config['revision'], 'figmaSampleId': '3'})
            response = poc.device_screen()

        load_devices.assert_not_called()
        self.assertEqual(response['meta']['dataSource'], 'sample')
        create, data, update = response['messages']
        self.assertEqual(create['createSurface']['catalogId'], poc.CUSTOM_CATALOG)
        pages = data['updateDataModel']['value']['pages']
        self.assertEqual([[room['name'] for room in page] for page in pages],
                         [['야외', '거실', '우리방'], ['준우방', '침실']])
        nodes = {node['id']: node for node in update['updateComponents']['components']}
        root = nodes['root']
        self.assertEqual(root['component'], 'AirCarePager')
        self.assertEqual([len(nodes[root[key]]['children']) for key in ('firstPage', 'secondPage')],
                         [3, 2])

    def test_design_selection_preserves_prompt_and_credentials(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(poc, 'CONFIG_PATH', Path(directory) / 'settings.json'):
            config = poc.configuration()
            config.update(prompt='Existing UX', pat='private-pat', modelKey='private-model-key')
            poc.save_file(config)
            state = poc.select_figma_design({'revision': config['revision'], 'figmaSampleId': '2', 'pat': 'unwanted-overwrite'})
            stored = poc.configuration()
            self.assertEqual(stored['prompt'], 'Existing UX')
            self.assertEqual(stored['pat'], 'private-pat')
            self.assertEqual(stored['modelKey'], 'private-model-key')
            self.assertEqual(stored['sourceMode'], 'figma')
            self.assertEqual(stored['figmaSampleId'], '2')
            self.assertNotIn('appKey', state)
            self.assertNotIn('private', json.dumps(state))
            same = poc.select_figma_design({'revision': state['revision'], 'figmaSampleId': '2'})
            self.assertEqual(same['revision'], state['revision'])
            with self.assertRaises(poc.PocError) as error:
                poc.select_figma_design({'revision': config['revision'], 'figmaSampleId': '1'})
            self.assertEqual(error.exception.status, 409)
            self.assertEqual(poc.configuration()['figmaSampleId'], '2')

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
