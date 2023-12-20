import influxdb_client, os, time, socket, threading, json
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN")
INFLUX_HOST = os.environ.get("INFLUX_HOST", "http://localhost:8086")
PORT = int(os.environ.get("PORT", 8888))

# Variables
stop_flag = False
influx_c = influxdb_client.InfluxDBClient(url=INFLUX_HOST, token=INFLUX_TOKEN, org="home")
influx_w = influx_c.write_api(write_options=SYNCHRONOUS)
influx_bucket = "socket_telemetry"

# Function to handle client connections
def handle_client(client_socket):
    global stop_flag

    datapoints = []
    fclient = client_socket.getpeername()[0]

    try:
        while stop_flag == False:
            try:
                # Receive data from the client (heartbeat)
                data = client_socket.recv(1024)
                if not data:
                    datapoints.append(Point("abrupt_exit").tag("host", fclient).field("no_data", 1))
                    break

                # Record the timestamp when the message is received
                current_time = time.time()
                try:
                    msg = data.decode()
                    j = json.loads(msg)

                    if "disconnect" in j:
                        datapoints.append(Point("graceful_disconnect").tag("host",fclient).tag("osname", j['host']))
                        print(f"{fclient} gracefully disconnected.")
                    else:
                        datapoints.append(Point("heartbeat").tag("host",fclient).tag("osname", j['host']).field("count", j['heartbeat_id']))
                        datapoints.append(Point("connection").tag("host",fclient).tag("osname", j['host']).field("count", j['connection']))
                        datapoints.append(Point("server_unavailable").tag("host",fclient).tag("osname", j['host']).field("count", j['server_unavailable']))
                        datapoints.append(Point("connection_reset").tag("host",fclient).tag("osname", j['host']).field("count", j['connection_resets']))
                        print(f"Received message from {fclient}:{fclient} at {current_time}: {data.decode()}")

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f"Error: {e}")

                influx_w.write(bucket=influx_bucket, record=datapoints)
                datapoints.clear

            except ConnectionResetError:
                # Report the result to Influx
                influx_w.write(bucket=influx_bucket, record=Point.tag("host", fclient).field("connection_reset_by_peer", 1))
                print(f"Connection reset by {fclient}:{client_socket.getpeername()[1]}")
                break

    except KeyboardInterrupt:
        print("Client thread interrupted.")
        stop_flag = True

    # Close the client socket when the connection is lost
    client_socket.close()

# Create a socket server
def start_server():
    global stop_flag

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', PORT))
    server.listen(5)
    print("Server listening on port 8888...")

    try:
        while stop_flag == False:
            client_socket, addr = server.accept()
            fclient = addr[0]
            print(f"Accepted connection from {fclient}:{addr[1]}... fclient-{fclient}")
            rec = Point("connection_accepted").tag("host",fclient)
            influx_w.write(bucket=influx_bucket, record=rec)

            # Start a new thread to handle the client connection
            client_handler = threading.Thread(target=handle_client, args=(client_socket,))
            client_handler.start()

    except KeyboardInterrupt:
        print("Server thread interrupted.")
        stop_flag = True

if __name__ == "__main__":
    start_server()
