import os
import socket
import time
import threading
import json

# Server info
SERVER = os.environ.get("SERVER", '127.0.0.1')
PORT = os.environ.get("PORT", 8888)
host = socket.gethostname()

# Variables
connection_count = 0
connection_reset_count = 0
message_count = 0
client_socket = None
server_unavailable_count = 0

def establish_connection():
    global client_socket, connection_count, connection_reset_count, server_unavailable_count

    while True:
        try:
            # Create a socket and connect to the server if not already connected
            if client_socket is None:
                print(f"Attempting to establish socket connection to {SERVER}:{PORT}")
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((SERVER, PORT))
                connection_count += 1

        except KeyboardInterrupt:
            print("Client interrupted.")
            break
        except TimeoutError:
            print("Socket connection timed out")
            time.sleep(1)
        except ConnectionResetError:
            print(f"Connection reset ({connection_reset_count}). Restablishing connection...")
            connection_reset_count += 1
            client_socket = None
            time.sleep(1)  # Wait for 1 seconds before attempting to reconnect
        except ConnectionRefusedError:
            print(f"Connection refused by server, retrying in 1s. (Attempt {server_unavailable_count})...")
            server_unavailable_count += 1
            client_socket = None
            time.sleep(1)  # Wait for 1 seconds before attempting to reconnect

def send_heartbeat():
    global message_count, client_socket, connection_reset_count, server_unavailable_count

    while True:
        try:
            if client_socket is not None:
                # Increment the message count
                message_count += 1

                # Append message ID and connection count to the heartbeat message
                heartbeat_message = dict(
                    host=host,
                    heartbeat_id=message_count,
                    connection=connection_count,
                    server_unavailable=server_unavailable_count,
                    connection_resets=connection_reset_count
                )
                j = json.dumps(heartbeat_message)
                client_socket.send(j.encode())
                print(f"Sent: {j}")

                #Message successfully sent, reset failure counters
                connection_reset_count = 0
                server_unavailable_count = 0

        except KeyboardInterrupt:
            disconnect = {"disconnect":"true"}
            j = json.dumps(disconnect)
            client_socket.send(j.encode())
            print("Client interrupted, sending disconnect & exit.")
            break
        except BrokenPipeError:
            client_socket = None
            pass
        except Exception as e:
            print(f"Error: {e}")

        # Sleep for 1 second before sending the next heartbeat or retrying
        time.sleep(1)

# Start a thread to send heartbeats
heartbeat_thread = threading.Thread(target=send_heartbeat)
heartbeat_thread.start()

# Start managing connection on main thread.
establish_connection()

try:
    heartbeat_thread.join()  # Wait for the heartbeat thread to finish

except KeyboardInterrupt:
    print("Client interrupted.")

finally:
    if client_socket is not None:
        client_socket.close()
