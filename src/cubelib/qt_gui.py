import sys
import math
import threading
import io
import logging
from typing import Optional, List

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                           QLabel, QOpenGLWidget, QLineEdit, QPushButton, QTextEdit, 
                           QListWidget, QSplitter, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QSurfaceFormat

from OpenGL.GL import *
from OpenGL.GLU import *

import cubelib.solution_builder
from cubelib.solution_builder import SolutionBuilder
from cubelib.viz import facelet_x, facelet_y, facelet_z, axis, BACKGROUND
from py_cubelib import Cube, Algorithm, StepInfo, scramble as gen_scramble

def _current() -> SolutionBuilder:
    return cubelib.solution_builder._current


class CubeGLWidget(QOpenGLWidget):
    """OpenGL widget that uses the CubeViz drawing methods"""
    
    def __init__(self, parent=None):
        super(CubeGLWidget, self).__init__(parent)
        self.setMinimumSize(400, 400)
        
        # Cube state
        self.cube = Cube("")
        self.scramble = ""
        self.colors = [(1, 1, 1, 0.2)] * 54
        self.inverse = False
        
        # View parameters
        self.camera_x = 0.0
        self.camera_y = -10.0
        self.camera_z = 6.0
        self.xq_angle = 0
        self.yq_angle = 0
        self.zq_angle = 0
        self.view_angle = -math.pi / 6
        
        # Display options
        self.hide_corners = False
        self.hide_edges = False
        self.show_all = False
        
        # Import pyquaternion only when needed
        # (keeps imports cleaner when module is loaded)
        try:
            import pyquaternion
            self.pyquaternion = pyquaternion
        except ImportError:
            QMessageBox.critical(self, "Import Error", 
                                "pyquaternion module required but not found")
            raise
            
        # Set up a timer for animation/updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(30)  # 30ms refresh rate (approx 33 fps)
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.last_mouse_pos = None
        self.dragging = False

    def set_scramble(self, scramble: str):
        """Set the cube to the given scramble"""
        logging.debug(f"Setting scramble to {scramble}")
        self.scramble = scramble
        self.cube = Cube(self.scramble)
        self.refresh()
        self.update()
        
    def set_inverse(self, inverse: bool):
        """Toggle between normal and inverse scramble"""
        self.inverse = inverse
        self.update_cube()
        
    def should_draw_edge(self, pos_id, face):
        """Determine if a specific edge facelet should be drawn"""
        if self.show_all:
            return True
        if self.hide_edges:
            return False
        return _current().step_info.should_draw_edge(self.cube, pos_id, face)

    def should_draw_corner(self, pos_id, face):
        """Determine if a specific corner facelet should be drawn"""
        if self.show_all:
            return True
        if self.hide_corners:
            return False
        return _current().step_info.should_draw_corner(self.cube, pos_id, face)
        
    def refresh(self):
        """Refresh the cube colors based on the current state"""
        # Import the color definitions from viz.py
        from cubelib.viz import (WHITE, YELLOW, GREEN, BLUE, RED, ORANGE, 
                              corner_piece_colors, corner_position_facelets,
                              edge_piece_colors, edge_position_facelets,
                              default_orientation, home_slice)
                              
        opacity = 0.8  # Default opacity
        
        self.colors = [(1, 1, 1, .2)] * 54
        self.colors[4] = WHITE + (opacity,)
        self.colors[13] = ORANGE + (opacity,)
        self.colors[22] = GREEN + (opacity,)
        self.colors[31] = RED + (opacity,)
        self.colors[40] = BLUE + (opacity,)
        self.colors[49] = YELLOW + (opacity,)
        
        corners = self.cube.corners()
        for i in range(0, 8):
            piece_id, orientation = corners[i]
            for side in range(0, 3):
                if not self.should_draw_corner(i, side):
                    continue
                face = (side + 3 - orientation) % 3
                self.colors[corner_position_facelets[i][side]] = (
                        corner_piece_colors[piece_id][face] +
                        (opacity,))
                        
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
                                                               opacity,)
                                                               
    def update_cube(self):
        """Update the cube based on the current solution builder"""
        self.cube = Cube(self.scramble)
        self.cube.apply(_current().full_alg())
        if self.inverse:
            self.cube.invert()
        self.refresh()
        self.update()  # Trigger a repaint
        
    def set_orientation(self, x, y, z):
        """Set the cube orientation angles"""
        self.xq_angle = x
        self.yq_angle = y
        self.zq_angle = z
        self.update()
        
    def rotate(self, dx, dy=0):
        """Rotate the cube view"""
        self.view_angle += dx * .005
        self.update()

    def initializeGL(self):
        """Initialize OpenGL settings"""
        glClearColor(BACKGROUND, BACKGROUND, BACKGROUND, 1)
        glEnable(GL_DEPTH_TEST)
        
        # Set up the perspective
        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, (self.width() / self.height()), 0.1, 50.0)
        
        # Enable alpha blending
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)
        
    def resizeGL(self, width, height):
        """Handle widget resize events"""
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (width / height), 0.1, 50.0)
        
    def draw_facelet(self, x, y, z, color, axis):
        """Draw a single cube facelet"""
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
        
    def paintGL(self):
        """Render the OpenGL scene"""
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
        qx = self.pyquaternion.Quaternion(axis=[1, 0, 0], angle=self.xq_angle)
        qy = self.pyquaternion.Quaternion(axis=[0, 1, 0], angle=self.yq_angle)
        qz = self.pyquaternion.Quaternion(axis=[0, 0, 1], angle=self.zq_angle)
        qview = self.pyquaternion.Quaternion(axis=[0, 0, 1], angle=self.view_angle)
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
        import numpy as np
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
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_mouse_pos = event.pos()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
    
    def mouseMoveEvent(self, event):
        if self.dragging and self.last_mouse_pos:
            dx = event.x() - self.last_mouse_pos.x()
            self.rotate(dx)
            self.last_mouse_pos = event.pos()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_X:
            self.set_orientation(self.xq_angle - math.pi / 2, 0, 0)
        elif event.key() == Qt.Key_Y:
            self.set_orientation(0, 0, self.zq_angle - math.pi / 2)
        elif event.key() == Qt.Key_Z:
            self.set_orientation(0, self.yq_angle + math.pi / 2, 0)
        elif event.key() == Qt.Key_Left:
            self.rotate(-25)
        elif event.key() == Qt.Key_Right:
            self.rotate(25)
        else:
            super(CubeGLWidget, self).keyPressEvent(event)


class CubeExplorer(QMainWindow):
    """Main window for cube exploration with PyQt"""
    
    def __init__(self):
        super(CubeExplorer, self).__init__()
        
        self.setWindowTitle("Cube Explorer")
        self.resize(1200, 800)
        
        # Set up the OpenGL format
        gl_format = QSurfaceFormat()
        gl_format.setVersion(2, 1)
        gl_format.setProfile(QSurfaceFormat.CompatibilityProfile)
        QSurfaceFormat.setDefaultFormat(gl_format)
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Create a splitter to divide the window
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel (controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        splitter.addWidget(left_panel)
        
        # Scramble controls
        scramble_layout = QHBoxLayout()
        scramble_label = QLabel("Scramble:")
        self.scramble_input = QLineEdit()
        generate_button = QPushButton("Generate")
        generate_button.clicked.connect(self.generate_scramble)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(lambda: self.set_scramble(self.scramble_input.text()))
        
        scramble_layout.addWidget(scramble_label)
        scramble_layout.addWidget(self.scramble_input)
        scramble_layout.addWidget(generate_button)
        scramble_layout.addWidget(apply_button)
        left_layout.addLayout(scramble_layout)
        
        # Command input
        command_layout = QHBoxLayout()
        command_label = QLabel("Command:")
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.execute_command)
        execute_button = QPushButton("Execute")
        execute_button.clicked.connect(lambda: self.execute_command())
        
        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_input)
        command_layout.addWidget(execute_button)
        left_layout.addLayout(command_layout)
        
        # Step buttons
        step_layout = QHBoxLayout()
        eo_buttons = [QPushButton(f"EO{axis}") for axis in ["UD", "FB", "RL"]]
        eo_buttons[0].clicked.connect(self.eoud)
        eo_buttons[1].clicked.connect(self.eofb)
        eo_buttons[2].clicked.connect(self.eorl)
        
        dr_buttons = [QPushButton(f"DR{axis}") for axis in ["UD", "FB", "RL"]]
        dr_buttons[0].clicked.connect(self.drud)
        dr_buttons[1].clicked.connect(self.drfb)
        dr_buttons[2].clicked.connect(self.drrl)
        
        for button in eo_buttons + dr_buttons:
            step_layout.addWidget(button)
            
        left_layout.addLayout(step_layout)
        
        advanced_layout = QHBoxLayout()
        htr_button = QPushButton("HTR")
        htr_button.clicked.connect(self.htr)
        fr_button = QPushButton("FR")
        fr_button.clicked.connect(self.fr)
        solve_button = QPushButton("Solve")
        solve_button.clicked.connect(self.solve)
        niss_button = QPushButton("NISS")
        niss_button.clicked.connect(self.niss)
        
        for button in [htr_button, fr_button, solve_button, niss_button]:
            advanced_layout.addWidget(button)
            
        left_layout.addLayout(advanced_layout)
        
        # Solution actions
        action_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save)
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset)
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.back)
        list_button = QPushButton("List")
        list_button.clicked.connect(self.list_solutions)
        
        for button in [save_button, reset_button, back_button, list_button]:
            action_layout.addWidget(button)
            
        left_layout.addLayout(action_layout)
        
        # Solution list
        self.solution_list = QListWidget()
        self.solution_list.itemDoubleClicked.connect(self.check_solution)
        left_layout.addWidget(self.solution_list)
        left_layout.addWidget(QLabel("Double-click to check a solution"))
        
        # Console output
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        left_layout.addWidget(self.console_output)
        
        # Right panel (cube display)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        splitter.addWidget(right_panel)
        
        # Status bar at top
        self.status_label = QLabel()
        right_layout.addWidget(self.status_label)
        
        # OpenGL widget
        self.gl_widget = CubeGLWidget()
        right_layout.addWidget(self.gl_widget)
        
        # Case label at bottom
        self.case_label = QLabel()
        right_layout.addWidget(self.case_label)
        
        # Set up stdout redirection
        self.stdout_buffer = io.StringIO()
        sys.stdout = self
        
        # Update listeners
        cubelib.solution_builder._listener = self._update_step
        
        # Set initial scramble
        self.generate_scramble()
        
        # Set focus to command input
        self.command_input.setFocus()
        
    def write(self, text):
        """Handle stdout redirection"""
        self.stdout_buffer.write(text)
        self.console_output.append(text.rstrip())
        
    def flush(self):
        """Handle stdout flush"""
        pass
        
    def _update_step(self, old_builder, new_builder):
        """Handle step changes"""
        current = _current()
        
        # Update status label
        step_type = f"{current.kind}{current.variant}"
        alg_text = f"{current.alg}"
        status = f"Step: {step_type} | Moves: {alg_text}"
        self.status_label.setText(status)
        
        # Update case label
        case = current.step_info.case_name(self.gl_widget.cube)
        self.case_label.setText(f"Case: {case}")
        
        # Update cube
        self.gl_widget.update_cube()
    
    def set_scramble(self, scramble: str):
        """Set the cube to a specific scramble"""
        self.scramble_input.setText(scramble)
        self.gl_widget.set_scramble(scramble)
        _current().clear()
        self._update_step(None, _current())
        
    def generate_scramble(self):
        """Generate a random scramble"""
        scramble = gen_scramble()
        self.set_scramble(scramble)
        
    def execute_command(self):
        """Execute a command from the command input"""
        cmd = self.command_input.text().strip()
        if not cmd:
            return
            
        self.console_output.append(f"> {cmd}")
        
        try:
            # Check if it's a sequence of cube moves
            if all(m in MOVES for m in cmd.upper().split()):
                self._append_moves(cmd.upper())
            else:
                # Assume it's a Python command
                if cmd.find("(") < 0:
                    cmd = f"{cmd}()"
                # Use locals and globals from this context
                exec(cmd, globals(), {'self': self})
        except Exception as e:
            self.console_output.append(f"Error: {str(e)}")
            
        self.command_input.clear()
    
    def _append_moves(self, moves):
        """Append moves to the current solution"""
        moves = moves.split(" ")
        inverse = self.gl_widget.inverse
        
        if _current().alg.len() > 0:
            if not _current().append_moves(moves, inverse):
                self.console_output.append(
                    f"{moves} not allowed after {_current().previous.kind}{_current().previous.variant}")
        else:
            if not _current().append_moves(moves, inverse):
                assert _current().previous is not None
                if all(_current().previous.allows_move(m) for m in moves):
                    alg = _current().previous.alg
                    _current().back()
                    _current().append_moves(alg.normal_moves(), False)
                    _current().append_moves(alg.inverse_moves(), True)
                    _current().append_moves(moves, inverse)
                else:
                    self.console_output.append(
                        f"{moves} not allowed after {_current().previous.kind}{_current().previous.variant}")
        
    def eoud(self):
        """Look for EO on UD axis"""
        self._set_mode("eo", "ud")
        
    def eofb(self):
        """Look for EO on FB axis"""
        self._set_mode("eo", "fb")
        
    def eorl(self):
        """Look for EO on RL axis"""
        self._set_mode("eo", "rl")
        
    def drud(self):
        """Look for DR on UD axis"""
        self._set_mode("dr", "ud")
        
    def drfb(self):
        """Look for DR on FB axis"""
        self._set_mode("dr", "fb")
        
    def drrl(self):
        """Look for DR on RL axis"""
        self._set_mode("dr", "rl")
        
    def htr(self):
        """Look for HTR"""
        self._set_mode("htr", _current().previous.variant if _current().previous else "ud")
        
    def fr(self):
        """Look for FR"""
        self._set_mode("fr", _current().previous.variant if _current().previous else "ud")
        
    def niss(self):
        """Switch between normal and inverse scramble"""
        self.gl_widget.set_inverse(not self.gl_widget.inverse)
    
    def _set_mode(self, kind, variant) -> bool:
        """Change to a specific solving step"""
        step_info = StepInfo(kind, variant)
        if step_info.is_eligible(self.gl_widget.cube):
            if (not _current().alg.is_empty()) and not _current().step_info.is_solved(self.gl_widget.cube):
                self.reset()
            _current().advance_to(kind, variant)
            while step_info.is_solved(self.gl_widget.cube) and _current().previous:
                _current().back()
            return True
        else:
            self.console_output.append(f"Cube is not eligible for {kind}{variant}")
            return False
    
    def solve(self):
        """Find and save solutions for the current step"""
        curr = _current()
        on_inverse = self.gl_widget.inverse
        if on_inverse:
            self.niss()
        n_existing = len(curr.saved_solutions_of_same_step())
        if curr.alg.len() == 0:
            # Multiple solutions of the full step, auto-save
            self.console_output.append(f"Finding solutions for {curr.kind}{curr.variant}...")
            algs = curr.step_info.solve(self.gl_widget.cube, n_existing + 10)
            self.console_output.append(f"Found {len(algs)} solutions. Saving")
            count = 0
            for alg in algs:
                count += 1 if curr.save_solution(alg) else 0
                if count >= 10:
                    break
            self.list_solutions()
        else:
            algs = curr.step_info.solve(self.gl_widget.cube, n_existing + 1)
            if algs:
                existing = {f"{a}" for a in curr.saved_solutions_of_same_step()}
                for a in algs:
                    if f"{a}" not in existing:
                        curr.alg = curr.alg.merge(a)
                        cubelib.solution_builder.update(curr)
                        break
            else:
                self.console_output.append("No solution found!")
        if on_inverse:
            self.niss()
    
    def save(self):
        """Save this algorithm and start a new one"""
        curr = _current()
        if not curr.step_info.is_solved(self.gl_widget.cube):
            if curr.kind == "" or curr.previous is None:
                self.console_output.append("Complete at least one step before saving")
                return
            partial = SolutionBuilder(
                kind=curr.previous.kind,
                variant=curr.previous.variant,
                previous=curr.previous.previous,
            )
            partial.alg = curr.previous.alg.merge(curr.alg)
            from cubelib.explore import NEXT_STEPS
            options = NEXT_STEPS.get((partial.kind, partial.variant), [])
            case = curr.step_info.case_name(self.gl_widget.cube)
            partial.comment = f"{curr.kind}{curr.variant}-{case}" if len(options) > 1 else case
            partial.save()
            return
        curr.save()
        from cubelib.explore import NEXT_STEPS
        next_steps = NEXT_STEPS.get((curr.kind, curr.variant))
        if next_steps is not None and len(next_steps) == 1:
            curr.advance_to(*next_steps[0])
        else:
            self.reset()
    
    def reset(self):
        """Reset the cube to the beginning of the current step"""
        _current().reset()
    
    def back(self):
        """Go back to the previous step"""
        _current().back()
    
    def list_solutions(self):
        """List saved solutions for the current step"""
        curr = _current()
        self.solution_list.clear()
        self.console_output.append(f"{curr.kind}{curr.variant}: ")
        for (i, b) in enumerate(curr.saved_solutions_of_same_step()):
            steps = b.substeps()
            summary = " ".join(
                [f"{s.alg} // {s.kind} ({s.full_alg().len()}) {s.comment}" for s in steps])
            self.solution_list.addItem(f"{i + 1:02d}: {summary}")
            self.console_output.append(f"{' ' if b.is_checked else '?'}{i + 1:02d}: {summary}")
            
    def check_solution(self, item):
        """Load a selected solution"""
        # Extract solution number from the item text (format: "01: solution...")
        index = int(item.text().split(':')[0].strip()) - 1
        _current().load(index)

# Basic set of cube moves
MOVES = {
    "R", "U", "F", "L", "D", "B",
    "R'", "U'", "F'", "L'", "D'", "B'",
    "R2", "U2", "F2", "L2", "D2", "B2",
}

def main():
    # Configure logging
    logging.basicConfig(
        filename="fmc-meta.log", filemode="w",
        level=logging.DEBUG,
        format='%(levelname)s - %(message)s'
    )
    
    # Create the Qt Application
    app = QApplication(sys.argv)
    window = CubeExplorer()
    window.show()
    
    # Start the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()