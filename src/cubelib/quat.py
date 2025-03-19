import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math

# Quaternion class with rotation functionality
class Quaternion:
    def __init__(self, w=1.0, x=0.0, y=0.0, z=0.0):
        self.w = w
        self.x = x
        self.y = y
        self.z = z

    def from_axis_angle(self, axis, angle):
        # Convert axis to unit vector
        axis = np.array(axis, dtype=np.float32)
        axis = axis / np.linalg.norm(axis)

        # Calculate quaternion components
        half_angle = angle / 2.0
        sin_half = math.sin(half_angle)

        self.w = math.cos(half_angle)
        self.x = axis[0] * sin_half
        self.y = axis[1] * sin_half
        self.z = axis[2] * sin_half

        return self

    def normalize(self):
        magnitude = math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        if magnitude > 0:
            self.w /= magnitude
            self.x /= magnitude
            self.y /= magnitude
            self.z /= magnitude
        return self

    def to_rotation_matrix(self):
        # Convert quaternion to 4x4 rotation matrix
        w, x, y, z = self.w, self.x, self.y, self.z

        xx = x * x
        xy = x * y
        xz = x * z
        xw = x * w

        yy = y * y
        yz = y * z
        yw = y * w

        zz = z * z
        zw = z * w

        matrix = np.array([
            [1 - 2 * (yy + zz), 2 * (xy - zw), 2 * (xz + yw), 0],
            [2 * (xy + zw), 1 - 2 * (xx + zz), 2 * (yz - xw), 0],
            [2 * (xz - yw), 2 * (yz + xw), 1 - 2 * (xx + yy), 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        return matrix

    def multiply(self, q2):
        # Quaternion multiplication
        w1, x1, y1, z1 = self.w, self.x, self.y, self.z
        w2, x2, y2, z2 = q2.w, q2.x, q2.y, q2.z

        result = Quaternion(
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
        )

        return result

# Define the vertices of a cube
def cube_vertices():
    vertices = [
        [1, -1, -1],
        [1, 1, -1],
        [-1, 1, -1],
        [-1, -1, -1],
        [1, -1, 1],
        [1, 1, 1],
        [-1, -1, 1],
        [-1, 1, 1]
    ]

    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # Base
        (4, 5), (5, 7), (7, 6), (6, 4),  # Top
        (0, 4), (1, 5), (2, 7), (3, 6)   # Sides
    ]

    surfaces = [
        (0, 1, 2, 3),  # Bottom
        (4, 5, 7, 6),  # Top
        (0, 1, 5, 4),  # Side
        (2, 3, 6, 7),  # Side
        (1, 2, 7, 5),  # Side
        (0, 3, 6, 4)   # Side
    ]

    colors = [
        (1, 0, 0),  # Red
        (0, 1, 0),  # Green
        (0, 0, 1),  # Blue
        (1, 1, 0),  # Yellow
        (1, 0, 1),  # Magenta
        (0, 1, 1)   # Cyan
    ]

    return vertices, edges, surfaces, colors

def draw_cube(vertices, edges, surfaces, colors):
    # Draw surfaces
    glBegin(GL_QUADS)
    for i, surface in enumerate(surfaces):
        color = colors[i]
        glColor3fv(color)
        for vertex in surface:
            glVertex3fv(vertices[vertex])
    glEnd()

    # Draw edges
    glBegin(GL_LINES)
    glColor3f(1, 1, 1)  # White edges
    for edge in edges:
        for vertex in edge:
            glVertex3fv(vertices[vertex])
    glEnd()

def main():
    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)

    # Set up perspective
    gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)
    glTranslatef(0.0, 0.0, -5)

    # Enable depth testing for 3D rendering
    glEnable(GL_DEPTH_TEST)

    # Get cube data
    vertices, edges, surfaces, colors = cube_vertices()

    # Create quaternions for rotation around different axes
    quat_x = Quaternion().from_axis_angle([1, 0, 0], 0)  # X-axis
    quat_y = Quaternion().from_axis_angle([0, 1, 0], 0)  # Y-axis
    quat_z = Quaternion().from_axis_angle([0, 0, 1], 0)  # Z-axis

    # Set rotation speeds (radians per frame)
    x_speed = 0.005
    y_speed = 0.007
    z_speed = 0.003
    x_angle = 0
    y_angle = 0
    z_angle = 0
    clock = pygame.time.Clock()
    dragging = False
    last_mouse_pos = (0,0)
    last_event = (None, None)

    while True:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            if event.type == pygame.MOUSEBUTTONDOWN:
                dragging = True
                last_mouse_pos = pygame.mouse.get_pos()
                print(f"Dragging from : {last_mouse_pos}")

            if event.type == pygame.MOUSEBUTTONUP:
                dragging = False
                print("Stopped dragging")

            if event.type == pygame.MOUSEMOTION:
                if dragging:
                    current_mouse_pos = pygame.mouse.get_pos()
                    print(f"Dragging to : {current_mouse_pos}")
                    dx = current_mouse_pos[0] - last_mouse_pos[0]
                    dy = current_mouse_pos[1] - last_mouse_pos[1]
                    y_angle += dx * x_speed
                    z_angle += dy * x_speed
                    print(f"x_angle: {x_angle}, y_angle: {y_angle}, z_angle: {z_angle}")
                    # quat_x.from_axis_ angle([1, 0, 0], x_angle)
                    # quat_y.from_axis_angle([0, 1, 0], y_angle)
                    # quat_z.from_axis_angle([0, 0, 1], z_angle)
                    # x_angle += x_speed
                    # y_angle += y_speed
                    # z_angle += z_speed
                    last_mouse_pos = current_mouse_pos


        # Update rotation quaternions
        # quat_x.from_axis_angle([1, 0, 0], x_angle)
        # quat_y.from_axis_angle([0, 1, 0], y_angle)
        # quat_z.from_axis_angle([0, 0, 1], z_angle)
        # x_angle += x_speed
        # y_angle += y_speed
        # z_angle += z_speed

        # Combine rotations (order matters in quaternion multiplication)
        combined_quat = quat_x.multiply(quat_y).multiply(quat_z)

        # Get rotation matrix
        rotation_matrix = combined_quat.to_rotation_matrix()

        # Clear screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Apply rotation
        glPushMatrix()
        glMultMatrixf(rotation_matrix)

        # Draw the cube
        draw_cube(vertices, edges, surfaces, colors)

        glPopMatrix()

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()