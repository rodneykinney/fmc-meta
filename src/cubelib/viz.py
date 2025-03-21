import sys
import logging
import os

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import numpy as np

from py_cubelib import (Cube, Solution)
import pyquaternion

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
#ORANGE = (1, .8, .1)
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
        os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
        pygame.display.set_mode((self.display_width, self.display_height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("")
        pygame.font.init()

        # Set up the perspective
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (self.display_width / self.display_height), 0.1, 50.0)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)

        # Initial camera position
        self.camera_x = 0.0
        self.camera_y = -10.0
        self.camera_z = 6.0
        self.z_angle = 0
        self.y_angle = 0
        self.xq_angle = XA
        self.yq_angle = 0
        self.zq_angle = ZA

        self.set_scramble(scramble)

    def set_scramble(self, scramble: str):
        logging.debug(f"Setting scramble to {scramble}")
        self.scramble = scramble
        self.set_solution(Solution())

    def set_solution(self, solution: Solution):
        self.cube = Cube(self.scramble)
        self.solution = solution
        self.cube.apply(solution)
        kind, variant = (self.solution.steps[-1].kind, self.solution.steps[-1].variant) if self.solution.steps else ("","")
        self.should_draw_edge = self.is_bad_edge(kind, variant)
        self.should_draw_corner = self.is_bad_corner(kind, variant)
        self.set_colors()

    def is_bad_edge(self, kind, variant):
        def f(pos_id, piece_id, orientation, face):
            return self.cube.should_draw_edge(kind, variant, pos_id, face)
        return f

    def is_bad_corner(self, kind, variant):
        def f(pos_id, piece_id, orientation, face):
            return self.cube.should_draw_corner(kind, variant, pos_id, face)
        return f

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
        self.colors = [(1,1,1,.2)] * 54
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

    def draw_facelet(self, x, y, z, color, axis):
        glPushMatrix()
        glTranslatef(x, y, z)
        draw_grid = False

    # Draw a square face
        glBegin(GL_QUADS)
        if axis == 'xy':
            if draw_grid:
                glColor4f(0,0,0, color[3])
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
                glColor4f(0,0,0, color[3])
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
                glColor4f(0,0,0, color[3])
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
        # q = quat.Quaternion().from_axis_angle([1,0,0], self.xq_angle) \
        #     .multiply(quat.Quaternion().from_axis_angle([0,0,1], self.zq_angle))
        qx = pyquaternion.Quaternion(axis=[1, 0, 0], angle=self.xq_angle)
        qy = pyquaternion.Quaternion(axis=[0, 1, 0], angle=self.yq_angle)
        qz = pyquaternion.Quaternion(axis=[0, 0, 1], angle=self.zq_angle)
        q =  qz * qx * qy
        rotation_matrix = q.rotation_matrix

        # Order faces from back to front
        def distance_eu(i):
            c = math.cos(self.z_angle * math.pi / 180)
            s = math.sin(self.z_angle * math.pi / 180)
            xp = (facelet_x[i] * c - facelet_y[i] * s)
            yp = (facelet_x[i] * s + facelet_y[i] * c)
            zp = facelet_z[i]
            c = math.cos(self.y_angle * math.pi / 180)
            s = math.sin(self.y_angle * math.pi / 180)
            xpp = (-xp * c - zp * s)
            ypp = yp
            zpp = (-xp * s + zp * c)
            return (xpp - self.camera_x) ** 2 + \
                (ypp - self.camera_y) ** 2 + \
                (zpp - self.camera_z) ** 2

        def distance_qt(i):
            # v = np.array([facelet_x[i], facelet_y[i], facelet_z[i], 1.0], dtype=np.float32)
            # v_rotated = np.dot(rotation_matrix, v)
            v_rotated = q.rotate([facelet_x[i], facelet_y[i], facelet_z[i]])
            return (v_rotated[0] - self.camera_x) ** 2 + \
                (v_rotated[1] - self.camera_y) ** 2 + \
                (v_rotated[2] - self.camera_z) ** 2

        distance = distance_qt if USE_QT else distance_eu
        faces = [
            (range(9 * i, 9 * (i + 1)), distance(9 * i + 4)) for i in range(0, 6)
        ]
        faces.sort(key=lambda x: -x[1])
        faces = [f for f, d in faces]

        if USE_QT:
            # Update the GL matrix with the new rotation
            m = np.identity(4)
            m[:3, :3] = rotation_matrix

            # Convert to OpenGL format (column-major) and apply
            glPushMatrix()
            glMultMatrixf(m.T.flatten())
        else:
            glRotatef(self.y_angle, 0, 1, 0)
            glRotatef(self.z_angle, 0, 0, 1)

        for face in faces:
            for i in face:
                self.draw_facelet(facelet_x[i], facelet_y[i], facelet_z[i],
                                  self.colors[i], axis[i])

        if USE_QT:
            glPopMatrix()

        # Draw text
        if not self.solution.steps:
            return
        font = pygame.font.SysFont('Arial', 22)

        def write(text, x, y, top_justify=False, right_justify=False):
            text_surface = font.render(text, True, (255, 255, 255))
            glColor4f(0.3, 0.3, 0.3, 1.0)
            glRectf(x, y, x + text_surface.get_width(), y + text_surface.get_height())
            text_data = pygame.image.tostring(text_surface, 'RGBA', True)
            glWindowPos2d(
                x if not right_justify else x - text_surface.get_width(),
                y if not top_justify else y - text_surface.get_height())
            glDrawPixels(text_surface.get_width(), text_surface.get_height(), GL_RGBA,
                         GL_UNSIGNED_BYTE, text_data)
            return text_surface.get_height()

        write(self.scramble, 10, self.display_height, top_justify=True)

        n = len(self.solution.steps)
        y = 10
        y += write(
            f"{self.solution.steps[n - 1].kind}{self.solution.steps[n - 1].variant} - {self.solution.steps[n - 1].alg}",
            10, y)
        for i in range(2, n + 1):
            y += write(
                f"{self.solution.steps[n - i].alg} // {self.solution.steps[n - i].kind}{self.solution.steps[n - i].variant}",
                10, y)

        if self.solution.steps:
            write(
                self.cube.case_name_for_step(self.solution.steps[-1].kind,
                                             self.solution.steps[-1].variant),
                self.display_width - 10, 10, right_justify=True
            )

    def rotate(self, dx, dy=0):
        self.z_angle += dx
        self.y_angle += dy
        self.xq_angle += dy * .005
        self.zq_angle += dx * .005


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
        dragging = False
        last_mouse_pos = None


        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        dragging = True
                        last_mouse_pos = pygame.mouse.get_pos()

                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # Left mouse button
                        dragging = False

                if event.type == pygame.MOUSEMOTION:
                    if dragging:
                        current_mouse_pos = pygame.mouse.get_pos()
                        dx = current_mouse_pos[0] - last_mouse_pos[0]
                        dy = current_mouse_pos[1] - last_mouse_pos[1]
                        self.rotate(dx, 0)
                        last_mouse_pos = current_mouse_pos



                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.rotate(0, 10)
                    if event.key == pygame.K_DOWN:
                        self.rotate(0, -10)
                    if event.key == pygame.K_LEFT:
                        self.rotate(-10, 0)
                    if event.key == pygame.K_RIGHT:
                        self.rotate(10, 0)

                clock.tick(30)

            self.draw()
            # Update the display
            pygame.display.flip()
        pygame.quit()

USE_QT=True
XA = 0
ZA = -math.pi/6

if __name__ == "__main__":
    viz = CubeViz()

    # qx = quat.Quaternion().from_axis_angle([1,0,0], viz.xq_angle)
    # qz = quat.Quaternion().from_axis_angle([0,0,1], viz.zq_angle)
    # m = qz.multiply(qx).to_rotation_matrix()
    qx = pyquaternion.Quaternion(axis=[1, 0, 0], angle=viz.xq_angle)
    qz = pyquaternion.Quaternion(axis=[0, 0, 1], angle=viz.zq_angle)
    q = qz * qx
    m = q.rotation_matrix

    v = [0,0,1]
    rv = [math.floor(v+0.5) for v in q.rotate(v)]
    print(f"U: {v} -> {rv}")
    v = [-1,0,0]
    rv = [math.floor(v+0.5) for v in q.rotate(v)]
    print(f"L: {v} -> {rv}")
    v = [0,-1,0]
    rv = [math.floor(v+0.5) for v in q.rotate(v)]
    print(f"F: {v} -> {rv}")
    v = [1,0,0]
    rv = [math.floor(v+0.5) for v in q.rotate(v)]
    print(f"R: {v} -> {rv}")
    v = [0,1,0]
    rv = [math.floor(v+0.5) for v in q.rotate(v)]
    print(f"B: {v} -> {rv}")
    v = [0,0,-1]
    rv = [math.floor(v+0.5) for v in q.rotate(v)]
    print(f"D: {v} -> {rv}")


    viz.run()