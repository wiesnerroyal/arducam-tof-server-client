import sys
import socket
import pickle
import ArducamDepthCamera as ac

IP = ""
PORT = 1234
RANGE2M = 2  # in Meters
RANGE4M = 4
DELIMITER = b"\x00\x00\xFF\xFF\x00\xFF"

def cam_init(cam, range_setting=RANGE2M):
    try:
        print("Initializing camera...")
        if cam.open(ac.TOFConnect.CSI, 0) != 0:
            raise RuntimeError("Camera initialization failed")
        if cam.start(ac.TOFOutput.DEPTH) != 0:
            raise RuntimeError("Failed to start camera")
        cam.setControl(ac.TOFControl.RANG, range_setting)
        print("Camera initialized ✓")
        return cam
    except Exception as e:
        print(e)
        sys.exit(1)

def cam_close(cam):
    cam.stop()
    cam.close()

def handle_client(conn, cam):
    try:
        while True:
            data = conn.recv(4096).decode("utf8")
            if data:
                if "GET_IMG" in data:
                    frame = cam.requestFrame(200)
                    depth_buf = frame.getDepthData()
                    amplitude_buf = frame.getAmplitudeData()
                    cam.releaseFrame(frame)
                    conn.sendall(pickle.dumps([depth_buf, amplitude_buf]) + DELIMITER)
            else:
                break
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        conn.close()

def server_init(ip, port, cam):
    print("Starting server...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ip, port))
        s.listen(1)
        print("Waiting for connections...")

        while True:
            conn, addr = s.accept()
            print(f"Connected by {addr}")
            handle_client(conn, cam)

if __name__ == "__main__":
    cam = cam_init(ac.ArducamCamera())
    try:
        server_init(IP, PORT, cam)
    except KeyboardInterrupt:
        print("Server shutdown requested by user.")
    finally:
        cam_close(cam)
        print("Camera closed.")