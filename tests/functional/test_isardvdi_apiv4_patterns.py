#!/usr/bin/env python3
"""
IsardVDI APIv4 equivalent tests for rethinkdb-mock

These tests replicate the exact database query patterns used in IsardVDI's APIv4
test suite to ensure rethinkdb-mock handles all their use cases correctly.
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestIsardVDIMediaPatterns(MockTest):
    """Test media-related patterns from IsardVDI APIv4"""

    def get_data(self):
        # Replicate IsardVDI media structure
        media_data = [
            {
                "id": "media1",
                "name": "ubuntu-20.04.iso",
                "status": "Downloaded",
                "user": "admin",
                "category": "system",
                "kind": "file",
                "url-web": "http://ubuntu.com/ubuntu-20.04.iso",
                "url-isard": "http://storage/ubuntu-20.04.iso",
                "detail": "Ubuntu 20.04 LTS",
                "description": "Ubuntu Desktop 20.04 LTS installation media",
                "icon": "fa-ubuntu",
                "size": 2800000000,  # ~2.8GB
                "progress": {"total": 2800000000, "received": 2800000000},
                "domains": ["domain1", "domain2"],
                "hypervisors_pools": ["default"],
                "allowed": {
                    "roles": ["admin"],
                    "categories": ["system"],
                    "groups": [],
                    "users": [],
                },
            },
            {
                "id": "media2",
                "name": "windows-10.iso",
                "status": "Available",
                "user": "user1",
                "category": "desktop",
                "kind": "file",
                "url-web": "http://microsoft.com/windows-10.iso",
                "url-isard": "http://storage/windows-10.iso",
                "detail": "Windows 10 Pro",
                "description": "Windows 10 Professional installation media",
                "icon": "fa-windows",
                "size": 4500000000,  # ~4.5GB
                "progress": {"total": 4500000000, "received": 4500000000},
                "domains": ["domain3"],
                "hypervisors_pools": ["default", "pool1"],
                "allowed": {
                    "roles": ["user"],
                    "categories": ["desktop"],
                    "groups": ["users"],
                    "users": ["user1", "user2"],
                },
            },
            {
                "id": "media3",
                "name": "centos-8.iso",
                "status": "Downloading",
                "user": "admin",
                "category": "server",
                "kind": "file",
                "url-web": "http://centos.org/centos-8.iso",
                "url-isard": "http://storage/centos-8.iso",
                "detail": "CentOS 8",
                "description": "CentOS 8 server installation media",
                "icon": "fa-server",
                "size": 7000000000,  # ~7GB
                "progress": {"total": 7000000000, "received": 3500000000},
                "domains": [],
                "hypervisors_pools": ["default"],
                "allowed": {
                    "roles": ["admin", "manager"],
                    "categories": ["server"],
                    "groups": [],
                    "users": [],
                },
            },
        ]

        categories_data = [
            {"id": "system", "name": "System", "enabled": True},
            {"id": "desktop", "name": "Desktop", "enabled": True},
            {"id": "server", "name": "Server", "enabled": False},
        ]

        users_data = [
            {"id": "admin", "name": "Administrator", "role": "admin"},
            {"id": "user1", "name": "Test User", "role": "user"},
            {"id": "user2", "name": "Another User", "role": "user"},
        ]

        return {
            **as_db_and_table("isard", "media", media_data),
            **as_db_and_table("isard", "categories", categories_data),
            **as_db_and_table("isard", "users", users_data),
        }

    def test_get_media_allowed_admin(self, conn):
        """Test getting media allowed for admin role - replicates test_media.py::test_get_media_allowed"""
        # This is the exact pattern from IsardVDI's get_media_allowed_domain function
        result = list(
            r.db("isard")
            .table("media")
            .filter({"status": "Downloaded"})
            .filter(
                lambda media: (
                    r.expr(["admin"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "media1")
        assertEqual(result[0]["name"], "ubuntu-20.04.iso")

    def test_get_media_allowed_user(self, conn):
        """Test getting media allowed for user role"""
        result = list(
            r.db("isard")
            .table("media")
            .filter({"status": "Available"})
            .filter(
                lambda media: (
                    r.expr(["user"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "media2")

    def test_get_media_allowed_none_handling(self, conn):
        """Test media access with None/empty roles - replicates test_media.py::test_get_media_allowed_none"""
        # Test the None handling pattern
        result = list(
            r.db("isard")
            .table("media")
            .filter(
                lambda media: r.branch(
                    r.row["allowed"]["roles"].default(None) == None,
                    True,  # If roles is None, allow access
                    r.expr(["admin"])
                    .set_intersection(r.row["allowed"]["roles"].default([]))
                    .count()
                    > 0,
                )
            )
            .run(conn)
        )

        # Should find media that either have no roles restriction or admin access
        assertEqual(len(result), 2)  # media1 (admin) and media3 (admin, manager)

    def test_get_media_with_category_info(self, conn):
        """Test media retrieval with category information join"""
        result = list(
            r.db("isard")
            .table("media")
            .filter({"status": "Downloaded"})
            .map(
                lambda media: media.merge(
                    {
                        "category_info": r.db("isard")
                        .table("categories")
                        .get(r.row["category"])
                        .default({"name": "Unknown", "enabled": False}),
                    }
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["category_info"]["name"], "System")
        assertEqual(result[0]["category_info"]["enabled"], True)

    def test_get_media_with_user_info(self, conn):
        """Test media retrieval with user information join"""
        result = list(
            r.db("isard")
            .table("media")
            .map(
                lambda media: media.merge(
                    {
                        "user_info": r.db("isard")
                        .table("users")
                        .get(r.row["user"])
                        .default({"name": "Unknown User"}),
                    }
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 3)
        assertEqual(result[0]["user_info"]["name"], "Administrator")
        assertEqual(result[1]["user_info"]["name"], "Test User")

    def test_media_access_with_multiple_criteria(self, conn):
        """Test complex media access filtering with multiple criteria"""
        result = list(
            r.db("isard")
            .table("media")
            .filter(
                lambda media: (
                    # Check role access
                    r.expr(["admin", "manager"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
                & (
                    # Check category access
                    r.expr(["system", "server"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["categories"].default([]).is_empty(),
                            ["default"],
                            r.row["allowed"]["categories"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 2)  # media1 and media3
        media_ids = {item["id"] for item in result}
        assertEqual(media_ids, {"media1", "media3"})

    def test_media_progress_calculation(self, conn):
        """Test media download progress calculations"""
        result = list(
            r.db("isard")
            .table("media")
            .map(
                lambda media: {
                    "id": r.row["id"],
                    "name": r.row["name"],
                    "status": r.row["status"],
                    "progress_percent": r.branch(
                        r.row["progress"]["total"] > 0,
                        (r.row["progress"]["received"] * 100)
                        / r.row["progress"]["total"],
                        0,
                    ),
                    "size_gb": r.row["size"] / 1000000000,
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 3)

        # Check progress calculations
        for item in result:
            if item["id"] == "media1":
                assertEqual(item["progress_percent"], 100.0)
                assertEqual(item["size_gb"], 2.8)
            elif item["id"] == "media2":
                assertEqual(item["progress_percent"], 100.0)
                assertEqual(item["size_gb"], 4.5)
            elif item["id"] == "media3":
                assertEqual(item["progress_percent"], 50.0)
                assertEqual(item["size_gb"], 7.0)


class TestIsardVDITemplatePatterns(MockTest):
    """Test template/domain-related patterns from IsardVDI APIv4"""

    def get_data(self):
        # Replicate IsardVDI domains (templates) structure
        domains_data = [
            {
                "id": "template1",
                "name": "Ubuntu Base Template",
                "status": "Available",
                "user": "admin",
                "category": "system",
                "kind": "template",
                "enabled": True,
                "icon": "fa-ubuntu",
                "description": "Base Ubuntu template for general use",
                "detail": "Ubuntu 20.04 LTS base template",
                "allowed": {
                    "roles": ["admin", "user"],
                    "categories": ["system", "desktop"],
                    "groups": [],
                    "users": [],
                },
                "create_dict": {
                    "hardware": {"vcpus": 2, "memory": 2048},
                    "origin": "ubuntu-base",
                },
                "hypervisors_pools": ["default"],
                "tags": ["linux", "ubuntu", "base"],
            },
            {
                "id": "template2",
                "name": "Windows Desktop Template",
                "status": "Available",
                "user": "admin",
                "category": "desktop",
                "kind": "template",
                "enabled": True,
                "icon": "fa-windows",
                "description": "Windows 10 desktop template",
                "detail": "Windows 10 Pro desktop template",
                "allowed": {
                    "roles": ["user"],
                    "categories": ["desktop"],
                    "groups": ["windows-users"],
                    "users": [],
                },
                "create_dict": {
                    "hardware": {"vcpus": 4, "memory": 4096},
                    "origin": "windows-base",
                },
                "hypervisors_pools": ["default", "pool1"],
                "tags": ["windows", "desktop"],
            },
            {
                "id": "template3",
                "name": "Server Template",
                "status": "Building",
                "user": "admin",
                "category": "server",
                "kind": "template",
                "enabled": False,
                "icon": "fa-server",
                "description": "CentOS server template",
                "detail": "CentOS 8 server template",
                "allowed": {
                    "roles": ["admin"],
                    "categories": ["server"],
                    "groups": [],
                    "users": ["admin"],
                },
                "create_dict": {
                    "hardware": {"vcpus": 8, "memory": 8192},
                    "origin": "centos-base",
                },
                "hypervisors_pools": ["default"],
                "tags": ["linux", "centos", "server"],
            },
        ]

        categories_data = [
            {"id": "system", "name": "System", "enabled": True},
            {"id": "desktop", "name": "Desktop", "enabled": True},
            {"id": "server", "name": "Server", "enabled": True},
        ]

        users_data = [
            {"id": "admin", "name": "Administrator", "role": "admin"},
            {"id": "user1", "name": "Test User", "role": "user"},
        ]

        return {
            **as_db_and_table("isard", "domains", domains_data),
            **as_db_and_table("isard", "categories", categories_data),
            **as_db_and_table("isard", "users", users_data),
        }

    def test_get_all_templates_allowed(self, conn):
        """Test getting all allowed templates - replicates test_templates.py::test_get_all_templates"""
        # This is the exact pattern from IsardVDI's template filtering
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .filter(
                lambda template: (
                    # Check if user roles intersect with template allowed roles
                    r.expr(["user"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["roles"].default([]).is_empty(),
                            ["admin", "manager", "advanced", "user"],
                            r.row["allowed"]["roles"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
                & (
                    # Check if user categories intersect with template allowed categories
                    r.expr(["desktop"])
                    .set_intersection(
                        r.branch(
                            r.row["allowed"]["categories"].default([]).is_empty(),
                            ["default"],
                            r.row["allowed"]["categories"].default([]),
                        )
                    )
                    .count()
                    > 0
                )
            )
            .map(
                lambda template: template.merge(
                    {
                        "category_name": r.db("isard")
                        .table("categories")
                        .get(r.row["category"])
                        .default({"name": "Unknown"})["name"],
                        "user_name": r.db("isard")
                        .table("users")
                        .get(r.row["user"])
                        .default({"name": "Unknown"})["name"],
                    }
                )
            )
            .run(conn)
        )

        # Should find template2 which matches the criteria
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "template2")
        assertEqual(result[0]["category_name"], "Desktop")
        assertEqual(result[0]["user_name"], "Administrator")

    def test_get_templates_by_category(self, conn):
        """Test getting templates filtered by category"""
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "category": "system"})
            .filter(
                lambda template: r.db("isard")
                .table("categories")
                .get(r.row["category"])
                .default({"enabled": False})["enabled"]
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "template1")

    def test_template_with_hardware_specs(self, conn):
        """Test template retrieval with hardware specifications"""
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .map(
                lambda template: {
                    "id": r.row["id"],
                    "name": r.row["name"],
                    "vcpus": r.row["create_dict"]["hardware"]["vcpus"],
                    "memory_gb": r.row["create_dict"]["hardware"]["memory"] / 1024,
                    "tags": r.row["tags"],
                    "pools": r.row["hypervisors_pools"],
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 2)

        for template in result:
            if template["id"] == "template1":
                assertEqual(template["vcpus"], 2)
                assertEqual(template["memory_gb"], 2.0)
                assertEqual(template["tags"], ["linux", "ubuntu", "base"])
            elif template["id"] == "template2":
                assertEqual(template["vcpus"], 4)
                assertEqual(template["memory_gb"], 4.0)
                assertEqual(template["tags"], ["windows", "desktop"])

    def test_template_access_by_groups(self, conn):
        """Test template access filtering by groups"""
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template", "enabled": True})
            .filter(
                lambda template: r.branch(
                    r.row["allowed"]["groups"].default([]).is_empty(),
                    True,  # No group restriction
                    r.row["allowed"]["groups"].default([]).contains("windows-users"),
                )
            )
            .run(conn)
        )

        assertEqual(
            len(result), 2
        )  # template1 (no restriction) and template2 (windows-users)

    def test_template_with_complex_joins(self, conn):
        """Test template with multiple table joins"""
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "template"})
            .map(
                lambda template: template.merge(
                    {
                        "category_info": r.db("isard")
                        .table("categories")
                        .get(r.row["category"])
                        .default({"name": "Unknown", "enabled": False}),
                        "owner_info": r.db("isard")
                        .table("users")
                        .get(r.row["user"])
                        .default({"name": "Unknown", "role": "unknown"}),
                        "is_accessible": r.branch(
                            r.row["enabled"] == True,
                            r.branch(
                                r.row["allowed"]["roles"].default([]).contains("user"),
                                "accessible",
                                "restricted",
                            ),
                            "disabled",
                        ),
                    }
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 3)

        for template in result:
            if template["id"] == "template1":
                assertEqual(template["category_info"]["name"], "System")
                assertEqual(template["owner_info"]["name"], "Administrator")
                assertEqual(template["is_accessible"], "accessible")
            elif template["id"] == "template2":
                assertEqual(template["category_info"]["name"], "Desktop")
                assertEqual(template["is_accessible"], "accessible")
            elif template["id"] == "template3":
                assertEqual(template["category_info"]["name"], "Server")
                assertEqual(template["is_accessible"], "disabled")


class TestIsardVDIAdvancedPatterns(MockTest):
    """Test advanced database patterns used in IsardVDI APIv4"""

    def get_data(self):
        # Complex data structure similar to IsardVDI
        domains_data = [
            {
                "id": "desktop1",
                "name": "User Desktop 1",
                "kind": "desktop",
                "status": "Started",
                "user": "user1",
                "category": "desktop",
                "template": "template1",
                "viewers": [
                    {"id": "viewer1", "type": "spice", "port": 5900},
                    {"id": "viewer2", "type": "vnc", "port": 5901},
                ],
                "hardware": {"vcpus": 2, "memory": 2048, "disk_size": 20},
                "network": {"ip": "192.168.1.100", "mac": "52:54:00:12:34:56"},
                "hypervisor": "hyp1",
                "allowed": {"roles": ["user"], "users": ["user1"]},
            },
            {
                "id": "desktop2",
                "name": "User Desktop 2",
                "kind": "desktop",
                "status": "Stopped",
                "user": "user2",
                "category": "desktop",
                "template": "template2",
                "viewers": [
                    {"id": "viewer3", "type": "spice", "port": 5902},
                ],
                "hardware": {"vcpus": 4, "memory": 4096, "disk_size": 40},
                "network": {"ip": "192.168.1.101", "mac": "52:54:00:12:34:57"},
                "hypervisor": "hyp2",
                "allowed": {"roles": ["user"], "users": ["user2"]},
            },
        ]

        hypervisors_data = [
            {
                "id": "hyp1",
                "hostname": "hypervisor1.local",
                "status": "Online",
                "resources": {
                    "cpu_used": 20,
                    "cpu_total": 100,
                    "memory_used": 8,
                    "memory_total": 32,
                },
                "capabilities": ["kvm", "spice", "vnc"],
            },
            {
                "id": "hyp2",
                "hostname": "hypervisor2.local",
                "status": "Online",
                "resources": {
                    "cpu_used": 40,
                    "cpu_total": 100,
                    "memory_used": 16,
                    "memory_total": 64,
                },
                "capabilities": ["kvm", "spice"],
            },
        ]

        users_data = [
            {
                "id": "user1",
                "name": "Test User 1",
                "role": "user",
                "category": "desktop",
            },
            {
                "id": "user2",
                "name": "Test User 2",
                "role": "user",
                "category": "desktop",
            },
        ]

        return {
            **as_db_and_table("isard", "domains", domains_data),
            **as_db_and_table("isard", "hypervisors", hypervisors_data),
            **as_db_and_table("isard", "users", users_data),
        }

    def test_desktop_with_hypervisor_info(self, conn):
        """Test desktop retrieval with hypervisor information"""
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "desktop", "status": "Started"})
            .map(
                lambda desktop: desktop.merge(
                    {
                        "hypervisor_info": r.db("isard")
                        .table("hypervisors")
                        .get(r.row["hypervisor"])
                        .default({"hostname": "unknown", "status": "offline"}),
                        "resource_usage": r.db("isard")
                        .table("hypervisors")
                        .get(r.row["hypervisor"])
                        .default({"resources": {"cpu_used": 0, "memory_used": 0}})[
                            "resources"
                        ],
                    }
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["hypervisor_info"]["hostname"], "hypervisor1.local")
        assertEqual(result[0]["resource_usage"]["cpu_used"], 20)

    def test_user_desktop_access_pattern(self, conn):
        """Test user-specific desktop access pattern"""
        user_id = "user1"
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "desktop"})
            .filter(
                lambda desktop: r.branch(
                    # Check if user has direct access
                    r.row["allowed"]["users"].default([]).contains(user_id),
                    True,
                    # Check if user role matches
                    r.expr(["user"])
                    .set_intersection(r.row["allowed"]["roles"].default([]))
                    .count()
                    > 0,
                )
            )
            .filter(lambda desktop: r.row["user"] == user_id)
            .map(
                lambda desktop: desktop.merge(
                    {
                        "owner_info": r.db("isard")
                        .table("users")
                        .get(r.row["user"])
                        .default({"name": "Unknown"}),
                        "viewers_count": r.row["viewers"].count(),
                        "memory_gb": r.row["hardware"]["memory"] / 1024,
                    }
                )
            )
            .run(conn)
        )

        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], "desktop1")
        assertEqual(result[0]["owner_info"]["name"], "Test User 1")
        assertEqual(result[0]["viewers_count"], 2)

    def test_hypervisor_resource_aggregation(self, conn):
        """Test aggregating resource usage across hypervisors"""
        result = list(
            r.db("isard")
            .table("hypervisors")
            .filter({"status": "Online"})
            .map(
                lambda hyp: {
                    "id": r.row["id"],
                    "hostname": r.row["hostname"],
                    "cpu_usage_percent": (r.row["resources"]["cpu_used"] * 100)
                    / r.row["resources"]["cpu_total"],
                    "memory_usage_percent": (r.row["resources"]["memory_used"] * 100)
                    / r.row["resources"]["memory_total"],
                    "domains_count": r.db("isard")
                    .table("domains")
                    .filter({"hypervisor": r.row["id"]})
                    .count(),
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 2)

        for hyp in result:
            if hyp["id"] == "hyp1":
                assertEqual(hyp["cpu_usage_percent"], 20.0)
                assertEqual(hyp["memory_usage_percent"], 25.0)
                assertEqual(hyp["domains_count"], 1)
            elif hyp["id"] == "hyp2":
                assertEqual(hyp["cpu_usage_percent"], 40.0)
                assertEqual(hyp["memory_usage_percent"], 25.0)
                assertEqual(hyp["domains_count"], 1)

    def test_complex_filtering_with_arrays(self, conn):
        """Test complex filtering involving array operations"""
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "desktop"})
            .filter(
                lambda desktop: r.row["viewers"]
                .filter(lambda viewer: viewer["type"] == "spice")
                .count()
                > 0
            )
            .map(
                lambda desktop: {
                    "id": r.row["id"],
                    "name": r.row["name"],
                    "spice_viewers": r.row["viewers"].filter(
                        lambda viewer: viewer["type"] == "spice"
                    ),
                    "total_viewers": r.row["viewers"].count(),
                    "has_vnc": r.row["viewers"]
                    .filter(lambda viewer: viewer["type"] == "vnc")
                    .count()
                    > 0,
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 2)

        for desktop in result:
            if desktop["id"] == "desktop1":
                assertEqual(len(desktop["spice_viewers"]), 1)
                assertEqual(desktop["total_viewers"], 2)
                assertEqual(desktop["has_vnc"], True)
            elif desktop["id"] == "desktop2":
                assertEqual(len(desktop["spice_viewers"]), 1)
                assertEqual(desktop["total_viewers"], 1)
                assertEqual(desktop["has_vnc"], False)

    def test_nested_conditional_logic(self, conn):
        """Test deeply nested conditional logic patterns"""
        result = list(
            r.db("isard")
            .table("domains")
            .filter({"kind": "desktop"})
            .map(
                lambda desktop: {
                    "id": r.row["id"],
                    "status_info": r.branch(
                        r.row["status"] == "Started",
                        r.branch(
                            r.row["viewers"].count() > 0,
                            "running_with_viewers",
                            "running_no_viewers",
                        ),
                        r.branch(
                            r.row["status"] == "Stopped",
                            "stopped",
                            r.branch(
                                r.row["status"] == "Starting",
                                "starting",
                                "unknown_status",
                            ),
                        ),
                    ),
                    "resource_level": r.branch(
                        r.row["hardware"]["memory"] >= 4096,
                        "high",
                        r.branch(
                            r.row["hardware"]["memory"] >= 2048,
                            "medium",
                            "low",
                        ),
                    ),
                    "access_level": r.branch(
                        r.row["allowed"]["users"].default([]).count() > 0,
                        "user_specific",
                        r.branch(
                            r.row["allowed"]["roles"].default([]).contains("admin"),
                            "admin_access",
                            "role_based",
                        ),
                    ),
                }
            )
            .run(conn)
        )

        assertEqual(len(result), 2)

        for desktop in result:
            if desktop["id"] == "desktop1":
                assertEqual(desktop["status_info"], "running_with_viewers")
                assertEqual(desktop["resource_level"], "medium")
                assertEqual(desktop["access_level"], "user_specific")
            elif desktop["id"] == "desktop2":
                assertEqual(desktop["status_info"], "stopped")
                assertEqual(desktop["resource_level"], "high")
                assertEqual(desktop["access_level"], "user_specific")


if __name__ == "__main__":
    import unittest

    unittest.main()
