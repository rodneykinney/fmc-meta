import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import py_cubelib

# U + L + F + R + B + D
facelet_x = \
    [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5] \
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [1, 0, -1, 1, 0, -1, 1, 0, -1] \
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1]
facelet_y = \
    [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 0, -1, 1, 0, -1, 1, 0, -1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5] \
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [-1, -1, -1, 0, 0, 0, 1, 1, 1]
facelet_z = \
    [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [1, 1, 1, 0, 0, 0, -1, -1, -1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5]

axis = ["xy"] * 9 \
       + ["yz"] * 9 \
       + ["xz"] * 9 \
       + ["yz"] * 9 \
       + ["xz"] * 9 \
       + ["xy"] * 9

WHITE = (1, 1, 1)
YELLOW = (1, 1, 0)
GREEN = (0, .7, 0)
BLUE = (0, 0, 1)
RED = (1, 0, 0)
ORANGE = (1, .5, .2)
GREY = (0.75, 0.75, 0.75)

corner_piece_colors = [
    (WHITE, ORANGE, BLUE),
    (WHITE, BLUE, RED),
    (WHITE, RED, GREEN),
    (WHITE, GREEN, ORANGE),
    (YELLOW, ORANGE, GREEN),
    (YELLOW, GREEN, RED),
    (YELLOW, RED, BLUE),
    (YELLOW, BLUE, ORANGE),
]

edge_piece_colors = [
    (WHITE, BLUE),
    (WHITE, RED),
    (WHITE, GREEN),
    (WHITE, ORANGE),
    (GREEN, RED),
    (GREEN, ORANGE),
    (BLUE, RED),
    (BLUE, ORANGE),
    (YELLOW, GREEN),
    (YELLOW, RED),
    (YELLOW, BLUE),
    (YELLOW, ORANGE),
]

corner_position_facelets = [
    (0, 9, 38),  # UBL
    (2, 36, 29),  # UBR
    (8, 27, 20),  # UFR
    (6, 18, 11),  # UFL
    (45, 17, 24),  # DFL
    (47, 26, 33),  # DFR
    (53, 35, 42),  # DBR
    (51, 44, 15),  # DBL
]

edge_position_facelets = [
    (1, 37),  # UB
    (5, 28),  # UR
    (7, 19),  # UF
    (3, 10),  # UL
    (23, 30),  # FR
    (21, 14),  # FL
    (39, 32),  # BR
    (41, 12),  # BL
    (46, 25),  # DF
    (50, 34),  # DR
    (52, 43),  # DB
    (48, 16),  # DL
]

home_slice = [0, 2, 0, 2, 1, 1, 1, 1, 0, 2, 0, 2]  # 0 = M, 1 = E, 2 = S

default_orientation = [
    0,  # Piece is in its home slice
    1,  # E <-> S
    2,  # E <-> M
    4,  # M <-> S
]

class CubeViz():
    """Visualize a cube in 3D space using pygame and OpenGL"""

    def __init__(
            self,
            width=800,
            height=600,
            opacity=1,  # Set the opacity for the colors
    ):
        # Set up the display
        self.display_width = width
        self.display_height = height
        self.opacity = opacity
        pygame.display.set_mode((self.display_width, self.display_height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("")

        # Set up the perspective
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (self.display_width / self.display_height), 0.1, 50.0)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)

        # Initial camera position
        self.camera_x = 0.0
        self.camera_y = -10.0
        self.camera_z = 6.0
        self.z_angle = -30
        self.y_angle = 0

        self.set_cube("U")

    def set_cube(self, setup: str):
        self.cube = py_cubelib.Cube(setup)
        self.set_colors()

    def set_colors(self):
        edges = self.cube.edges
        self.colors = [(0.75, 0.75, 0.75, 0.3)] * 54
        self.colors[4] = WHITE + (self.opacity,)
        self.colors[13] = ORANGE + (self.opacity,)
        self.colors[22] = GREEN + (self.opacity,)
        self.colors[31] = RED + (self.opacity,)
        self.colors[40] = BLUE + (self.opacity,)
        self.colors[49] = YELLOW + (self.opacity,)
        corners = self.cube.corners()
        # for i in range(0, 8):
        #     for side in range(0,3):
        #         self.colors[corner_position_facelets[i][side]] = corner_piece_colors[corners[i][0]][(corners[0][1] + side) % 3] + (self.opacity,)
        edges = self.cube.edges()
        for i in range(0, 12):
            default_orientation = home_slice[edges[i][0]] ^ home_slice[i]
            flipped = 0 if edges[i][1] == default_orientation else 1
            for side in range(0, 2):
                self.colors[edge_position_facelets[i][side]] = edge_piece_colors[edges[i][0]][
                                                                   (side + flipped) % 2] + (
                                                               self.opacity,)

    def draw_facelet(self, x, y, z, color, axis='xy'):
        """Draw a single face of the cube"""

        glPushMatrix()
        glTranslatef(x, y, z)
        glColor4fv(color)

        # Draw a square face
        glBegin(GL_QUADS)
        if axis == 'xy':
            glVertex3f(-0.48, -0.48, 0.0)
            glVertex3f(0.48, -0.48, 0.0)
            glVertex3f(0.48, 0.48, 0.0)
            glVertex3f(-0.48, 0.48, 0.0)
        elif axis == 'xz':
            glVertex3f(-0.48, 0.0, -0.48)
            glVertex3f(0.48, 0.0, -0.48)
            glVertex3f(0.48, 0.0, 0.48)
            glVertex3f(-0.48, 0.0, 0.48)
        elif axis == 'yz':
            glVertex3f(0.0, -0.48, -0.48)
            glVertex3f(0.0, 0.48, -0.48)
            glVertex3f(0.0, 0.48, 0.48)
            glVertex3f(0.0, -0.48, 0.48)
        glEnd()

        glPopMatrix()

    def draw(self):
        # Clear the screen
        glClearColor(.2, .2, .2, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set camera position
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.camera_x, self.camera_y, self.camera_z,  # Camera position
                  0, 0, 0,  # Look at point
                  0, 1, 0)  # Up vector

        glRotatef(self.z_angle, 0, 0, 1)
        glRotatef(self.y_angle, 0, 1, 0)

        """Draw facelets from back to front"""
        # D
        for i in range(45, 54):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i], axis[i])
        # B
        for i in range(36, 45):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i], axis[i])
        # L
        for i in range(9, 18):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i], axis[i])
        # R
        for i in range(27, 36):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i], axis[i])

        # F
        for i in range(18, 27):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i], axis[i])
        # U
        for i in range(0, 9):
            self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                              self.colors[i], axis[i])

    def rotate(self, z_angle, y_angle=0):
        self.z_angle += z_angle
        self.y_angle += y_angle
        print(f"Rotation angle: {self.z_angle}")

    def move_camera(self, dx, dy, dz):
        """Move the camera position"""
        self.camera_x += dx
        self.camera_y += dy
        self.camera_z += dz
        print(f"Camera position: ({self.camera_x}, {self.camera_y}, {self.camera_z})")


def main():
    # Initialize pygame
    pygame.init()

    viz = CubeViz()
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Camera position controls
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    # viz.move_camera(0, 0, 2)
                    viz.rotate(0, 12)
                if event.key == pygame.K_DOWN:
                    # viz.move_camera(0, 0, -2)
                    viz.rotate(0, -12)
                if event.key == pygame.K_LEFT:
                    viz.rotate(-12, 0)
                if event.key == pygame.K_RIGHT:
                    viz.rotate(12, 0)

        viz.draw()

        # Update the display
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
