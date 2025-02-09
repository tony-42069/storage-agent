"""Seed initial data

Revision ID: 20250208_1907
Revises: 108b65ea7fda
Create Date: 2025-02-08 19:07:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '20250208_1907'
down_revision = '108b65ea7fda'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create initial facility
    op.execute("""
        INSERT INTO facilities (name, address, city, state, zip_code, phone, email, hours, amenities)
        VALUES (
            'Storage Plus',
            '123 Storage Lane',
            'Springfield',
            'IL',
            '62701',
            '555-0123',
            'info@storageplus.com',
            '{"monday": {"open": "09:00", "close": "18:00"}, 
              "tuesday": {"open": "09:00", "close": "18:00"},
              "wednesday": {"open": "09:00", "close": "18:00"},
              "thursday": {"open": "09:00", "close": "18:00"},
              "friday": {"open": "09:00", "close": "18:00"},
              "saturday": {"open": "10:00", "close": "16:00"},
              "sunday": {"open": "10:00", "close": "16:00"}}',
            '["24/7 Access", "Security Cameras", "Climate Control"]'
        )
        RETURNING id;
    """)

    # Create initial units
    op.execute("""
        INSERT INTO units (unit_id, size, square_feet, floor, price, climate_controlled, available, features, facility_id)
        VALUES 
        ('A101', '5x5', 25, 1, 49.99, false, true, ARRAY['Ground Floor', 'Drive Up'], 1),
        ('B202', '10x10', 100, 2, 149.99, true, true, ARRAY['Climate Control', 'Indoor Access'], 1),
        ('C303', '10x15', 150, 3, 199.99, true, true, ARRAY['Climate Control', 'Indoor Access', 'Large Door'], 1);
    """)

def downgrade() -> None:
    op.execute("DELETE FROM units")
    op.execute("DELETE FROM facilities")
