from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, ParkingLot, ParkingSpot, Reservation
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_admin_user():
    """Create default admin user if doesn't exist"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@parking.com',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created - Username: admin, Password: admin123")


# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(username=username, email=email, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))
    
    parking_lots = ParkingLot.query.all()
    total_spots = sum(lot.maximum_number_of_spots for lot in parking_lots)
    occupied_spots = sum(lot.occupied_spots for lot in parking_lots)
    available_spots = total_spots - occupied_spots
    total_users = User.query.filter_by(is_admin=False).count()
    
    # Chart data
    lot_data = []
    for lot in parking_lots:
        lot_data.append({
            'name': lot.prime_location_name,
            'total': lot.maximum_number_of_spots,
            'occupied': lot.occupied_spots,
            'available': lot.available_spots
        })
    
    return render_template('admin/dashboard.html', 
                         parking_lots=parking_lots,
                         total_spots=total_spots,
                         occupied_spots=occupied_spots,
                         available_spots=available_spots,
                         total_users=total_users,
                         lot_data=lot_data)

@app.route('/admin/create_lot', methods=['GET', 'POST'])
@login_required
def create_lot():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        prime_location_name = request.form['prime_location_name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price_per_hour = float(request.form['price_per_hour'])
        maximum_number_of_spots = int(request.form['maximum_number_of_spots'])
        
        # Create parking lot
        lot = ParkingLot(
            prime_location_name=prime_location_name,
            address=address,
            pin_code=pin_code,
            price_per_hour=price_per_hour,
            maximum_number_of_spots=maximum_number_of_spots
        )
        db.session.add(lot)
        db.session.flush()  # Get the lot ID
        
        # Create parking spots
        for i in range(1, maximum_number_of_spots + 1):
            spot = ParkingSpot(
                lot_id=lot.id,
                spot_number=f"S{i:03d}"
            )
            db.session.add(spot)
        
        db.session.commit()
        flash(f'Parking lot "{prime_location_name}" created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/create_lot.html')

@app.route('/admin/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def edit_lot(lot_id):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))
    
    lot = ParkingLot.query.get_or_404(lot_id)
    
    if request.method == 'POST':
        lot.prime_location_name = request.form['prime_location_name']
        lot.address = request.form['address']
        lot.pin_code = request.form['pin_code']
        lot.price_per_hour = float(request.form['price_per_hour'])
        new_max_spots = int(request.form['maximum_number_of_spots'])
        
        current_spots = len(lot.parking_spots)
        
        if new_max_spots > current_spots:
            # Add new spots
            for i in range(current_spots + 1, new_max_spots + 1):
                spot = ParkingSpot(
                    lot_id=lot.id,
                    spot_number=f"S{i:03d}"
                )
                db.session.add(spot)
        elif new_max_spots < current_spots:
            # Remove spots (only if they're available)
            spots_to_remove = ParkingSpot.query.filter_by(
                lot_id=lot.id, status='A'
            ).order_by(ParkingSpot.id.desc()).limit(current_spots - new_max_spots).all()
            
            if len(spots_to_remove) < (current_spots - new_max_spots):
                flash('Cannot reduce spots: Some spots are currently occupied', 'error')
                return render_template('admin/edit_lot.html', lot=lot)
            
            for spot in spots_to_remove:
                db.session.delete(spot)
        
        lot.maximum_number_of_spots = new_max_spots
        db.session.commit()
        flash('Parking lot updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_lot.html', lot=lot)

@app.route('/admin/delete_lot/<int:lot_id>')
@login_required
def delete_lot(lot_id):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))
    
    lot = ParkingLot.query.get_or_404(lot_id)
    
    # Check if all spots are empty
    if lot.occupied_spots > 0:
        flash('Cannot delete lot: Some parking spots are occupied', 'error')
        return redirect(url_for('admin_dashboard'))
    
    db.session.delete(lot)
    db.session.commit()
    flash(f'Parking lot "{lot.prime_location_name}" deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))
    
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin/users.html', users=users)

# User Routes
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    parking_lots = ParkingLot.query.all()
    active_reservation = Reservation.query.filter_by(
        user_id=current_user.id, 
        is_active=True,
        leaving_timestamp=None
    ).first()
    
    # User's booking history
    past_bookings = Reservation.query.filter_by(
        user_id=current_user.id
    ).order_by(Reservation.parking_timestamp.desc()).limit(5).all()
    
    return render_template('user/dashboard.html', 
                         parking_lots=parking_lots,
                         active_reservation=active_reservation,
                         past_bookings=past_bookings)

@app.route('/user/book_parking/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def book_parking(lot_id):
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    lot = ParkingLot.query.get_or_404(lot_id)
    
    # Check if user already has an active booking
    active_booking = Reservation.query.filter_by(
        user_id=current_user.id, 
        leaving_timestamp=None
    ).first()
    
    if active_booking:
        flash('You already have an active parking reservation', 'error')
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        vehicle_number = request.form['vehicle_number']
        
        # Find first available spot
        available_spot = ParkingSpot.query.filter_by(
            lot_id=lot.id, 
            status='A'
        ).first()
        
        if not available_spot:
            flash('No available spots in this parking lot', 'error')
            return redirect(url_for('user_dashboard'))
        
        # Create reservation
        reservation = Reservation(
            spot_id=available_spot.id,
            user_id=current_user.id,
            vehicle_number=vehicle_number
        )
        
        # Update spot status
        available_spot.status = 'O'
        
        db.session.add(reservation)
        db.session.commit()
        
        flash(f'Parking spot {available_spot.spot_number} booked successfully!', 'success')
        return redirect(url_for('user_dashboard'))
    
    return render_template('user/book_parking.html', lot=lot)

@app.route('/user/release_parking/<int:reservation_id>')
@login_required
def release_parking(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    if reservation.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('user_dashboard'))
    
    if reservation.leaving_timestamp:
        flash('Parking already released', 'error')
        return redirect(url_for('user_dashboard'))
    
    # Update reservation
    reservation.leaving_timestamp = datetime.utcnow()
    reservation.is_active = False
    reservation.calculate_cost()
    
    # Update spot status
    reservation.parking_spot.status = 'A'
    
    db.session.commit()
    
    flash(f'Parking released. Total cost: ₹{reservation.parking_cost:.2f}', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/my_bookings')
@login_required
def my_bookings():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    bookings = Reservation.query.filter_by(
        user_id=current_user.id
    ).order_by(Reservation.parking_timestamp.desc()).all()
    
    return render_template('user/my_bookings.html', bookings=bookings)

# API Routes (Optional)
@app.route('/api/parking_lots')
def api_parking_lots():
    lots = ParkingLot.query.all()
    return jsonify([{
        'id': lot.id,
        'name': lot.prime_location_name,
        'address': lot.address,
        'price_per_hour': lot.price_per_hour,
        'total_spots': lot.maximum_number_of_spots,
        'available_spots': lot.available_spots,
        'occupied_spots': lot.occupied_spots
    } for lot in lots])

@app.route('/api/parking_spot/<int:spot_id>')
def api_parking_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    data = {
        'id': spot.id,
        'spot_number': spot.spot_number,
        'status': spot.status,
        'lot_name': spot.parking_lot.prime_location_name
    }
    
    if spot.status == 'O' and spot.current_reservation:
        reservation = spot.current_reservation
        data['reservation'] = {
            'vehicle_number': reservation.vehicle_number,
            'user': reservation.user.username,
            'parking_time': reservation.parking_timestamp.isoformat()
        }
    
    return jsonify(data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_user()
    app.run(debug=True)