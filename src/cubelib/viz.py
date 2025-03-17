import sys
import logging
import os

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
from py_cubelib import (Cube, Solution)

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
ORANGE = (1, .4, .3)
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
    5,  # E <-> M
    4,  # M <-> S
    1,  # E <-> S
]


class CubeViz():
    """Visualize a cube in 3D space using pygame and OpenGL"""

    def __init__(
            self,
            scramble="",
            width=800,
            height=600,
            opacity=.9,  # Set the opacity for the colors
    ):
        # Set up the display
        self.display_width = width
        self.display_height = height
        self.opacity = opacity
        os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
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

        self.set_scramble(scramble)

    def set_scramble(self, scramble: str):
        logging.debug(f"Setting scramble to {scramble}")
        self.scramble = scramble
        self.set_solution(Solution())

    def set_cube(self, setup: str):
        logging.debug(f"Setting cube to {setup}")
        self.cube = Cube(setup)
        self.set_colors()

    def set_solution(self, solution: Solution):
        self.cube = Cube(self.scramble)
        self.solution = solution
        self.cube.apply(solution)
        mode = ""
        if self.solution.steps:
            mode = f"{self.solution.steps[-1].kind}{self.solution.steps[-1].variant}"
        self.set_mode(mode)

    def set_mode(self, mode: str):
        logging.debug(f"Setting mode to {mode}")
        if mode == "eofb":
            self.should_draw_edge = self.is_bad_eofb
            self.should_draw_corner = self.do_not_draw
        elif mode == "eorl":
            self.should_draw_edge = self.is_bad_eorl
            self.should_draw_corner = self.do_not_draw
        elif mode == "eoud":
            self.should_draw_edge = self.is_bad_eoud
            self.should_draw_corner = self.do_not_draw
        elif mode == "drud":
            self.should_draw_edge = lambda pos, piece, o, f: o & 3 > 0
            self.should_draw_corner = lambda pos, piece, o, f: o != 0 and o == f
        else:
            self.should_draw_edge = self.do_draw
            self.should_draw_corner = self.do_draw
        self.set_colors()

    def do_draw(self, pos_id, piece_id, orientation, face):
        return True

    def do_not_draw(self, pos_id, piece_id, orientation, face):
        return False

    def is_bad_eofb(self, pos_id, piece_id, orientation, face):
        return orientation & 2 > 0

    def is_bad_eoud(self, pos_id, piece_id, orientation, face):
        return orientation & 4 > 0

    def is_bad_eorl(self, pos_id, piece_id, orientation, face):
        return orientation & 1 > 0

    def set_colors(self):
        self.colors = [(0.75, 0.75, 0.75, 0.3)] * 54
        self.colors[4] = WHITE + (self.opacity,)
        self.colors[13] = ORANGE + (self.opacity,)
        self.colors[22] = GREEN + (self.opacity,)
        self.colors[31] = RED + (self.opacity,)
        self.colors[40] = BLUE + (self.opacity,)
        self.colors[49] = YELLOW + (self.opacity,)
        corners = self.cube.corners()
        for i in range(0, 8):
            piece_id, orientation = corners[i]
            for side in range(0, 3):
                if not self.should_draw_corner(i, piece_id, orientation, side):
                    continue
                face = (side + 3 - orientation) % 3
                self.colors[corner_position_facelets[i][side]] = (
                        corner_piece_colors[piece_id][face] +
                        (self.opacity,))
        edges = self.cube.edges()
        for i in range(0, 12):
            piece_id, piece_orientation = edges[i]
            orientation = default_orientation[home_slice[piece_id] ^ home_slice[i]]
            flipped = 0 if piece_orientation == orientation else 1
            for side in range(0, 2):
                if not self.should_draw_edge(i, piece_id, piece_orientation, side):
                    continue
                self.colors[edge_position_facelets[i][side]] = edge_piece_colors[edges[i][0]][
                                                                   (side + flipped) % 2] + (
                                                                   self.opacity,)

        pygame.display.flip()

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
        glClearColor(.3, .3, .3, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set camera position
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.camera_x, self.camera_y, self.camera_z,  # Camera position
                  0, 0, 0,  # Look at point
                  0, 1, 0)  # Up vector

        glRotatef(self.z_angle, 0, 0, 1)
        # glRotatef(self.y_angle, 0, 1, 0)

        """Order faces from back to front"""

        def distance(i):
            c, s = math.cos(self.z_angle * math.pi / 180), math.sin(self.z_angle * math.pi / 180)
            return ((facelet_x[i] * c - facelet_y[i] * s) - self.camera_x) ** 2 + \
                ((facelet_x[i] * s + facelet_y[i] * c) - self.camera_y) ** 2 + \
                (facelet_z[i] - self.camera_z) ** 2

        faces = [
            (range(9 * i, 9 * (i + 1)), distance(9 * i + 4)) for i in range(0, 6)
        ]
        faces.sort(key=lambda x: -x[1])
        faces = [f for f, d in faces]

        for face in faces:
            for i in face:
                self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                                  self.colors[i], axis[i])
        # Draw text
        if not self.solution.steps:
            return
        pygame.font.init()
        font = pygame.font.SysFont('Arial', 22)

        def write(text, x, y):
            text_surface = font.render(text, True, (255, 255, 255))
            text_data = pygame.image.tostring(text_surface, 'RGBA', True)
            glWindowPos2d(x, y)
            glDrawPixels(text_surface.get_width(), text_surface.get_height(), GL_RGBA,
                         GL_UNSIGNED_BYTE, text_data)
            return text_surface.get_height()

        y = 10
        write(f"{self.solution.steps[-1].kind}{self.solution.steps[-1].variant} - {self.solution.steps[-1].alg}", 10, y)
        for i in range(len(self.solution.steps) - 1, 0, -1):
            y -= write(f"{self.solution.steps[i].alg} // {self.solution.steps[i].kind}{self.solution.steps[i].variant} - ", 10, y)

    def rotate(self, z_angle, y_angle=0):
        self.z_angle += z_angle
        self.y_angle += y_angle

    # def move_camera(self, dx, dy, dz):
    #     """Move the camera position"""
    #     self.camera_x += dx
    #     self.camera_y += dy
    #     self.camera_z += dz

    def stop(self):
        self.running = False

    def run(self):
        # Initialize pygame
        pygame.init()

        clock = pygame.time.Clock()
        self.running = True

        scramble = self.scramble.split(" ")

        modes = ["", "eofb", "eorl", "eoud"]

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                scramble_changed = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        # self.move_camera(0, 0, 2)
                        self.rotate(0, 10)
                    if event.key == pygame.K_DOWN:
                        # self.move_camera(0, 0, -2)
                        self.rotate(0, -10)
                    if event.key == pygame.K_LEFT:
                        self.rotate(-10, 0)
                    if event.key == pygame.K_RIGHT:
                        self.rotate(10, 0)
                    # if event.key in {pygame.K_r, pygame.K_u, pygame.K_f, pygame.K_l, pygame.K_b,
                    #                  pygame.K_d}:
                    #     scramble.append(pygame.key.name(event.key))
                    #     scramble_changed = True
                    # if event.key == pygame.K_QUOTE and scramble:
                    #     scramble[-1] = f"{scramble[-1]}'".replace("''", "").replace("2'", "2")
                    #     scramble_changed = True
                    # if event.key == pygame.K_2 and scramble:
                    #     scramble[-1] = f"{scramble[-1]}2".replace("22", "").replace("'2", "2")
                    #     scramble_changed = True
                    # if event.key == pygame.K_m:
                    #     self.set_mode(modes[(modes.index(self.mode) + 1) % len(modes)])

                if scramble_changed:
                    self.set_cube(" ".join(scramble))
                clock.tick(30)

            self.draw()
            # Update the display
            pygame.display.flip()
        pygame.quit()


if __name__ == "__main__":
    viz = CubeViz()
    viz.set_cube(sys.argv[1])
    viz.run()
