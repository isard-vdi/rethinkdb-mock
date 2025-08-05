#
#   Copyright © 2025 Pau Abril Iranzo
#
#   This file is part of IsardVDI.
#
#   IsardVDI is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or (at your
#   option) any later version.
#
#   IsardVDI is distributed in the hope that it will be useful, but WITHOUT ANY
#   WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#   FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
#   details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with IsardVDI. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later


import pytest
from api.routes.tests.helpers import MockJWT


@pytest.fixture()
def media_db_factory():
    """Fixture to create a mock database for templates."""

    def media_db_tables_data(jwt: MockJWT):
        return {
            "domains": [
                {
                    "id": "template-1",
                    "kind": "template",
                    "user": jwt.payload["user_id"],
                    "group": jwt.payload["group_id"],
                    "category": jwt.payload["category_id"],
                    "create_dict": {"hardware": {"isos": []}},
                    "name": "Template 1",
                    "description": "Test template 1",
                    "image": "dGVzdA==",
                    "status": "Stopped",
                },
                {
                    "id": "desktop-1",
                    "kind": "desktop",
                    "user": jwt.payload["user_id"],
                    "group": jwt.payload["group_id"],
                    "category": jwt.payload["category_id"],
                    "create_dict": {
                        "hardware": {
                            "isos": [
                                {
                                    "description": "lorem ipsum dolor sit amet, consectetur adipiscing elit",
                                    "id": "media-1",
                                    "name": "dsl-4.4.10.iso",
                                }
                            ]
                        }
                    },
                    "name": "Desktop 1",
                    "description": "Test desktop 1",
                    "image": "aW1hZ2U=",
                    "status": "Stopped",
                },
                {
                    "id": "desktop-2",
                    "kind": "desktop",
                    "user": jwt.payload["user_id"],
                    "group": jwt.payload["group_id"],
                    "category": jwt.payload["category_id"],
                    "create_dict": {"hardware": {"isos": []}},
                    "name": "Desktop 2",
                    "description": "Test desktop 2",
                    "image": "aW1hZ2U=",
                    "status": "Stopped",
                },
                {
                    "id": "desktop-3",
                    "kind": "desktop",
                    "user": "another-user",
                    "group": jwt.payload["group_id"],
                    "category": jwt.payload["category_id"],
                    "create_dict": {
                        "hardware": {
                            "isos": [
                                {
                                    "description": "lorem ipsum dolor sit amet, consectetur adipiscing elit",
                                    "id": "media-1",
                                    "name": "dsl-4.4.10.iso",
                                }
                            ]
                        }
                    },
                    "name": "Desktop 3",
                    "description": "Test desktop 3",
                    "image": "aW1hZ2U=",
                    "status": "Stopped",
                },
            ],
            "media": [
                {
                    "accessed": 1709728599,
                    "allowed": {
                        "categories": False,
                        "groups": False,
                        "roles": False,
                        "users": ["another-user"],
                    },
                    "category": jwt.payload["category_id"],
                    "description": "lorem ipsum dolor sit amet, consectetur adipiscing elit",
                    "group": jwt.payload["group_id"],
                    "icon": "fa-circle-o",
                    "id": "media-1",
                    "kind": "iso",
                    "name": "dsl-4.4.10.iso",
                    "path": "{category}/{group}/{provider}/{user}/dsl-4.4.10.iso".format(
                        category=jwt.payload["category_id"],
                        group=jwt.payload["group_id"],
                        provider=jwt.payload["provider"],
                        user=jwt.payload["user_id"],
                    ),
                    "path_downloaded": "/isard/media/media-1.iso",
                    "progress": {
                        "received": "415M",
                        "received_percent": 97,
                        "speed_current": "19.2M",
                        "speed_download_average": "25.9M",
                        "speed_upload_average": "0",
                        "time_left": "0:00:01",
                        "time_spent": "0:00:15",
                        "time_total": "0:00:16",
                        "total": "415M",
                        "total_bytes": 435159040,
                        "total_percent": 100,
                        "xferd": "0",
                        "xferd_percent": "0",
                    },
                    "status": "Downloaded",
                    "status_time": 1709896679.0916216,
                    "url-isard": False,
                    "url-web": "https://example.org/dsl-4.4.10.iso",
                    "user": jwt.payload["user_id"],
                    "username": jwt.payload["name"],
                },
            ],
            "users": [
                {
                    "id": jwt.payload["user_id"],
                    "name": jwt.payload["name"],
                    "username": jwt.payload["name"],
                    "role_id": jwt.payload["role_id"],
                    "provider": jwt.payload["provider"],
                    "group": jwt.payload["group_id"],
                    "category": jwt.payload["category_id"],
                },
                {
                    "id": "another-user",
                    "name": "Another User",
                    "username": "another-user",
                    "uid": "another-user",
                    "role_id": "advanced",
                    "provider": "local",
                    "group": jwt.payload["group_id"],
                    "category": jwt.payload["category_id"],
                },
                {
                    "id": "another-user-2",
                    "name": "Another Another User",
                    "username": "another-user-2",
                    "role_id": "manager",
                    "provider": "local",
                    "group": jwt.payload["group_id"],
                    "category": jwt.payload["category_id"],
                },
            ],
            "groups": [
                {
                    "id": jwt.payload["group_id"],
                    "name": "Default Group",
                    "uid": jwt.payload["group_id"],
                    "parent_category": jwt.payload["category_id"],
                }
            ],
            "categories": [
                {
                    "id": jwt.payload["category_id"],
                    "name": "Default Category",
                    "uid": jwt.payload["category_id"],
                }
            ],
        }

    return media_db_tables_data


def test_get_user_media(test_client, media_db_factory):
    jwt = MockJWT()

    db_data = media_db_factory(jwt)

    expected_response = [
        {
            "accessed": 1709728599,
            "allowed": {
                "categories": False,
                "groups": False,
                "roles": False,
                "users": ["another-user"],
            },
            "category": "default",
            "description": "lorem ipsum dolor sit amet, consectetur adipiscing elit",
            "group": "default-default",
            "icon": "fa-circle-o",
            "id": "media-1",
            "kind": "iso",
            "name": "dsl-4.4.10.iso",
            "path": "default/default-default/local/local-default-admin-admin/dsl-4.4.10.iso",
            "path_downloaded": "/isard/media/media-1.iso",
            "progress": {
                "received": "415M",
                "received_percent": 97,
                "speed_current": "19.2M",
                "speed_download_average": "25.9M",
                "speed_upload_average": "0",
                "time_left": "0:00:01",
                "time_spent": "0:00:15",
                "time_total": "0:00:16",
                "total": "415M",
                "total_bytes": 435159040,
                "total_percent": 100,
                "xferd": "0",
                "xferd_percent": "0",
            },
            "status": "Downloaded",
            "status_time": 1709896679.0916216,
            "url-isard": False,
            "url-web": "https://example.org/dsl-4.4.10.iso",
            "user": "local-default-admin-admin",
            "username": "Administrator",
            "editable": True,
        }
    ]

    response = test_client(
        db_tables_data=db_data,
        method="GET",
        url="/items/media",
        jwt=jwt,
    )

    assert response.status_code == 200
    assert response.json() == expected_response


def test_get_media_allowed(test_client, media_db_factory):
    expected_response = [
        {
            "id": "media-1",
            "name": "dsl-4.4.10.iso",
            "status": "Downloaded",
            "category": "default",
            "category_name": "Default Category",
            "group": "default-default",
            "group_name": "Default Group",
            "progress": {
                "received": "415M",
                "received_percent": 97,
                "speed_current": "19.2M",
                "speed_download_average": "25.9M",
                "speed_upload_average": "0",
                "time_left": "0:00:01",
                "time_spent": "0:00:15",
                "time_total": "0:00:16",
                "total": "415M",
                "total_bytes": 435159040,
                "total_percent": 100,
                "xferd": "0",
                "xferd_percent": "0",
            },
            "user": "local-default-admin-admin",
            "description": "lorem ipsum dolor sit amet, consectetur adipiscing elit",
            "kind": "iso",
            "icon": "fa-circle-o",
            "url-isard": False,
            "url-web": "https://example.org/dsl-4.4.10.iso",
            "allowed": {
                "categories": False,
                "groups": False,
                "roles": False,
                "users": ["another-user"],
            },
            "user_name": "Administrator",
            "editable": True,
        }
    ]

    response = test_client(
        db_tables_data=media_db_factory(MockJWT()),
        method="GET",
        url="/items/media/get-shared",
        jwt=MockJWT(user_id="another-user"),
    )

    assert response.status_code == 200
    assert response.json() == expected_response


def test_get_media_allowed_none(test_client, media_db_factory):
    """Test when no media is shared with the user."""
    response = test_client(
        db_tables_data=media_db_factory(MockJWT()),
        method="GET",
        url="/items/media/get-shared",
        jwt=MockJWT(user_id="another-user-2"),
    )

    assert response.status_code == 200
    assert response.json() == []


# TODO: r.args(v) does not work correctly with rethinkdb_mock
# def test_get_media_allowed_table(test_client, media_db_factory):
#     jwt = MockJWT()
#
#     db_data = media_db_factory(jwt)
#
#     expected_response = {
#         "categories": False,
#         "groups": False,
#         "roles": False,
#         "users": [
#             {
#                 "category_name": "Default",
#                 "group_name": "Default",
#                 "id": "another-user",
#                 "name": "Another User",
#                 "uid": "another-user",
#             }
#         ],
#     }
#
#     response = test_client(
#         db_tables_data=db_data,
#         method="GET",
#         url="/item/media/{media_id}/get-allowed".format(
#             media_id="media-1",
#         ),
#         jwt=jwt,
#     )
#
#     assert response.status_code == 200
#     assert response.json() == expected_response


# TODO: r.args(v) does not work correctly with rethinkdb_mock
# def test_get_media_allowed_table_all_fields(test_client, media_db_factory):
#     jwt = MockJWT()
#
#     db_data = media_db_factory(jwt)
#
#     db_data["media"][0]["allowed"] = {
#         "categories": [jwt.payload["category_id"]],
#         "groups": [jwt.payload["group_id"]],
#         "roles": [],
#         "users": ["another-user"],
#     }
#
#     expected_response = {
#         "categories": [
#             {
#                 "id": jwt.payload["category_id"],
#                 "name": "Default Category",
#                 "uid": jwt.payload["category_id"],
#             }
#         ],
#         "groups": [
#             {
#                 "category_name": "Default Category",
#                 "id": jwt.payload["group_id"],
#                 "name": "Default Group",
#                 "parent_category": jwt.payload["category_id"],
#                 "uid": jwt.payload["group_id"],
#             }
#         ],
#         "roles": [],
#         "users": [
#             {
#                 "category_name": "Default Category",
#                 "group_name": "Default Group",
#                 "id": "another-user",
#                 "name": "Another User",
#                 "uid": "another-user",
#             }
#         ],
#     }
#
#     response = test_client(
#         db_tables_data=db_data,
#         method="GET",
#         url="/item/media/{media_id}/get-allowed".format(
#             media_id="media-1",
#         ),
#         jwt=jwt,
#     )
#
#     assert response.status_code == 200
#     assert response.json() == expected_response


def test_get_media_desktops(test_client, media_db_factory):
    jwt = MockJWT()

    db_data = media_db_factory(jwt)

    expected_response = [
        {
            "create_dict": {
                "hardware": {
                    "isos": [
                        {
                            "description": "lorem ipsum dolor sit amet, consectetur adipiscing elit",
                            "id": "media-1",
                            "name": "dsl-4.4.10.iso",
                        }
                    ]
                }
            },
            "id": "desktop-1",
            "kind": "desktop",
            "name": "Desktop 1",
            "status": "Stopped",
            "user": "local-default-admin-admin",
            "user_name": "Administrator",
        },
        {
            "create_dict": {
                "hardware": {
                    "isos": [
                        {
                            "description": "lorem ipsum dolor sit amet, consectetur adipiscing elit",
                            "id": "media-1",
                            "name": "dsl-4.4.10.iso",
                        }
                    ]
                }
            },
            "id": "desktop-3",
            "kind": "desktop",
            "name": "Desktop 3",
            "status": "Stopped",
            "user": "another-user",
            "user_name": "Another User",
        },
    ]

    response = test_client(
        db_tables_data=db_data,
        method="GET",
        url="/item/media/{media_id}/get-desktops".format(
            media_id="media-1",
        ),
        jwt=jwt,
    )

    assert response.status_code == 200
    assert response.json() == expected_response
