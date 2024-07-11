import cv2
import sys
import time
import socket
import pickle
import numpy as np
import pyvista as pv

# Server configuration
IP = "raspberrypi.local"
PORT = 1234
DELIMITER = b"\x00\x00\xFF\xFF\x00\xFF"
GET_IMGES = "GET_IMG"
IMG_WIDTH = 240
IMG_HEIGHT = 180

fx = IMG_WIDTH / (2 * np.tan(0.5 * np.pi * 64.3 / 180))
fy = IMG_HEIGHT / (2 * np.tan(0.5 * np.pi * 50.4 / 180))

# Initialize the client socket
def client_init(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        return s
    except socket.error as e:
        print(f"Socket error: {e}")
        sys.exit(1)

# Close the client socket
def client_close(s):
    s.close()

# Transmit message to server and receive data
def client_transmit(s, msg):
    try:
        s.send(msg.encode("utf8"))
        data = bytearray()
        while True:
            chunk = s.recv(4096)
            if DELIMITER in chunk:
                data.extend(chunk.split(DELIMITER)[0])
                break
            data.extend(chunk)

        images = pickle.loads(data)
        return images
    except Exception as e:
        print(f"Transmission error: {e}")
        return None

# Generate point cloud from depth and amplitude images
def get_cloud(depth_img, amplitude_img):
    col_indices, row_indices = np.meshgrid(np.arange(IMG_WIDTH), np.arange(IMG_HEIGHT))
    valid_mask = amplitude_img > 30

    zz = depth_img[valid_mask]
    xx = ((120 - col_indices[valid_mask]) / fx) * zz
    yy = ((90 - row_indices[valid_mask]) / fy) * zz

    points = np.column_stack((xx, yy, zz))
    point_cloud = pv.PolyData(points)
    point_cloud.point_data['z'] = points[:, 2]
    return point_cloud

# Initialize the plotter
def plotter_init():
    p = pv.Plotter(off_screen=True)
    p.set_background("black")
    p.camera_position = (-2.0, 0.0, -2.0)
    p.camera.view_angle = 30
    p.camera.focal_point = (-0.7, -0.05, 0.6)
    p.camera.roll = -1
    return p

if __name__ == "__main__":
    s = client_init(IP, PORT)
    p = plotter_init()

    while True:
        start_time = time.time()

        images = client_transmit(s, GET_IMGES)
        if images is None:
            break

        point_cloud = get_cloud(images[0], images[1])

        p.clear()
        p.add_mesh(
            point_cloud, 
            scalars="z", 
            cmap="viridis", 
            point_size=1.0,
            render_points_as_spheres=True,
            scalar_bar_args={
                "title": "Z-Value\r\n", 
                "color": "white", 
                "title_font_size": 24,
                "label_font_size": 16
            })

        img = p.screenshot(None, return_img=True)
        cv2.imshow('Point Cloud', img)

        if cv2.waitKey(25) & 0xFF == ord('q'):
            break
        if cv2.getWindowProperty('Point Cloud', cv2.WND_PROP_VISIBLE) < 1:
            break

        stop_time = time.time()
        #print(f"FPS: {int(1/(stop_time-start_time))}")
        start_time = stop_time

    p.close()
    client_close(s)
