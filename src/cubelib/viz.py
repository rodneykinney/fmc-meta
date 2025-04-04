import sys
import logging
import os

from OpenGL.GL import *
from OpenGL.GLU import *
import math
import numpy as np

import  cubelib.solution_builder
from cubelib.solution_builder import SolutionBuilder
from py_cubelib import (Cube, StepInfo)
import pyquaternion

def _current() -> SolutionBuilder:
    return cubelib.solution_builder._current

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
GREEN = (0, .6, 0)
BLUE = (0, 0, 1)
RED = (1, 0, 0)
# ORANGE = (1, .8, .1)
ORANGE = (1, .37, .2)
GREY = (0.75, 0.75, 0.75)
BACKGROUND = .3

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
            opacity=.8,  # Set the opacity for the colors
    ):
        # Set up the display
        self.display_width = width
        self.display_height = height
        self.opacity = opacity
        #os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'

        # Set up the perspective
        # glMatrixMode(GL_PROJECTION)
        # gluPerspective(45, (self.display_width / self.display_height), 0.1, 50.0)
        #
        # glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # glEnable(GL_BLEND)

        # Initial camera position
        self.camera_x = 0.0
        self.camera_y = -10.0
        self.camera_z = 6.0
        self.xq_angle = 0
        self.yq_angle = 0
        self.zq_angle = 0
        self.view_angle = -math.pi / 6

        self.hide_corners = False
        self.hide_edges = False
        self.show_all = False

        self.scramble = ""
        self.cube = Cube("")
        self.inverse = False
        self.colors = [(1, 1, 1, .2)] * 54

    def initializeGL(self, width, height):
        """Initialize OpenGL settings"""
        glClearColor(BACKGROUND, BACKGROUND, BACKGROUND, 1)
        glEnable(GL_DEPTH_TEST)

        # Enable alpha blending
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)

        # Set up the perspective
        self.resize(width, height)


    def resize(self, width, height):
        """Handle widget resize events"""
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(25, (width / height), 0.1, 50.0)


    def set_scramble(self, scramble: str):
        logging.debug(f"Setting scramble to {scramble}")
        self.scramble = scramble
        self.cube = Cube(self.scramble)
        self.refresh()

    def should_draw_edge(self, pos_id, face):
        if self.show_all:
            return True
        if self.hide_edges:
            return False
        return _current().step_info.should_draw_edge(self.cube, pos_id, face)

    def should_draw_corner(self, pos_id, face):
        if self.show_all:
            return True
        if self.hide_corners:
            return False
        return _current().step_info.should_draw_corner(self.cube, pos_id, face)

    def refresh(self):
        self.colors = [(1, 1, 1, .2)] * 54
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
                if not self.should_draw_corner(i, side):
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
                if not self.should_draw_edge(i, side):
                    continue
                self.colors[edge_position_facelets[i][side]] = edge_piece_colors[edges[i][0]][
                                                                   (side + flipped) % 2] + (
                                                                   self.opacity,)


    def draw_facelet(self, x, y, z, color, axis):
        glPushMatrix()
        glTranslatef(x, y, z)
        draw_grid = False

        # Draw a square face
        glBegin(GL_QUADS)
        if axis == 'xy':
            if draw_grid:
                glColor4f(0, 0, 0, color[3])
                glVertex3f(-0.5, -0.5, 0.0)
                glVertex3f(0.5, -0.5, 0.0)
                glVertex3f(0.5, 0.5, 0.0)
                glVertex3f(-0.5, 0.5, 0.0)
            glColor4fv(color)
            glVertex3f(-0.48, -0.48, 0.0)
            glVertex3f(0.48, -0.48, 0.0)
            glVertex3f(0.48, 0.48, 0.0)
            glVertex3f(-0.48, 0.48, 0.0)
        elif axis == 'xz':
            if draw_grid:
                glColor4f(0, 0, 0, color[3])
                glVertex3f(-0.5, 0.0, -0.5)
                glVertex3f(0.5, 0.0, -0.5)
                glVertex3f(0.5, 0.0, 0.5)
                glVertex3f(-0.5, 0.0, 0.5)
            glColor4fv(color)
            glVertex3f(-0.48, 0.0, -0.48)
            glVertex3f(0.48, 0.0, -0.48)
            glVertex3f(0.48, 0.0, 0.48)
            glVertex3f(-0.48, 0.0, 0.48)
        elif axis == 'yz':
            if draw_grid:
                glColor4f(0, 0, 0, color[3])
                glVertex3f(0.0, -0.5, -0.5)
                glVertex3f(0.0, 0.5, -0.5)
                glVertex3f(0.0, 0.5, 0.5)
                glVertex3f(0.0, -0.5, 0.5)
            glColor4fv(color)
            glVertex3f(0.0, -0.48, -0.48)
            glVertex3f(0.0, 0.48, -0.48)
            glVertex3f(0.0, 0.48, 0.48)
            glVertex3f(0.0, -0.48, 0.48)
        glEnd()

        glPopMatrix()

    def set_inverse(self, inverse: bool):
        self.inverse = inverse

    def update(self):
        self.cube = Cube(self.scramble)
        self.cube.apply(_current().full_alg())
        if self.inverse:
            self.cube.invert()
        self.refresh()

    def draw(self):
        # Clear the screen
        glClearColor(BACKGROUND, BACKGROUND, BACKGROUND, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set camera position
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.camera_x, self.camera_y, self.camera_z,  # Camera position
                  0, 0, 0,  # Look at point
                  0, 1, 0)  # Up vector

        # Apply rotation
        qx = pyquaternion.Quaternion(axis=[1, 0, 0], angle=self.xq_angle)
        qy = pyquaternion.Quaternion(axis=[0, 1, 0], angle=self.yq_angle)
        qz = pyquaternion.Quaternion(axis=[0, 0, 1], angle=self.zq_angle)
        qview = pyquaternion.Quaternion(axis=[0, 0, 1], angle=self.view_angle)
        q = qview * qz * qx * qy
        rotation_matrix = q.rotation_matrix

        # Order faces from back to front
        def distance(i):
            v_rotated = q.rotate([facelet_x[i], facelet_y[i], facelet_z[i]])
            return (v_rotated[0] - self.camera_x) ** 2 + \
                (v_rotated[1] - self.camera_y) ** 2 + \
                (v_rotated[2] - self.camera_z) ** 2

        faces = [
            (range(9 * i, 9 * (i + 1)), distance(9 * i + 4)) for i in range(0, 6)
        ]
        faces.sort(key=lambda x: -x[1])
        faces = [f for f, d in faces]

        # Update the GL matrix with the new rotation
        m = np.identity(4)
        m[:3, :3] = rotation_matrix

        # Convert to OpenGL format (column-major) and apply
        glPushMatrix()
        glMultMatrixf(m.T.flatten())

        for face in faces:
            for i in face:
                self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                                  self.colors[i], axis[i])

        glPopMatrix()

    def rotate(self, dx, dy=0):
        self.view_angle += dx * .005

    def set_orientation(self, x, y, z):
        """Set the cube orientation angles"""
        self.xq_angle = x
        self.yq_angle = y
        self.zq_angle = z

