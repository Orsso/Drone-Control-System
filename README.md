# Drone Control System

A web-based drone control platform featuring real-time video processing and color-based object tracking.

## Overview

The system provides a military-style interface for drone control with real-time video feed, color tracking capabilities, and 3D visualization of drone orientation. The interface includes basic drone controls (takeoff/land), color-based tracking options, and velocity monitoring.

## Technical Stack

Built with Flask and OpenCV for backend operations, featuring an HTML5/CSS3 frontend with Three.js for 3D visualization. The color tracking system uses HSV color space detection with support for multiple color presets.

## Getting Started

Install dependencies:
```bash
pip install flask opencv-python numpy
```

Launch the application:
```bash
python app.py
```

Access the interface at `http://localhost:5000` to begin controlling the drone, monitoring video feed, and utilizing tracking features.

## Usage

Control your drone through the intuitive web interface. Select tracking colors from the palette for autonomous following. Monitor drone status and orientation through the real-time 3D visualization and status indicators.
