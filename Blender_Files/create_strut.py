import bpy
import csv
import bmesh

# Configuration
BEVEL_TYPE = "RECTANGLE"  # Options: "CIRCLE" or "RECTANGLE"
RECTANGLE_WIDTH = 0.3  # Width for the rectangular profile
THRESHOLD_HIGH = 127.5  # Threshold for cleaning vertices
THRESHOLD_LOW = 0.5  # Threshold for cleaning vertices
NUMBER_OF_FILES = 256 # Number of files to process
VOXEL_SIZE_UNIFORM_INITIAL = 0.1 # Initial meshing
VOXEL_SIZE_UNIFORM = 0.05; #Post-process the structure 
#Check if voxel_size_uniform operations is completed. Otherwise, perform manually.

# File path options
FILE_PATH_OPTIONS = {
    "OPTION_1": "C:\\path\\to\\folder\\",
    "OPTION_2": "/path/to/folder/"
}
SELECTED_PATH = FILE_PATH_OPTIONS["OPTION_1"]  # Choose the file path

# Function to export the combined paths as STL
def export_combined_paths_as_stl(filepath):
    combined_paths = combine_paths()  # Combine all paths into one object
    # Export the combined paths as an STL file
    # bpy.ops.export_mesh.stl(filepath=filepath, use_selection=True)
    return combined_paths  # Return the combined paths object for further operations

# Function to combine all paths into a single object
def combine_paths():
    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')
    
    # Select all path objects based on the naming pattern
    for obj in bpy.context.scene.objects:
        if obj.name.startswith("SplineObject_"):  # Adjusted to match your naming convention
            obj.select_set(True)
    
    # Join the selected objects into one
    bpy.ops.object.join()
    
    # The combined object will be the active object
    return bpy.context.view_layer.objects.active

# Function to apply final remesh
def apply_final_remesh(mesh_obj, voxel_size=VOXEL_SIZE_UNIFORM):
    remesh_modifier = mesh_obj.modifiers.new(name="FinalVoxelRemesh", type='REMESH')
    remesh_modifier.mode = 'VOXEL'
    remesh_modifier.voxel_size = voxel_size
    remesh_modifier.use_smooth_shade = True
    remesh_modifier.use_fix_poles = True
    remesh_modifier.use_preserve_volume = False
    bpy.ops.object.modifier_apply(modifier="FinalVoxelRemesh")

# Function to apply uniform remeshing
def apply_uniform_remesh(mesh_obj, voxel_size=VOXEL_SIZE_UNIFORM_INITIAL):
    remesh_modifier = mesh_obj.modifiers.new(name="VoxelRemesh", type='REMESH')
    remesh_modifier.mode = 'VOXEL'
    remesh_modifier.voxel_size = voxel_size # Adjust the voxel size for finer or coarser resolution
    remesh_modifier.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier="VoxelRemesh")

# Function to clean and fill the mesh
def clean_and_fill(mesh_obj, threshold_high, threshold_low, fill_holes=True):
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type="VERT")
    mesh = bmesh.from_edit_mesh(mesh_obj.data)
    bpy.ops.mesh.select_all(action='DESELECT')
    # Select vertices based on the Z-threshold
    for v in mesh.verts:
        if v.co.z > threshold_high or v.co.z < threshold_low:
            v.select = True
    bmesh.update_edit_mesh(mesh_obj.data)
    bpy.ops.mesh.delete(type='VERT')
    if fill_holes: # Fill holes if requested
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.fill_holes(sides=0)
    #Added later for clean-up    
    bpy.ops.mesh.remove_doubles(threshold=1e-6)
    bpy.ops.mesh.normals_make_consistent()
    
    bpy.ops.object.mode_set(mode='OBJECT')

# Function to create a circular or rectangular bevel profile
def create_bevel_profile(dimension, width=None):
    #bpy.ops.object.select_all(action='DESELECT')
    if BEVEL_TYPE == "CIRCLE":
        bpy.ops.curve.primitive_bezier_circle_add(radius=dimension, location=(0, 0, 0))
    elif BEVEL_TYPE == "RECTANGLE":
        bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
        rectangle = bpy.context.object
        rectangle.scale = (width, dimension, 1)
        bpy.ops.object.convert(target='CURVE')
        rectangle.data.dimensions = '2D'
        return rectangle
    return bpy.context.object

# Function to process a single file with a given dimension and export the result as an STL file
def process_file(file_path, dimension, index):
    points = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file, delimiter=' ')
        for row in reader:
            x, y, z = map(float, row)
            points.append((x, y, z))

    curve_data = bpy.data.curves.new(f'SplineCurve_{index}', type='CURVE')
    curve_data.dimensions = '3D'
    spline = curve_data.splines.new('NURBS')
    spline.points.add(len(points) - 1)
    for i, point in enumerate(points):
        spline.points[i].co = (point[0], point[1], point[2], 1)
  # Adjust the curve settings to ensure the first and last points are used
    spline.use_endpoint_u = True  # Ensures the curve passes through the first and last control points
    spline.order_u = 4  # Set the order (degree + 1) of the NURBS curve

    curve_obj = bpy.data.objects.new(f'SplineObject_{index}', curve_data)
    bpy.context.collection.objects.link(curve_obj)
    
    # Set spline resolution
    spline.resolution_u = 12  # Increase resolution for smoother paths

    bevel_obj = create_bevel_profile(dimension, width=RECTANGLE_WIDTH if BEVEL_TYPE == "RECTANGLE" else None)
    bpy.context.view_layer.objects.active = curve_obj
    curve_obj.data.bevel_mode = 'OBJECT'
    curve_obj.data.bevel_object = bevel_obj
    curve_obj.data.use_fill_caps = True
    
    # Ensure we are in object mode
    if bpy.context.view_layer.objects.active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Select the spline object
    curve_obj.select_set(True)

    bpy.ops.object.convert(target='MESH')
    mesh_obj = bpy.context.object # Assuming the active object is the mesh

    # ————————————————————————————
    # Add a Decimate modifier to reduce face/vertex count for large files if necessary
    #dec_mod = mesh_obj.modifiers.new(name="DecimateMod", type='DECIMATE')
    #dec_mod.ratio = 0.5       # keep 50% of faces (tweak this 0.0–1.0 to taste)
    # Optionally:
    # dec_mod.decimate_type = 'DISSOLVE'  # for planar-face merging instead of uniform reduction

    # Apply it immediately
    #bpy.context.view_layer.objects.active = mesh_obj
    #bpy.ops.object.modifier_apply(modifier=dec_mod.name)
    # ————————————————————————————
    
    apply_uniform_remesh(mesh_obj, voxel_size=VOXEL_SIZE_UNIFORM_INITIAL)
    clean_and_fill(mesh_obj, THRESHOLD_HIGH, THRESHOLD_LOW, fill_holes=True)
    #apply_final_remesh(mesh_obj, voxel_size=VOXEL_SIZE_UNIFORM)
    bpy.data.objects.remove(bevel_obj, do_unlink=True)

    combined_paths = export_combined_paths_as_stl('combined_paths.stl')  # Export combined paths as STL
    
    # Optionally, delete the curve object after exporting
    #bpy.data.objects.remove(curve_obj, do_unlink=True)

# Read dimensions from the input file
dimensions = []
with open(f'{SELECTED_PATH}input_dimension.txt', 'r') as file:
    reader = csv.reader(file, delimiter=' ')
    for row in reader:
        dimensions.append(float(row[0]))

# Process each file
for i in range(1, NUMBER_OF_FILES+1):
    file_path = f'{SELECTED_PATH}input_path_{i}.txt'
    dimension = dimensions[i - 1]
    process_file(file_path, dimension, i)
