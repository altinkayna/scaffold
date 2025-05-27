import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import time

# Define global variables at the top of the script
resolution = 80  # Number of sampling points in each dimension
linspace_min = 0.5 #Limit of sampling points in X and Y dimensions
linspace_max = 10.0
linspace_min_Z = 1.0 #Limit of sampling points in Z dimension
linspace_max_Z = 9.0
ray_direction = Vector((1, 0, 0))  # Direction for ray casting
show_red_spheres = False  # Option to show red spheres

# File path options
FILE_PATH_OPTIONS = {
    "OPTION_1": "C:\\path\\to\\folder\\",
    "OPTION_2": "/path/to/folder/"
}
SELECTED_PATH = FILE_PATH_OPTIONS["OPTION_1"]  # Choose the file path

# Set a maximum script run time in seconds
max_duration = 120  # Limit script execution to 120 seconds
start_time = time.time()

# Select the object in question
obj = bpy.context.active_object

# Ensure the object is in object mode to access mesh data
if obj.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')

# Create BVH tree for the object to efficiently calculate distances
bm = bmesh.new()
bm.from_mesh(obj.data)
bvh_tree = BVHTree.FromBMesh(bm)

# Initialize bounding box limits
bbox_min = Vector((float('inf'), float('inf'), float('inf')))
bbox_max = Vector((float('-inf'), float('-inf'), float('-inf')))

# Iterate over the vertices of the mesh to find min and max coordinates
for vert in bm.verts:
    coord = vert.co
    bbox_min.x = min(bbox_min.x, coord.x)
    bbox_min.y = min(bbox_min.y, coord.y)
    bbox_min.z = min(bbox_min.z, coord.z)

    bbox_max.x = max(bbox_max.x, coord.x)
    bbox_max.y = max(bbox_max.y, coord.y)
    bbox_max.z = max(bbox_max.z, coord.z)

# Set up a 3D grid of points where we will sample distances (based on bounding box)
x_vals = np.linspace(linspace_min, linspace_max, resolution)
y_vals = np.linspace(linspace_min, linspace_max, resolution)
z_vals = np.linspace(linspace_min_Z, linspace_max_Z, resolution)

# Function to determine if a point is inside the solid
def is_inside_solid(point, bvh_tree):
    ray_origin = point
    hit_count = 0

    while True:
        hit = bvh_tree.ray_cast(ray_origin, ray_direction)
        if hit[0] is None:  # No further intersections
            break
        hit_count += 1
        ray_origin = hit[0] + ray_direction * 1e-6  # Move slightly past the hit point to continue

    return hit_count % 2 == 1

# List to store point data and max distances
point_data = []
max_distances = []

# Iterate over the grid of points and calculate distance to nearest surface
for x in x_vals:
    for y in y_vals:
        for z in z_vals:
            if time.time() - start_time > max_duration:
                print("Script stopped due to timeout")
                break  # Exit the loop if the script exceeds the time limit

            point = Vector((x, y, z))
            if is_inside_solid(point, bvh_tree):
                continue  # Skip points inside the solid

            location, normal, index, distance = bvh_tree.find_nearest(point)
            point_data.append((point, distance))
            max_distances.append((distance, point))

# Sort and process point data
point_data.sort(reverse=True, key=lambda x: x[1])
max_distances.sort(reverse=True, key=lambda x: x[0])

# Save all radius values to a text file
with open(f'{SELECTED_PATH}radius.txt', 'w') as file:
    file.write("Point Location (x, y, z), Radius\n")
    for point, radius in point_data:
        file.write(f"{point.x:.4f}, {point.y:.4f}, {point.z:.4f}, {radius:.4f}\n")

#print(f"Point locations and radii have been saved to {output_file}")

# Highlight the top 3 maximum distances
# The diameter values will always be added as custom properties, even if spheres are not displayed
top_3_distances = max_distances[:3]

if show_red_spheres:
    # Create a red material
    material_name = "Red_Material"
    material = bpy.data.materials.get(material_name)
    if material is None:
        material = bpy.data.materials.new(name=material_name)
        material.diffuse_color = (1.0, 0.0, 0.0, 1.0)  # Red color (RGBA format)

    for idx, (dist, pt) in enumerate(top_3_distances, start=1):
        print(f"Top {idx} sphere center: {pt}, diameter: {dist * 2}")
        bpy.ops.mesh.primitive_uv_sphere_add(radius=dist, location=pt)
        sphere = bpy.context.object
        if sphere.data.materials:
            sphere.data.materials[0] = material
        else:
            sphere.data.materials.append(material)
        sphere["Diameter"] = dist * 2

# Always add the diameter as a custom property to the original object
for idx, (dist, pt) in enumerate(top_3_distances, start=1):
    obj[f"Diameter_{idx}"] = dist * 2

# Optionally switch back to object mode after execution
bpy.ops.object.mode_set(mode='OBJECT')

# Print bounding box for debugging
print(f"Bounding box min: {bbox_min}")
print(f"Bounding box max: {bbox_max}")
