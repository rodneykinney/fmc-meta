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
from cubelib.viz import facelet_x, facelet_y, facelet_z, axis, BACKGROUND, CubeViz
from py_cubelib import Cube, Algorithm, StepInfo, scramble as gen_scramble

def _current() -> SolutionBuilder:
    return cubelib.solution_builder._current


class CubeGLWidget(QOpenGLWidget):
    """OpenGL widget that uses the CubeViz drawing methods"""
    
    def __init__(self, viz: CubeViz, parent=None):
        super(CubeGLWidget, self).__init__(parent)
        self.setMinimumSize(400, 400)

        self.viz = viz
        
        # Set up a timer for animation/updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(30)  # 30ms refresh rate (approx 33 fps)
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.last_mouse_pos = None
        self.dragging = False

    def update_cube(self):
        """Update the cube based on the current solution builder"""
        self.viz.update()
        self.update()  # Trigger a repaint
        
    def initializeGL(self):
        """Initialize OpenGL settings"""
        self.viz.initializeGL(self.width(), self.height())

    def resizeGL(self, width, height):
        """Handle widget resize events"""
        self.viz.resize(width, height)

    def paintGL(self):
        """Render the OpenGL scene"""
        self.viz.draw()

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
            self.viz.rotate(dx)
            self.last_mouse_pos = event.pos()
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_X:
            self.viz.set_orientation(self.xq_angle - math.pi / 2, 0, 0)
        elif event.key() == Qt.Key_Y:
            self.viz.set_orientation(0, 0, self.zq_angle - math.pi / 2)
        elif event.key() == Qt.Key_Z:
            self.viz.set_orientation(0, self.yq_angle + math.pi / 2, 0)
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
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Top section: GL widget + scramble/step info
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        main_layout.addWidget(top_panel)
        
        # OpenGL widget (now on the left)
        self.viz = CubeViz()
        self.gl_widget = CubeGLWidget(self.viz)
        top_layout.addWidget(self.gl_widget)
        
        # Scramble and step info panel (right of GL widget)
        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        top_layout.addWidget(info_panel)
        
        current_container = QWidget()
        current_layout = QVBoxLayout(current_container)
        self.current_solution = QListWidget()
        self.current_solution.setStyleSheet("font-size: 16px;")
        current_layout.addWidget(self.current_solution)
        info_layout.addWidget(current_container)

        # Step info (from _current())
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 16px;")
        info_layout.addWidget(self.status_label)
        
        # Case label
        self.case_label = QLabel()
        info_layout.addWidget(self.case_label)
        
        # Command input below the GL widget
        command_container = QWidget()
        command_layout = QHBoxLayout(command_container)
        command_label = QLabel("Command:")
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.execute_command)
        execute_button = QPushButton("Execute")
        execute_button.clicked.connect(lambda: self.execute_command())
        
        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_input)
        command_layout.addWidget(execute_button)
        main_layout.addWidget(command_container)
        
        # Solutions list at the bottom
        solutions_container = QWidget()
        solutions_layout = QVBoxLayout(solutions_container)
        solutions_layout.addWidget(QLabel("Found Solutions (Double-click to check a solution):"))
        self.solution_list = QListWidget()
        self.solution_list.itemDoubleClicked.connect(self.check_solution)
        solutions_layout.addWidget(self.solution_list)
        main_layout.addWidget(solutions_container)
        
        # Console output
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        main_layout.addWidget(self.console_output)
        
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

    def refresh_current_solution(self):
        curr = _current()
        self.current_solution.clear()
        self.current_solution.addItem("self.viz.scramble")
        self.current_solution.addItem("")
        for step in _current().substeps():
            comment = ""
            if step.step_info.is_solved(self.viz.cube):
                comment = f"{step.kind} ({step.full_alg().len()}) {step.comment}"
            else:
                comment = f"{step.kind}-{step.step_info.case_name(self.viz.cube)} {step.comment}"
            self.current_solution.addItem(f"{step.alg} // {comment}")

    def _update_step(self, old_builder, new_builder):
        """Handle step changes"""
        current = _current()

        # Update cube
        self.gl_widget.update_cube()

        # Update status label
        self.refresh_current_solution()
        step_type = f"{current.kind}{current.variant}"
        alg_text = f"{current.alg}"
        status = f"Step: {step_type} | Moves: {alg_text}"
        self.status_label.setText(status)
        
        # Update case label
        case = current.step_info.case_name(self.viz.cube)
        self.case_label.setText(f"Case: {case}")
        

    def set_scramble(self, scramble: str):
        """Set the cube to a specific scramble"""
        self.refresh_current_solution()
        self.viz.set_scramble(scramble)
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
                exec(f"self.{cmd}", globals(), {'self': self})
        except Exception as e:
            self.console_output.append(f"Error: {str(e)}")
            
        self.command_input.clear()
    
    def _append_moves(self, moves):
        """Append moves to the current solution"""
        moves = moves.split(" ")
        inverse = self.viz.inverse
        
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
        self.viz.set_inverse(not self.viz.inverse)
        self.gl_widget.update_cube()
    
    def _set_mode(self, kind, variant) -> bool:
        """Change to a specific solving step"""
        step_info = StepInfo(kind, variant)
        if step_info.is_eligible(self.viz.cube):
            if (not _current().alg.is_empty()) and not _current().step_info.is_solved(self.viz.cube):
                self.reset()
            _current().advance_to(kind, variant)
            while step_info.is_solved(self.viz.cube) and _current().previous:
                _current().back()
            return True
        else:
            self.console_output.append(f"Cube is not eligible for {kind}{variant}")
            return False
    
    def solve(self):
        """Find and save solutions for the current step"""
        curr = _current()
        on_inverse = self.viz.inverse
        if on_inverse:
            self.niss()
        n_existing = len(curr.saved_solutions_of_same_step())
        if curr.alg.len() == 0:
            # Multiple solutions of the full step, auto-save
            self.console_output.append(f"Finding solutions for {curr.kind}{curr.variant}...")
            algs = curr.step_info.solve(self.viz.cube, n_existing + 10)
            self.console_output.append(f"Found {len(algs)} solutions. Saving")
            count = 0
            for alg in algs:
                count += 1 if curr.save_solution(alg) else 0
                if count >= 10:
                    break
            self.list_solutions()
        else:
            algs = curr.step_info.solve(self.viz.cube, n_existing + 1)
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
        if not curr.step_info.is_solved(self.viz.cube):
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
            case = curr.step_info.case_name(self.viz.cube)
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