import http.server
import json
import mysql.connector

# Total number of tables available in the restaurant
TOTAL_TABLES = 20

class ReservationServer(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        try:
            self.conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='root',
                port=3306,
                database='Res'
            )
            self.cursor = self.conn.cursor()
            self.create_table() # Create table if not exists
        except mysql.connector.Error as err:
            print("Error connecting to MySQL:", err)
        super().__init__(*args, **kwargs)

    def _set_response(self, content_type='application/json'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()

    def create_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS reservations (
                    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
                    customer_name VARCHAR(100) NOT NULL,
                    reservation_date DATE NOT NULL,
                    reservation_time TIME NOT NULL,
                    party_size INT NOT NULL
                )
            """)
            print("Table 'reservations' created successfully.")
        except mysql.connector.Error as err:
            print("Error creating table:", err)

    def do_GET(self):
        if self.path == '/reservations':
            self.cursor.execute("SELECT * FROM reservations")
            reservations = self.cursor.fetchall()
            remaining_tables = TOTAL_TABLES - len(reservations)
        
            # Format date and time fields
            formatted_reservations = []
            for reservation in reservations:
                formatted_reservation = {
                    'reservation_id': reservation[0],
                    'customer_name': reservation[1],
                    'reservation_date': reservation[2].strftime('%Y-%m-%d'),  # Format date
                    'reservation_time': str(reservation[3]),  # Convert time to string
                    'party_size': reservation[4]
                }
                formatted_reservations.append(formatted_reservation)

            response = {
                'reservations': formatted_reservations,
                'remaining_tables': remaining_tables
            }
            self._set_response()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == '/reservations':
            content_len = int(self.headers.get('content-length'))
            post_data = self.rfile.read(content_len)
        
            if self.headers.get('content-type') == 'application/json':
                try:
                    request_data = json.loads(post_data.decode())
                    if 'action' in request_data:
                        if request_data['action'] == 'create':
                            self.create_reservation(request_data)
                        elif request_data['action'] == 'delete':
                            self.cancel_reservation(request_data)
                        else:
                            self.send_response(400)
                            self.end_headers()
                    else:
                        self.send_response(400)
                        self.end_headers()
                except (json.JSONDecodeError, KeyError) as e:
                    self.send_response(400)
                    self.end_headers()
            else:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def create_reservation(self, data):
        try:
            self.cursor.execute("INSERT INTO reservations (customer_name, reservation_date, reservation_time, party_size) VALUES (%s, %s, %s, %s)", (data['customer_name'], data['reservation_date'], data['reservation_time'], data['party_size']))
            self.conn.commit()
            reservation_id = self.cursor.lastrowid  # Get the ID of the last inserted row
            response_data = {
                'reservation_id': reservation_id,
                'customer_name': data['customer_name'],
                'reservation_date': data['reservation_date'],
                'reservation_time': data['reservation_time'],
                'party_size': data['party_size']
            }
            self._set_response()
            self.wfile.write(json.dumps(response_data).encode())
        except mysql.connector.Error as err:
            print("Error creating reservation:", err)
            self.send_response(500)
            self.end_headers()

    def cancel_reservation(self, data):
        try:
            reservation_id = data.get('reservation_id')
            if reservation_id:
                self.cursor.execute("DELETE FROM reservations WHERE reservation_id = %s", (reservation_id,))
                self.conn.commit()
                self._set_response()
                self.wfile.write(json.dumps({'message': 'Reservation cancelled successfully'}).encode())
            else:
                self.send_response(400)
                self.end_headers()
        except mysql.connector.Error as err:
            print("Error cancelling reservation:", err)
            self.send_response(500)
            self.end_headers()

    def __del__(self):
        # Close database connection
        self.cursor.close()
        self.conn.close()

if __name__ == '__main__':
    server_address = ('', 8080)
    httpd = http.server.HTTPServer(server_address, ReservationServer)
    print('Starting server...')
    httpd.serve_forever()
