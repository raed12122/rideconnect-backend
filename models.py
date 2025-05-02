import psycopg2


def get_db_connection():
    return psycopg2.connect(
        dbname="335",
        user="raedaldakheel",
        password="2132",
        host="localhost",
        port="5432"
    )

def calculate_distance_km(pickup_lon, pickup_lat, dropoff_lon, dropoff_lat):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ST_DistanceSphere(
            ST_SetSRID(ST_MakePoint(%s, %s), 4326),
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        ) / 1000;
    """, (pickup_lon, pickup_lat, dropoff_lon, dropoff_lat))
    distance_km = cur.fetchone()[0]
    cur.close()
    conn.close()
    return round(distance_km, 2)

def get_active_surge(pickup_lon, pickup_lat):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT SurgeID, Surge_multiplier
        FROM Surge
        WHERE ST_Contains(
            Area,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        )
        AND CURRENT_TIMESTAMP BETWEEN Start_time AND End_time
        ORDER BY Start_time DESC
        LIMIT 1;
    """, (pickup_lon, pickup_lat))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return (result[0], float(result[1])) if result else (None, 1.0)

def find_nearby_drivers(pickup_lon, pickup_lat, limit=3):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DriverID
        FROM Driver
        WHERE Status = 'online'
        AND ST_DistanceSphere(Location, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) <= 5000
        ORDER BY ST_DistanceSphere(Location, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
        LIMIT %s;
    """, (pickup_lon, pickup_lat, pickup_lon, pickup_lat, limit))
    drivers = cur.fetchall()
    cur.close()
    conn.close()
    return [d[0] for d in drivers]

def calculate_eta(driver_id, pickup_lon, pickup_lat):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ST_DistanceSphere(
            Location,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        ) / 1000
        FROM Driver
        WHERE DriverID = %s;
    """, (pickup_lon, pickup_lat, driver_id))
    distance_km = cur.fetchone()[0]
    cur.close()
    conn.close()
    speed_kmh = 40
    return round((distance_km / speed_kmh) * 60, 2)

def insert_ride(data):
    pickup_lon = data["pickup_lon"]
    pickup_lat = data["pickup_lat"]
    dropoff_lon = data["dropoff_lon"]
    dropoff_lat = data["dropoff_lat"]
    category = data["category_name"]
    rider_id = data["rider_id"]

    distance_km = calculate_distance_km(pickup_lon, pickup_lat, dropoff_lon, dropoff_lat)
    estimated_duration = round((distance_km / 40) * 60, 2)

    base_fares = {
        "economy": (10.0, 1.0),
        "premium": (13.0, 1.1),
        "family": (15.0, 1.25)
    }
    base_fare, category_multiplier = base_fares[category]
    surge_id, surge_multiplier = get_active_surge(pickup_lon, pickup_lat)
    estimated_fare = round(base_fare * category_multiplier * surge_multiplier * (distance_km / 5), 2)

    nearby_drivers = find_nearby_drivers(pickup_lon, pickup_lat)
    if not nearby_drivers:
        raise Exception("No drivers available nearby.")
    eta_minutes = calculate_eta(nearby_drivers[0], pickup_lon, pickup_lat)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Ride (
            RiderID, SurgeID, Status, Pickup_location, Dropoff_location,
            Estimated_duration, Estimated_fare, Distance
        )
        VALUES (
            %s, %s, 'requested',
            ST_SetSRID(ST_MakePoint(%s, %s), 4326),
            ST_SetSRID(ST_MakePoint(%s, %s), 4326),
            %s, %s, %s
        )
        RETURNING RideID;
    """, (
        rider_id, surge_id, pickup_lon, pickup_lat, dropoff_lon, dropoff_lat,
        estimated_duration, estimated_fare, distance_km
    ))
    ride_id = cur.fetchone()[0]

    for driver_id in nearby_drivers:
        cur.execute("""
            INSERT INTO Driver_Offer (DriverID, RideID, Status)
            VALUES (%s, %s, 'pending');
        """, (driver_id, ride_id))

    conn.commit()
    cur.close()
    conn.close()

    return {
        "ride_id": ride_id,
        "estimated_duration": estimated_duration,
        "estimated_fare": estimated_fare,
        "estimated_arrival": eta_minutes
    }







def accept_ride(data):
    ride_id = data["ride_id"]
    driver_id = data["driver_id"]

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Start transaction
        cur.execute("BEGIN;")

        # Lock the ride row
        cur.execute("""
            SELECT Status, Pickup_location
            FROM Ride
            WHERE RideID = %s
            FOR UPDATE;
        """, (ride_id,))
        ride = cur.fetchone()

        if not ride:
            return {"error": "Ride not found"}, 404

        status, pickup_point = ride

        if status != 'requested':
            return {"error": "Ride already accepted or unavailable"}, 409

        # Update ride with driver and change status
        cur.execute("""
            UPDATE Ride
            SET Status = 'accepted',
                DriverID = %s,
                Pickup_time = CURRENT_TIMESTAMP
            WHERE RideID = %s;
        """, (driver_id, ride_id))

        # Update driver's status to 'busy'
        cur.execute("""
            UPDATE Driver
            SET Status = 'busy'
            WHERE DriverID = %s;
        """, (driver_id,))

        # Mark other offers as 'declined'
        cur.execute("""
            UPDATE Driver_Offer
            SET Status = 'declined'
            WHERE RideID = %s AND DriverID != %s;
        """, (ride_id, driver_id))

        # Mark this driver's offer as 'accepted'
        cur.execute("""
            UPDATE Driver_Offer
            SET Status = 'accepted',
                Acceptance_time = CURRENT_TIMESTAMP
            WHERE RideID = %s AND DriverID = %s;
        """, (ride_id, driver_id))

        # Get driver location
        cur.execute("""
            SELECT ST_X(Location), ST_Y(Location)
            FROM Driver
            WHERE DriverID = %s;
        """, (driver_id,))
        driver_loc = cur.fetchone()

        # Calculate pickup distance and update offer
        cur.execute("""
            SELECT ST_DistanceSphere(
                ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                %s
            ) / 1000;
        """, (driver_loc[0], driver_loc[1], pickup_point))
        distance_km = cur.fetchone()[0]

        cur.execute("""
            UPDATE Driver_Offer
            SET Distance_to_pickup = %s
            WHERE RideID = %s AND DriverID = %s;
        """, (round(distance_km, 2), ride_id, driver_id))

        # Commit all
        conn.commit()

        return {
            "ride_id": ride_id,
            "driver_id": driver_id,
            "status": "accepted",
            "distance_to_pickup_km": round(distance_km, 2)
        }

    except Exception as e:
        conn.rollback()
        return {"error": str(e)}, 500

    finally:
        cur.close()
        conn.close()