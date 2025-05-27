import bpy
import bmesh

# Function to calculate the volume of the selected mesh
def calculate_volume(obj):
    # Save the current mode
    initial_mode = obj.mode
    
    try:
        # Ensure the object is in object mode for bmesh operations
        if initial_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Create a new bmesh representation
        bm = bmesh.new()
        
        # Load the mesh data from the object
        bm.from_mesh(obj.data)
        
        # Ensure the mesh is triangulated for volume calculation
        bmesh.ops.triangulate(bm, faces=bm.faces)
        
        # Calculate the volume using the bmesh geometry
        volume = bm.calc_volume(signed=True)
        print(f"Volume of {obj.name}: {volume} cubic units")
        
        # Store the volume as a custom property on the object
        obj["Volume"] = volume
        
    except Exception as e:
        print(f"Error calculating volume: {e}")
        volume = None
    
    finally:
        # Free the bmesh and revert the mode
        bm.free()
        bpy.ops.object.mode_set(mode=initial_mode)
    
    return volume

# Usage:
obj = bpy.context.view_layer.objects.active  # Get the active object in the scene

if obj is None:
    print("No object is selected.")
elif obj.type == 'MESH':
    calculate_volume(obj)
else:
    print(f"{obj.name} is not a mesh object.")
