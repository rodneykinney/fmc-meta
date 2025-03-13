import pygame
import math
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# Initialize pygame
pygame.init()

# Set up the display
display_width = 800
display_height = 600
pygame.display.set_mode((display_width, display_height), DOUBLEBUF | OPENGL)
pygame.display.set_caption("3D Grid of Colored Squares")

# Set up the perspective
glMatrixMode(GL_PROJECTION)
gluPerspective(45, (display_width / display_height), 0.1, 50.0)

glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
glEnable( GL_BLEND )

# Initial camera position
camera_x = 5.0
camera_y = 5.0
camera_z = 10.0

# Define colors for the squares (RGB format)
colors = [
    (1.0, 0.0, 0.0, 0.3),  # Red
    (0.0, 1.0, 0.0, 0.3),  # Green
    (0.0, 0.0, 1.0, 0.3),  # Blue
    (1.0, 1.0, 0.0, 0.3),  # Yellow
    (1.0, 0.0, 1.0, 0.3),  # Magenta
    (0.0, 1.0, 1.0, 0.3),  # Cyan
    (0.7, 0.3, 0.5, 0.3),  # Purple
    (1.0, 0.5, 0.0, 0.3),  # Orange
    (0.5, 0.5, 0.5, 0.3)  # Gray
]


def draw_square(x, y, z, color_idx, axis='xy'):
    """Draw a square at given position with specified color and axis"""
    # if color_idx not in {2, 7}:
    #     return

    color = colors[color_idx]

    glPushMatrix()
    glTranslatef(x, y, z)
    glColor4fv(color)

    # Draw a square face
    glBegin(GL_QUADS)
    if axis == 'xy':
        glVertex3f(-0.5, -0.5, 0.0)
        glVertex3f(0.5, -0.5, 0.0)
        glVertex3f(0.5, 0.5, 0.0)
        glVertex3f(-0.5, 0.5, 0.0)
    elif axis == 'xz':
        glVertex3f(-0.5, 0.0, -0.5)
        glVertex3f(0.5, 0.0, -0.5)
        glVertex3f(0.5, 0.0, 0.5)
        glVertex3f(-0.5, 0.0, 0.5)
    elif axis == 'yz':
        glVertex3f(0.0, -0.5, -0.5)
        glVertex3f(0.0, 0.5, -0.5)
        glVertex3f(0.0, 0.5, 0.5)
        glVertex3f(0.0, -0.5, 0.5)
    glEnd()

    glPopMatrix()

    # U + L + F + R + B + D


facelet_x = \
    [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5] \
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [1, 0, -1, 1, 0, -1, 1, 0, -1] \
    + [1, 0, -1, 1, 0, -1, 1, 0, -1]
facelet_y = \
    [-1, -1, -1, 0, 0, 0, 1, 1, 1] \
    + [-1, 0, 1, -1, 0, 1, -1, 0, 1] \
    + [1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5] \
    + [1, 0, -1, 1, 0, -1, 1, 0, -1] \
    + [-1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5, -1.5] \
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


def draw_grid():
    """Draw a 3x3 grid of squares"""
    color_idx = 0
    for i in range(0,54):
        draw_square(facelet_x[i], facelet_y[i], facelet_z[i], color_idx, axis[i])
        # for a in range(-1, 2):
        #     for b in range(-1, 2):
        #         draw_square(b, -1.5, a, color_idx, "xz")
        #         draw_square(b, 1.5, a, color_idx, "xz")
        #         draw_square(-1.5, a, b, color_idx, "yz")
        #         draw_square(1.5, a, b, color_idx, "yz")
        #         draw_square(a, b, -1.5, color_idx, "xy")
        #         draw_square(a, b, 1.5, color_idx, "xy")
        color_idx = (color_idx + 1) % len(colors)  # Cycle through colors


def main():
    global camera_x, camera_y, camera_z

    clock = pygame.time.Clock()
    running = True
    rotation_angle = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Camera position controls
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    camera_x -= 0.5
                if event.key == pygame.K_RIGHT:
                    camera_x += 0.5
                if event.key == pygame.K_UP:
                    camera_y += 0.5
                if event.key == pygame.K_DOWN:
                    camera_y -= 0.5
                if event.key == pygame.K_w:
                    camera_z -= 0.5
                if event.key == pygame.K_s:
                    camera_z += 0.5

        # Clear the screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Set camera position
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(camera_x, camera_y, camera_z,  # Camera position
                  0, 0, 0,  # Look at point
                  0, 1, 0)  # Up vector

        # Slowly rotate the view
        rotation_angle += 0.5
        glRotatef(rotation_angle, 0, 1, 0)

        # Draw the grid
        draw_grid()

        # Update the display
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
