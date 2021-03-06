# Copyright Contributors to the Amundsen project.
# SPDX-License-Identifier: Apache-2.0

import json
import unittest
from http import HTTPStatus
from unittest import mock
from unittest.mock import MagicMock

from amundsen_common.entity.resource_type import ResourceType
from amundsen_common.models.dashboard import DashboardSummary
from amundsen_common.models.popular_table import PopularTable

from metadata_service import create_app
from metadata_service.api.user import (UserDetailAPI, UserFollowAPI,
                                       UserFollowsAPI, UserOwnAPI, UserOwnsAPI,
                                       UserReadsAPI)
from metadata_service.util import UserResourceRel


class UserDetailAPITest(unittest.TestCase):
    @mock.patch('metadata_service.api.user.get_proxy_client')
    def setUp(self, mock_get_proxy_client: MagicMock) -> None:
        self.app = create_app(config_module_class='metadata_service.config.LocalConfig')
        self.app_context = self.app.app_context()
        self.app_context.push()

        self.mock_client = mock.Mock()
        mock_get_proxy_client.return_value = self.mock_client
        self.api = UserDetailAPI()

    def test_get(self) -> None:
        self.mock_client.get_user.return_value = {}
        response = self.api.get(id='username')
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        self.mock_client.get_user.assert_called_once_with(id='username')

    def test_gets(self) -> None:
        self.mock_client.get_users.return_value = []
        response = self.api.get()
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        self.mock_client.get_users.assert_called_once()

    def test_put(self) -> None:
        m = MagicMock()
        m.data = json.dumps({'email': 'create_email@email.com'})
        with mock.patch("metadata_service.api.user.request", m):
            # Test user creation
            create_email = {'email': 'test_email'}
            self.mock_client.create_update_user.return_value = create_email, True
            test_user, test_user_created = self.api.put()
            self.assertEqual(test_user, json.dumps(create_email))
            self.assertEqual(test_user_created, HTTPStatus.CREATED)

            # Test user update
            update_email = {'email': 'update_email@email.com'}
            self.mock_client.create_update_user.return_value = update_email, False
            test_user2, test_user_updated = self.api.put()
            self.assertEqual(test_user2, json.dumps(update_email))
            self.assertEqual(test_user_updated, HTTPStatus.OK)

    def test_put_no_inputs(self) -> None:
        # Test no data provided
        m2 = MagicMock()
        m2.data = {}
        with mock.patch("metadata_service.api.user.request", m2):
            _, status_code = self.api.put()
            self.assertEquals(status_code, HTTPStatus.BAD_REQUEST)


class UserFollowsAPITest(unittest.TestCase):

    @mock.patch('metadata_service.api.user.get_proxy_client')
    def setUp(self, mock_get_proxy_client: MagicMock) -> None:
        self.mock_client = mock.Mock()
        mock_get_proxy_client.return_value = self.mock_client
        self.api = UserFollowsAPI()

    def test_get(self) -> None:
        self.mock_client.get_table_by_user_relation.return_value = {'table': [
            PopularTable(database='d1', cluster='c1', schema='s1bbc', name='n1_test_a_table'),
            PopularTable(database='d1', cluster='c2', schema='s1abc', name='n1_test_b_table'),
            PopularTable(database='d1', cluster='c3', schema='s1abc', name='n1_test_a_table'),
        ]}
        self.mock_client.get_dashboard_by_user_relation.return_value = {'dashboard': [
            DashboardSummary(uri='foobar_dashboard_3',
                             cluster='cluster',
                             group_name='dashboard_group_b',
                             group_url='http://foo.bar/group',
                             product='foobar',
                             name='dashboard_b',
                             url='http://foo.bar/dashboard_b'),
            DashboardSummary(uri='foobar_dashboard_2',
                             cluster='cluster',
                             group_name='dashboard_group_a',
                             group_url='http://foo.bar/group',
                             product='foobar',
                             name='dashboard_a',
                             url='http://foo.bar/dashboard_a'),
            DashboardSummary(uri='foobar_dashboard_1',
                             cluster='cluster',
                             group_name='dashboard_group_a',
                             group_url='http://foo.bar/group',
                             product='foobar',
                             name='dashboard_c',
                             url='http://foo.bar/dashboard_c'),
        ]}

        response = self.api.get(user_id='username')
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        self.mock_client.get_table_by_user_relation.assert_called_once()

        # test results are sorted
        assert list(response)[0].get('table') == [
            {'cluster': 'c3', 'database': 'd1', 'description': None, 'name': 'n1_test_a_table', 'schema': 's1abc'},
            {'cluster': 'c2', 'database': 'd1', 'description': None, 'name': 'n1_test_b_table', 'schema': 's1abc'},
            {'cluster': 'c1', 'database': 'd1', 'description': None, 'name': 'n1_test_a_table', 'schema': 's1bbc'},
        ]
        assert list(response)[0].get('dashboard') == [
            {
                'chart_names': [],
                'cluster': 'cluster',
                'description': None,
                'group_name': 'dashboard_group_a',
                'group_url': 'http://foo.bar/group',
                'last_successful_run_timestamp': None,
                'name': 'dashboard_a',
                'product': 'foobar',
                'uri': 'foobar_dashboard_2',
                'url': 'http://foo.bar/dashboard_a'
            },
            {
                'chart_names': [],
                'cluster': 'cluster',
                'description': None,
                'group_name': 'dashboard_group_a',
                'group_url': 'http://foo.bar/group',
                'last_successful_run_timestamp': None,
                'name': 'dashboard_c',
                'product': 'foobar',
                'uri': 'foobar_dashboard_1',
                'url': 'http://foo.bar/dashboard_c'
            },
            {
                'chart_names': [],
                'cluster': 'cluster',
                'description': None,
                'group_name': 'dashboard_group_b',
                'group_url': 'http://foo.bar/group',
                'last_successful_run_timestamp': None,
                'name': 'dashboard_b',
                'product': 'foobar',
                'uri': 'foobar_dashboard_3',
                'url': 'http://foo.bar/dashboard_b'
            },
        ]


class UserFollowAPITest(unittest.TestCase):

    @mock.patch('metadata_service.api.user.get_proxy_client')
    def setUp(self, mock_get_proxy_client: MagicMock) -> None:
        self.mock_client = mock.Mock()
        mock_get_proxy_client.return_value = self.mock_client
        self.api = UserFollowAPI()

    def test_table_put(self) -> None:
        response = self.api.put(user_id='username', resource_type='table', resource_id='3')
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        self.mock_client.add_resource_relation_by_user.assert_called_with(id='3',
                                                                          user_id='username',
                                                                          relation_type=UserResourceRel.follow,
                                                                          resource_type=ResourceType.Table)

    def test_dashboard_put(self) -> None:
        response = self.api.put(user_id='username', resource_type='dashboard', resource_id='3')
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        self.mock_client.add_resource_relation_by_user.assert_called_with(id='3',
                                                                          user_id='username',
                                                                          relation_type=UserResourceRel.follow,
                                                                          resource_type=ResourceType.Dashboard)

    def test_table_delete(self) -> None:
        response = self.api.delete(user_id='username', resource_type='table', resource_id='3')
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        self.mock_client.delete_resource_relation_by_user.assert_called_with(id='3',
                                                                             user_id='username',
                                                                             relation_type=UserResourceRel.follow,
                                                                             resource_type=ResourceType.Table)

    def test_dashboard_delete(self) -> None:
        response = self.api.delete(user_id='username', resource_type='dashboard', resource_id='3')
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        self.mock_client.delete_resource_relation_by_user.assert_called_with(id='3',
                                                                             user_id='username',
                                                                             relation_type=UserResourceRel.follow,
                                                                             resource_type=ResourceType.Dashboard)


class UserOwnsAPITest(unittest.TestCase):

    @mock.patch('metadata_service.api.user.get_proxy_client')
    def setUp(self, mock_get_proxy_client: MagicMock) -> None:
        self.mock_client = mock.Mock()
        mock_get_proxy_client.return_value = self.mock_client
        self.api = UserOwnsAPI()

    def test_get(self) -> None:
        self.mock_client.get_table_by_user_relation.return_value = {'table': []}
        self.mock_client.get_dashboard_by_user_relation.return_value = {'dashboard': []}
        response = self.api.get(user_id='username')
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        self.mock_client.get_table_by_user_relation.assert_called_once()
        self.mock_client.get_dashboard_by_user_relation.assert_called_once()


class UserOwnAPITest(unittest.TestCase):

    @mock.patch('metadata_service.api.user.get_proxy_client')
    def setUp(self, mock_get_proxy_client: MagicMock) -> None:
        self.mock_client = mock.Mock()
        mock_get_proxy_client.return_value = self.mock_client
        self.api = UserOwnAPI()

    def test_put(self) -> None:
        response = self.api.put(user_id='username', resource_type='2', table_uri='3')
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        self.mock_client.add_owner.assert_called_once()

    def test_delete(self) -> None:
        response = self.api.delete(user_id='username', resource_type='2', table_uri='3')
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        self.mock_client.delete_owner.assert_called_once()


class UserReadsAPITest(unittest.TestCase):
    @mock.patch('metadata_service.api.user.get_proxy_client')
    def test_get(self, mock_get_proxy_client: MagicMock) -> None:
        mock_client = mock.Mock()
        mock_get_proxy_client.return_value = mock_client
        mock_client.get_frequently_used_tables.return_value = {'table': []}
        api = UserReadsAPI()
        response = api.get(user_id='username')
        self.assertEqual(list(response)[1], HTTPStatus.OK)
        mock_client.get_frequently_used_tables.assert_called_once()
