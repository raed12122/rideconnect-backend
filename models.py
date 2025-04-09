import psycopg2

# Reusable function to connect to the database
def get_db_connection():
    return psycopg2.connect(
        dbname="raedaldakheel",
        user="postgres",
        password="your_password",  # Replace with your actual password
        host="localhost",
        port="5432"
    )

# Insert a new ride request into the database
def insert_ride_request(data):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("BEGIN;")

    cur.execute("""
        INSERT INTO RideRequests (
            rider_id, pickup_lat, pickup_lng, dropoff_lat, dropoff_lng,
            category_name, price_multiplier, surge_multiplier, surge_id,
            estimated_duration, estimated_arrival_time, base_fare, total_fare,
            status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'requested')
        RETURNING ride_id;
    """, (
        data["rider_id"],
        data["pickup_lat"],
        data["pickup_lng"],
        data["dropoff_lat"],
        data["dropoff_lng"],
        data["category_name"],
        data["price_multiplier"],
        data["surge_multiplier"],
        data["surge_id"],
        data["estimated_duration"],
        data["estimated_arrival_time"],
        data["base_fare"],
        data["total_fare"]
    ))

    ride_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return ride_id

# Accept and assign a driver to a ride
def accept_ride_transaction(ride_id, driver_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("BEGIN;")

    cur.execute("""
        SELECT status FROM RideRequests
        WHERE ride_id = %s
        FOR UPDATE;
    """, (ride_id,))
    result = cur.fetchone()

    if not result:
        return "not_found"

    if result[0] != "requested":
        return "unavailable"

    cur.execute("""
        UPDATE RideRequests
        SET status = 'accepted', driver_id = %s
        WHERE ride_id = %s;
    """, (driver_id, ride_id))

    conn.commit()
    cur.close()
    conn.close()
    return "success"