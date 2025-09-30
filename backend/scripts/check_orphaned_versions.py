#!/usr/bin/env python3
"""Check for orphaned versioned objects in MongoDB.

This script inspects the versioned_data collection to find:
1. Orphaned versions (supersedes/superseded_by chains with missing documents)
2. Non-latest versions without superseded_by
3. Latest versions that are superseded
4. Broken dependency chains
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from floridify.caching.models import BaseVersionedData


async def check_orphaned_versions():
    """Check for orphaned and inconsistent versioned objects."""
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["floridify"]  # Production database

    # Initialize Beanie
    await init_beanie(database=db, document_models=[BaseVersionedData])

    print("=" * 80)
    print("VERSIONED OBJECTS HEALTH CHECK")
    print("=" * 80)
    print(f"Database: {db.name}")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 80)
    print()

    # Get all versioned objects
    all_versions = await BaseVersionedData.find_all().to_list()
    print(f"📊 Total versioned objects: {len(all_versions)}")
    print()

    # Create lookup maps
    by_id = {str(v.id): v for v in all_versions}
    by_resource = defaultdict(list)
    for v in all_versions:
        by_resource[v.resource_id].append(v)

    # Statistics
    stats = {
        "total_objects": len(all_versions),
        "unique_resources": len(by_resource),
        "latest_versions": 0,
        "orphaned_supersedes": 0,
        "orphaned_superseded_by": 0,
        "non_latest_without_superseded_by": 0,
        "latest_with_superseded_by": 0,
        "broken_dependencies": 0,
        "by_resource_type": defaultdict(int),
    }

    # Issues found
    issues = {
        "orphaned_supersedes": [],
        "orphaned_superseded_by": [],
        "non_latest_without_superseded_by": [],
        "latest_with_superseded_by": [],
        "broken_dependencies": [],
    }

    # Check each version
    for version in all_versions:
        resource_type = version.resource_type.value
        stats["by_resource_type"][resource_type] += 1

        if version.version_info.is_latest:
            stats["latest_versions"] += 1

        # Check supersedes chain
        if version.version_info.supersedes:
            supersedes_id = str(version.version_info.supersedes)
            if supersedes_id not in by_id:
                stats["orphaned_supersedes"] += 1
                issues["orphaned_supersedes"].append({
                    "id": str(version.id),
                    "resource_id": version.resource_id,
                    "resource_type": resource_type,
                    "version": version.version_info.version,
                    "missing_supersedes_id": supersedes_id,
                })

        # Check superseded_by chain
        if version.version_info.superseded_by:
            superseded_by_id = str(version.version_info.superseded_by)
            if superseded_by_id not in by_id:
                stats["orphaned_superseded_by"] += 1
                issues["orphaned_superseded_by"].append({
                    "id": str(version.id),
                    "resource_id": version.resource_id,
                    "resource_type": resource_type,
                    "version": version.version_info.version,
                    "missing_superseded_by_id": superseded_by_id,
                })

        # Check for non-latest without superseded_by
        if not version.version_info.is_latest and not version.version_info.superseded_by:
            stats["non_latest_without_superseded_by"] += 1
            issues["non_latest_without_superseded_by"].append({
                "id": str(version.id),
                "resource_id": version.resource_id,
                "resource_type": resource_type,
                "version": version.version_info.version,
            })

        # Check for latest with superseded_by (inconsistency)
        if version.version_info.is_latest and version.version_info.superseded_by:
            stats["latest_with_superseded_by"] += 1
            issues["latest_with_superseded_by"].append({
                "id": str(version.id),
                "resource_id": version.resource_id,
                "resource_type": resource_type,
                "version": version.version_info.version,
                "superseded_by_id": str(version.version_info.superseded_by),
            })

        # Check dependencies
        for dep_id in version.version_info.dependencies:
            if str(dep_id) not in by_id:
                stats["broken_dependencies"] += 1
                issues["broken_dependencies"].append({
                    "id": str(version.id),
                    "resource_id": version.resource_id,
                    "resource_type": resource_type,
                    "version": version.version_info.version,
                    "missing_dependency_id": str(dep_id),
                })

    # Print statistics
    print("📈 STATISTICS")
    print("-" * 80)
    print(f"Total objects:         {stats['total_objects']}")
    print(f"Unique resources:      {stats['unique_resources']}")
    print(f"Latest versions:       {stats['latest_versions']}")
    print()
    print("By resource type:")
    for resource_type, count in sorted(stats["by_resource_type"].items()):
        print(f"  {resource_type:15s}: {count:4d}")
    print()

    # Print issues
    total_issues = sum([
        stats["orphaned_supersedes"],
        stats["orphaned_superseded_by"],
        stats["non_latest_without_superseded_by"],
        stats["latest_with_superseded_by"],
        stats["broken_dependencies"],
    ])

    if total_issues == 0:
        print("✅ NO ISSUES FOUND")
        print("   All version chains are intact and consistent.")
        print()
    else:
        print(f"⚠️  ISSUES FOUND: {total_issues}")
        print("-" * 80)
        print()

        if stats["orphaned_supersedes"] > 0:
            print(f"❌ Orphaned 'supersedes' references: {stats['orphaned_supersedes']}")
            print("   These versions point to a previous version that doesn't exist:")
            for issue in issues["orphaned_supersedes"][:5]:  # Show first 5
                print(f"   - {issue['resource_id']} v{issue['version']} "
                      f"({issue['resource_type']})")
                print(f"     Missing: {issue['missing_supersedes_id']}")
            if len(issues["orphaned_supersedes"]) > 5:
                print(f"   ... and {len(issues['orphaned_supersedes']) - 5} more")
            print()

        if stats["orphaned_superseded_by"] > 0:
            print(f"❌ Orphaned 'superseded_by' references: {stats['orphaned_superseded_by']}")
            print("   These versions point to a newer version that doesn't exist:")
            for issue in issues["orphaned_superseded_by"][:5]:
                print(f"   - {issue['resource_id']} v{issue['version']} "
                      f"({issue['resource_type']})")
                print(f"     Missing: {issue['missing_superseded_by_id']}")
            if len(issues["orphaned_superseded_by"]) > 5:
                print(f"   ... and {len(issues['orphaned_superseded_by']) - 5} more")
            print()

        if stats["non_latest_without_superseded_by"] > 0:
            print(f"⚠️  Non-latest without 'superseded_by': {stats['non_latest_without_superseded_by']}")
            print("   These versions are not latest but don't point to their successor:")
            for issue in issues["non_latest_without_superseded_by"][:5]:
                print(f"   - {issue['resource_id']} v{issue['version']} "
                      f"({issue['resource_type']})")
            if len(issues["non_latest_without_superseded_by"]) > 5:
                print(f"   ... and {len(issues['non_latest_without_superseded_by']) - 5} more")
            print()

        if stats["latest_with_superseded_by"] > 0:
            print(f"❌ Latest versions with 'superseded_by': {stats['latest_with_superseded_by']}")
            print("   These versions are marked as latest but have a successor (inconsistency):")
            for issue in issues["latest_with_superseded_by"][:5]:
                print(f"   - {issue['resource_id']} v{issue['version']} "
                      f"({issue['resource_type']})")
                print(f"     Superseded by: {issue['superseded_by_id']}")
            if len(issues["latest_with_superseded_by"]) > 5:
                print(f"   ... and {len(issues['latest_with_superseded_by']) - 5} more")
            print()

        if stats["broken_dependencies"] > 0:
            print(f"❌ Broken dependency references: {stats['broken_dependencies']}")
            print("   These versions depend on objects that don't exist:")
            for issue in issues["broken_dependencies"][:5]:
                print(f"   - {issue['resource_id']} v{issue['version']} "
                      f"({issue['resource_type']})")
                print(f"     Missing dependency: {issue['missing_dependency_id']}")
            if len(issues["broken_dependencies"]) > 5:
                print(f"   ... and {len(issues['broken_dependencies']) - 5} more")
            print()

    # Print per-resource analysis
    print("=" * 80)
    print("PER-RESOURCE VERSION CHAINS")
    print("=" * 80)
    print()

    resources_with_issues = 0
    for resource_id, versions in sorted(by_resource.items()):
        if len(versions) == 1:
            continue  # Single version resources are always consistent

        # Check chain consistency
        latest_count = sum(1 for v in versions if v.version_info.is_latest)
        if latest_count != 1:
            resources_with_issues += 1
            print(f"⚠️  {resource_id}")
            print(f"   Resource type: {versions[0].resource_type.value}")
            print(f"   Total versions: {len(versions)}")
            print(f"   Latest count: {latest_count} (should be 1)")
            print()

    if resources_with_issues == 0:
        print("✅ All resources have exactly one latest version")
    else:
        print(f"⚠️  {resources_with_issues} resources have incorrect latest version counts")

    print()
    print("=" * 80)
    print("HEALTH CHECK COMPLETE")
    print("=" * 80)

    client.close()


if __name__ == "__main__":
    asyncio.run(check_orphaned_versions())