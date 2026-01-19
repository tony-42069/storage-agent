#!/usr/bin/env python
"""Database seeding script for initial data population.

Usage:
    python scripts/seed_database.py [--reset] [--dry-run]

Options:
    --reset: Drop and recreate all tables before seeding
    --dry-run: Show what would be done without making changes
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from datetime import datetime
from sqlalchemy import text

from src.core.config import get_settings
from src.db.session import get_sync_engine, get_sync_session, init_database
from src.utils.logger import get_logger

logger = get_logger(__name__)


def seed_facilities(session, dry_run: bool = False) -> int:
    """Seed facilities table."""
    facilities = [
        {
            'name': 'Storage Plus Downtown',
            'address': '123 Main Street',
            'city': 'Springfield',
            'state': 'IL',
            'zip_code': '62701',
            'phone': '555-0101',
            'email': 'downtown@storageplus.com',
            'hours': {
                'monday': {'open': '08:00', 'close': '20:00'},
                'tuesday': {'open': '08:00', 'close': '20:00'},
                'wednesday': {'open': '08:00', 'close': '20:00'},
                'thursday': {'open': '08:00', 'close': '20:00'},
                'friday': {'open': '08:00', 'close': '20:00'},
                'saturday': {'open': '09:00', 'close': '18:00'},
                'sunday': {'open': '09:00', 'close': '17:00'},
            },
            'amenities': ['24/7 Access', 'Security Cameras', 'Electronic Gate', 'Lighting'],
            'latitude': 39.7817,
            'longitude': -89.6501,
        },
        {
            'name': 'Storage Plus West',
            'address': '456 Oak Avenue',
            'city': 'Springfield',
            'state': 'IL',
            'zip_code': '62704',
            'phone': '555-0102',
            'email': 'west@storageplus.com',
            'hours': {
                'monday': {'open': '09:00', 'close': '18:00'},
                'tuesday': {'open': '09:00', 'close': '18:00'},
                'wednesday': {'open': '09:00', 'close': '18:00'},
                'thursday': {'open': '09:00', 'close': '18:00'},
                'friday': {'open': '09:00', 'close': '18:00'},
                'saturday': {'open': '10:00', 'close': '16:00'},
                'sunday': {'open': 'closed', 'close': 'closed'},
            },
            'amenities': ['Climate Control', 'Security Cameras', 'Loading Dock', 'Dollies'],
            'latitude': 39.7920,
            'longitude': -89.7100,
        },
    ]
    
    if dry_run:
        logger.info(f"[DRY RUN] Would seed {len(facilities)} facilities")
        return 0
    
    for facility in facilities:
        result = session.execute(
            text("""
                INSERT INTO facilities (name, address, city, state, zip_code, phone, email, hours, amenities, latitude, longitude)
                VALUES (:name, :address, :city, :state, :zip_code, :phone, :email, :hours, :amenities, :latitude, :longitude)
                RETURNING id
            """),
            facility
        )
        facility_id = result.scalar()
        logger.info(f"Created facility: {facility['name']} (ID: {facility_id})")
    
    return len(facilities)


def seed_units(session, facility_id: int, dry_run: bool = False) -> int:
    """Seed units table for a facility."""
    units = [
        {'unit_id': 'A101', 'size': '5x5', 'square_feet': 25, 'floor': 1, 'price': 49.99, 'climate_controlled': False, 'available': True, 'features': ['Ground Floor', 'Drive Up']},
        {'unit_id': 'A102', 'size': '5x5', 'square_feet': 25, 'floor': 1, 'price': 49.99, 'climate_controlled': False, 'available': True, 'features': ['Ground Floor', 'Drive Up']},
        {'unit_id': 'A103', 'size': '5x10', 'square_feet': 50, 'floor': 1, 'price': 79.99, 'climate_controlled': False, 'available': True, 'features': ['Ground Floor', 'Drive Up']},
        {'unit_id': 'B201', 'size': '10x10', 'square_feet': 100, 'floor': 2, 'price': 129.99, 'climate_controlled': True, 'available': True, 'features': ['Climate Control', 'Indoor Access']},
        {'unit_id': 'B202', 'size': '10x10', 'square_feet': 100, 'floor': 2, 'price': 129.99, 'climate_controlled': True, 'available': True, 'features': ['Climate Control', 'Indoor Access']},
        {'unit_id': 'B203', 'size': '10x10', 'square_feet': 100, 'floor': 2, 'price': 129.99, 'climate_controlled': True, 'available': False, 'features': ['Climate Control', 'Indoor Access']},
        {'unit_id': 'B204', 'size': '10x15', 'square_feet': 150, 'floor': 2, 'price': 179.99, 'climate_controlled': True, 'available': True, 'features': ['Climate Control', 'Indoor Access', 'Large Door']},
        {'unit_id': 'C301', 'size': '10x20', 'square_feet': 200, 'floor': 3, 'price': 249.99, 'climate_controlled': True, 'available': True, 'features': ['Climate Control', 'Indoor Access', 'Vehicle Storage']},
        {'unit_id': 'C302', 'size': '10x20', 'square_feet': 200, 'floor': 3, 'price': 249.99, 'climate_controlled': True, 'available': True, 'features': ['Climate Control', 'Indoor Access', 'Vehicle Storage']},
        {'unit_id': 'C303', 'size': '10x30', 'square_feet': 300, 'floor': 3, 'price': 349.99, 'climate_controlled': True, 'available': True, 'features': ['Climate Control', 'Indoor Access', 'Vehicle Storage', 'Double Door']},
    ]
    
    if dry_run:
        logger.info(f"[DRY RUN] Would seed {len(units)} units for facility {facility_id}")
        return 0
    
    count = 0
    for unit in units:
        unit['facility_id'] = facility_id
        session.execute(
            text("""
                INSERT INTO units (unit_id, size, square_feet, floor, price, climate_controlled, available, features, facility_id)
                VALUES (:unit_id, :size, :square_feet, :floor, :price, :climate_controlled, :available, :features, :facility_id)
            """),
            unit
        )
        count += 1
        logger.debug(f"Created unit: {unit['unit_id']}")
    
    logger.info(f"Created {count} units for facility {facility_id}")
    return count


def seed_all_facilities(session, dry_run: bool = False) -> dict:
    """Seed all facilities and their units."""
    results = {'facilities': 0, 'units': 0}
    
    facilities = [
        {
            'name': 'Storage Plus Downtown',
            'address': '123 Main Street',
            'city': 'Springfield',
            'state': 'IL',
            'zip_code': '62701',
            'phone': '555-0101',
            'email': 'downtown@storageplus.com',
            'hours': '{"monday": {"open": "08:00", "close": "20:00"}, "tuesday": {"open": "08:00", "close": "20:00"}}',
            'amenities': '["24/7 Access", "Security Cameras"]',
        },
        {
            'name': 'Storage Plus West',
            'address': '456 Oak Avenue',
            'city': 'Springfield',
            'state': 'IL',
            'zip_code': '62704',
            'phone': '555-0102',
            'email': 'west@storageplus.com',
            'hours': '{"monday": {"open": "09:00", "close": "18:00"}}',
            'amenities': '["Climate Control", "Security Cameras"]',
        },
    ]
    
    if dry_run:
        logger.info(f"[DRY RUN] Would seed {len(facilities)} facilities")
        return results
    
    for facility in facilities:
        result = session.execute(
            text("""
                INSERT INTO facilities (name, address, city, state, zip_code, phone, email, hours, amenities)
                VALUES (:name, :address, :city, :state, :zip_code, :phone, :email, :hours, :amenities)
                RETURNING id
            """),
            facility
        )
        facility_id = result.scalar()
        results['facilities'] += 1
        results['units'] += seed_units(session, facility_id, dry_run)
    
    return results


def reset_database(session):
    """Drop all tables and recreate."""
    logger.warning("Dropping all tables...")
    from src.models.base import Base
    Base.metadata.drop_all(session.get_bind())
    logger.info("All tables dropped")
    
    logger.info("Recreating tables...")
    init_database()
    logger.info("Tables recreated")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Seed the database with initial data')
    parser.add_argument('--reset', action='store_true', help='Drop and recreate tables')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    args = parser.parse_args()
    
    settings = get_settings()
    logger.info(f"Database seeding started (environment: {settings.APP_ENV})")
    
    engine = get_sync_engine()
    session = get_sync_session()
    
    try:
        if args.reset:
            reset_database(session)
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
        
        results = seed_all_facilities(session, args.dry_run)
        
        if not args.dry_run:
            session.commit()
            logger.info("Database seeding completed successfully!")
        
        logger.info(f"Summary: {results['facilities']} facilities, {results['units']} units")
        
    except Exception as e:
        session.rollback()
        logger.error(f"Database seeding failed: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
