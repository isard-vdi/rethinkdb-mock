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
def templates_db_factory():
    """Fixture to create a mock database for templates."""

    def templates_db_tables_data(jwt):
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
                },
                {
                    "id": "desktop-1",
                    "kind": "desktop",
                    "user": jwt.payload["user_id"],
                    "group": jwt.payload["group_id"],
                    "category": jwt.payload["category_id"],
                    "create_dict": {"hardware": {"isos": []}},
                    "name": "Desktop 1",
                    "description": "Test desktop 1",
                    "image": "aW1hZ2U=",
                },
                # {
                #     "id": "template-2",
                #     "kind": "template",
                #     "user": "another-user",
                #     "group": jwt.payload["group_id"],
                #     "category": jwt.payload["category_id"],
                #     "create_dict": {"hardware": {"isos": []}},
                #     "name": "Template 1",
                #     "description": "Test template 1",
                #     "image": "YW5vdGhlci1pbWFnZQ==",
                # },
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
                    "role_id": "advanced",
                    "provider": "local",
                    "group": jwt.payload["group_id"],
                    "category": jwt.payload["category_id"],
                },
            ],
            "groups": [
                {
                    "id": jwt.payload["group_id"],
                }
            ],
            "categories": [
                {
                    "id": jwt.payload["category_id"],
                }
            ],
        }

    return templates_db_tables_data


def test_get_all_templates(test_client, templates_db_factory):
    jwt = MockJWT(role_id="advanced")

    db_tables_data = templates_db_factory(jwt)

    expected_response = {
        "templates": [
            {
                "id": "template-1",
                "create_dict": {"hardware": {"isos": [], "interfaces": []}},
                "name": "Template 1",
                "user": "Administrator",
                "user_name": "Administrator",
                "group": "default-default",
                "category": "default",
                "description": "Test template 1",
                "image": "dGVzdA==",
            }
        ]
    }

    response = test_client(
        db_tables_data=db_tables_data,
        method="GET",
        url="/api/v4/items/templates",
        jwt=jwt,
    )

    assert response.status_code == 200
    assert response.json() == expected_response
