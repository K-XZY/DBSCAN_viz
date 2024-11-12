import tkinter as tk
from tkinter import Scale, Button, HORIZONTAL, Label, Checkbutton, IntVar
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import os
import sys

# Initialize Tkinter UI
root = tk.Tk()
root.title("Interactive DBSCAN Visualizer")

# Set up the main frame
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True)

# Variables for drawing and animation
points = []
brush_size = 1  # Default brush size
animation_frames = []
export_animation = IntVar()
prev_click_position = None  # For brush functionality
current_frame = 0  # For GUI animation
cluster_colors = ['red', 'green', 'yellow', 'blue', 'pink']

def get_cluster_color(cluster_id):
    # Clusters are numbered starting from 1
    index = (cluster_id - 1) % len(cluster_colors)
    return cluster_colors[index]

# Create a frame to hold the canvas and add a black border
canvas_frame = tk.Frame(main_frame, bg='black', bd=2)
canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=2, pady=2)

# Create a Matplotlib figure for plotting
fig, ax = plt.subplots(figsize=(5, 5))  # Fixed size figure

canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill=tk.BOTH, expand=True)

def draw_points(event):
    global points, prev_click_position
    x = event.x
    y = event.y
    # Adjust y-coordinate
    canvas_height = canvas_widget.winfo_height()
    y_corrected = canvas_height - y
    # Convert canvas coordinates to data coordinates
    inv = ax.transData.inverted()
    x_data, y_data = inv.transform((x, y_corrected))
    # Calculate distance from previous click
    if prev_click_position is not None:
        distance = np.hypot(x_data - prev_click_position[0], y_data - prev_click_position[1])
        if distance < brush_size * 0.05:
            return  # Do not add points if within previous click radius
    prev_click_position = (x_data, y_data)
    # Randomly spawn points within the brush radius
    num_points = brush_size * 5  # Adjust density as needed
    angles = np.random.uniform(0, 2 * np.pi, num_points)
    radii = np.random.uniform(0, brush_size * 0.05, num_points)
    xs = x_data + radii * np.cos(angles)
    ys = y_data + radii * np.sin(angles)
    new_points = np.column_stack((xs, ys))
    points.extend(new_points.tolist())
    update_plot()

def clear_canvas():
    global points, animation_frames, prev_click_position, current_frame
    points = []
    animation_frames = []
    prev_click_position = None
    current_frame = 0
    ax.clear()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')  # Hide axes for a cleaner look
    canvas.draw()

def update_plot():
    ax.clear()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')  # Hide axes for a cleaner look
    if points:
        points_np = np.array(points)
        ax.plot(points_np[:, 0], points_np[:, 1], 'o', color='black', markersize=5, markeredgewidth=0, alpha=0.9)
    canvas.draw()

def run_dbscan():
    global animation_frames, current_frame
    if points:
        epsilon = epsilon_slider.get() / 100  # Adjust scale
        min_pts = min_pts_slider.get()
        animation_frames = []
        current_frame = 0
        # Run the DBSCAN process and record frames
        dbscan_with_visualization(np.array(points), epsilon, min_pts)
        # Start GUI animation
        play_gui_animation()
        if export_animation.get():
            save_animation()

def dbscan_with_visualization(points_array, epsilon, min_pts):
    labels = [0] * len(points_array)  # 0 indicates unvisited
    cluster_id = 0
    n_points = len(points_array)
    processed = set()

    def region_query(point_idx):
        neighbors = []
        for i in range(n_points):
            if np.linalg.norm(points_array[point_idx] - points_array[i]) <= epsilon:
                neighbors.append(i)
        return neighbors

    def expand_cluster(point_idx, neighbors):
        labels[point_idx] = cluster_id
        record_frame(labels.copy(), points_array[point_idx], epsilon)
        i = 0
        while i < len(neighbors):
            neighbor_idx = neighbors[i]
            if neighbor_idx in processed:
                i += 1
                continue
            processed.add(neighbor_idx)
            if labels[neighbor_idx] == 0:  # Unvisited
                labels[neighbor_idx] = cluster_id
                record_frame(labels.copy(), points_array[neighbor_idx], epsilon)
                new_neighbors = region_query(neighbor_idx)
                if len(new_neighbors) >= min_pts:
                    neighbors += new_neighbors
            elif labels[neighbor_idx] == -1:
                labels[neighbor_idx] = cluster_id  # Change noise to border point
                record_frame(labels.copy(), points_array[neighbor_idx], epsilon)
            i += 1

    def record_frame(labels_snapshot, current_point=None, epsilon=None):
        frame = {
            'labels': labels_snapshot,
            'current_point': current_point,
            'epsilon': epsilon
        }
        animation_frames.append(frame)

    for i in range(n_points):
        if labels[i] != 0:
            continue  # Already processed
        processed.add(i)
        neighbors = region_query(i)
        if len(neighbors) >= min_pts:
            cluster_id += 1
            expand_cluster(i, neighbors)
        else:
            labels[i] = -1  # Mark as noise
            record_frame(labels.copy(), points_array[i], epsilon)

    # Record final frame
    record_frame(labels.copy())

def update_dbscan_plot(frame_index):
    if frame_index < 0 or frame_index >= len(animation_frames):
        return
    frame = animation_frames[frame_index]
    labels = frame['labels']
    current_point = frame.get('current_point', None)
    epsilon = frame.get('epsilon', None)
    ax.clear()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')  # Hide axes for a cleaner look
    points_np = np.array(points)
    unique_labels = set(labels)
    for k in sorted(unique_labels):
        class_member_mask = (np.array(labels) == k)
        xy = points_np[class_member_mask]
        if k == 0:
            # Unvisited points in black
            col = 'black'
        elif k == -1:
            # Noise points in gray
            col = 'gray'
        else:
            # Assign colors to clusters based on the fixed mapping
            col = get_cluster_color(k)
        ax.plot(xy[:, 0], xy[:, 1], 'o', color=col, markersize=5, markeredgewidth=0, alpha=0.9)
    # Draw circle around current point
    if current_point is not None and epsilon is not None:
        circle = Circle((current_point[0], current_point[1]), epsilon, color='red', fill=False, linewidth=1)
        ax.add_patch(circle)
    canvas.draw()

def play_gui_animation():
    global current_frame
    def update_frame():
        global current_frame
        if current_frame < len(animation_frames):
            update_dbscan_plot(current_frame)
            current_frame += 1
            root.after(animation_speed_slider.get(), update_frame)
        else:
            # Animation finished
            pass
    update_frame()

def save_animation():
    # Create a matplotlib animation
    def animate(i):
        update_dbscan_plot(i)

    ani = animation.FuncAnimation(fig, animate, frames=len(animation_frames), interval=100, repeat=False)

    # Determine the download directory
    if sys.platform.startswith('win'):
        download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    elif sys.platform.startswith('darwin'):
        download_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
    else:
        download_dir = os.path.expanduser('~')

    # Save the animation as an MP4 file
    output_path = os.path.join(download_dir, 'dbscan_animation.mp4')
    ani.save(output_path, writer='ffmpeg', fps=10)
    print(f"Animation saved to {output_path}")

# UI Elements
canvas_widget.bind("<Button-1>", draw_points)  # Capture single clicks
canvas_widget.bind("<B1-Motion>", draw_points)

# Right frame for controls
control_frame = tk.Frame(main_frame)
control_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Slider for brush size
brush_label = tk.Label(control_frame, text="Brush Size")
brush_label.pack(pady=5)
brush_slider = Scale(control_frame, from_=1, to=10, orient=HORIZONTAL)
brush_slider.set(brush_size)
brush_slider.pack()

def update_brush_size(val):
    global brush_size
    brush_size = int(val)

brush_slider.config(command=update_brush_size)

# Button to clear canvas
clear_button = Button(control_frame, text="Clear", command=clear_canvas)
clear_button.pack(pady=10)

# Sliders for DBSCAN parameters
epsilon_label = tk.Label(control_frame, text="Radius (epsilon)")
epsilon_label.pack(pady=5)
epsilon_slider = Scale(control_frame, from_=1, to=50, orient=HORIZONTAL)
epsilon_slider.set(5)
epsilon_slider.pack()

min_pts_label = tk.Label(control_frame, text="Min Points (minPts)")
min_pts_label.pack(pady=5)
min_pts_slider = Scale(control_frame, from_=1, to=20, orient=HORIZONTAL)
min_pts_slider.set(5)
min_pts_slider.pack()

# Slider for animation speed
animation_speed_label = Label(control_frame, text="Animation Speed (ms)")
animation_speed_label.pack(pady=5)
animation_speed_slider = Scale(control_frame, from_=1, to=200, orient=HORIZONTAL)
animation_speed_slider.set(50)  # Default to faster animation
animation_speed_slider.pack()

# Checkbox for exporting animation
export_checkbox = Checkbutton(control_frame, text="Export Animation", variable=export_animation)
export_checkbox.pack(pady=5)

# Button to run DBSCAN
run_button = Button(control_frame, text="Run DBSCAN", command=run_dbscan)
run_button.pack(pady=10)

# Initial plot setup
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')  # Hide axes for a cleaner look
canvas.draw()

root.mainloop()
