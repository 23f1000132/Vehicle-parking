from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(15))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reservations = db.relationship('Reservation', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    maximum_number_of_spots = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    parking_spots = db.relationship('ParkingSpot', backref='parking_lot', lazy=True, cascade='all, delete-orphan')
    
    @property
    def available_spots(self):
        return len([spot for spot in self.parking_spots if spot.status == 'A'])
    
    @property
    def occupied_spots(self):
        return len([spot for spot in self.parking_spots if spot.status == 'O'])
    
    def __repr__(self):
        return f'<ParkingLot {self.prime_location_name}>'

class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    spot_number = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(1), default='A')  # A-Available, O-Occupied
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    reservations = db.relationship('Reservation', backref='parking_spot', lazy=True)
    
    @property
    def current_reservation(self):
        return Reservation.query.filter_by(
            spot_id=self.id, 
            leaving_timestamp=None
        ).first()
    
    def __repr__(self):
        return f'<ParkingSpot {self.spot_number}>'

class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vehicle_number = db.Column(db.String(20), nullable=False)
    parking_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    leaving_timestamp = db.Column(db.DateTime)
    parking_cost = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    
    @property
    def duration_hours(self):
        if self.leaving_timestamp:
            duration = self.leaving_timestamp - self.parking_timestamp
            return round(duration.total_seconds() / 3600, 2)
        return 0
    
    def calculate_cost(self):
        if self.leaving_timestamp:
            hours = self.duration_hours
            # Minimum 1 hour charge
            if hours < 1:
                hours = 1
            self.parking_cost = hours * self.parking_spot.parking_lot.price_per_hour
            return self.parking_cost
        return 0
    
    def __repr__(self):
        return f'<Reservation {self.vehicle_number}>'
