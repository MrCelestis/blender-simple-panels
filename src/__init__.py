bl_info = {
    "name": "Simple panels",
    "blender": (2, 80, 0),
    "category": "Object",
}

if "bpy" in locals():
    import importlib
    if "edge_walker" in locals():
        importlib.reload(edge_walker)

import bpy

from . import (
    edge_walker
)
import bpy
import bmesh
import random
  
class SimplePanels(bpy.types.Operator):
    """Simple panel generator"""      # Use this as a tooltip for menu items and buttons.
    bl_idname = "object.simple_panels"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Simple panels"         # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.
    forward_chance: bpy.props.FloatProperty(name="Forward walk", default=0.65, min=0, max=1)
    bevel_panel_corners: bpy.props.BoolProperty(name="Bevel panel corners", default=False)

    @classmethod
    def poll(cls, context):
        return context.edit_object is not None

    def invoke(self, context, event):
        return self.execute(context)
    
    def cancel(self, context):
        self.report({'INFO'}, 'Cancel')

    def execute(self, context):        # execute() is called when running the operator.

        self.report(
            {'INFO'}, 'Fwd chance: %.2f  bevel corners: %s' %
            (self.forward_chance, self.bevel_panel_corners)
        )
        mesh = context.edit_object.data
        bm = bmesh.from_edit_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        
        start_edge = random.choice(bm.edges)
        start_vert = random.choice(start_edge.verts)
        
        random.seed(100) #TODO: take seed from property
        walker = edge_walker.EdgeWalker(bm)
        walker.start(start_edge, start_vert)

        self.walk(walker)

        if self.bevel_panel_corners:
            self.cut_corners(bm, walker.traversed_edges)

        #TODO: for now just select the edges
        for e in walker.traversed_edges:
            e.select = True
        bm.select_flush_mode()

        bmesh.update_edit_mesh(mesh)

        self.report(
            {'INFO'}, "Traversed edges: %d; has open vert: %s" %
            (len(walker.traversed_edges), walker.first_open_vert() != None)
        )

        return {'FINISHED'} # Lets Blender know the operator finished successfully.
    
    def walk(self, walker):
        while True:
            while walker.is_valid() and not walker.ends_at_traversed_vertex():
                if random.random() < self.forward_chance:
                    walker.forward()
                else:
                    walker.turn()
            #Try to pick starting vertex and edge for next walk.
            #Open edges (random edge from vertex with only 1 traversed edge) are always processed.
            #The rest depends on random with the following priority:
            #- vertices with 2 connected traversed edges at corners - TODO
            #- vertices with 2 connected traversed edges
            #- non-traversed vertices
            next_iteration_vert = walker.first_open_vert()
            #try to pick a non-traversed edge starting from first_open_vert
            next_iteration_edge = walker.random_non_traversed_edge_from_vertex(next_iteration_vert)
            if next_iteration_edge == None or next_iteration_vert == None:
                #try random pick: vertices with 2 connected traversed edges
                if random.random() < 0.5:
                    next_iteration_vert = walker.random_bi_connected_vert()
                    next_iteration_edge = walker.random_non_traversed_edge_from_vertex(next_iteration_vert)
                elif random.random() < 0.5:
                    next_iteration_vert = walker.random_non_traversed_vert()
                    next_iteration_edge = walker.random_non_traversed_edge_from_vertex(next_iteration_vert)
            if next_iteration_edge == None or next_iteration_vert == None:
                if random.random() < 0.1:
                    return
            #if there is a continuation, continue walk
            walker.start(next_iteration_edge, next_iteration_vert)
    
    def cut_corners(self, bm, traversed_edges):
        affected_verts = set()
        result = list()
        for face in bm.faces:
            if len(face.edges) != 4:
                continue
            traversed_cnt = sum(1 for e in face.edges if e in traversed_edges)
            if traversed_cnt != 2:
                continue
            for i in range(0, 4):
                cur_edge = face.edges[i]
                next_edge = face.edges[(i + 1) % 4]
                if cur_edge in traversed_edges and next_edge in traversed_edges:
                    vert = shared_vert(cur_edge, next_edge)
                    if vert in affected_verts:
                        continue
                    #need to connect to only 2 traversed edges (effectively being the edges of current face)
                    #can't be boundary, thus must have 4 link loops
                    traversed_link_edges = list(e for e in vert.link_edges if e in traversed_edges)
                    if len(traversed_link_edges) == 2 and len(vert.link_loops) == 4:
                        cur_other_vert = cur_edge.other_vert(vert)
                        next_other_vert = next_edge.other_vert(vert)
                        if cur_other_vert in affected_verts or next_other_vert in affected_verts:
                            continue
                        vert.co = (cur_other_vert.co + next_other_vert.co) * 0.5
                        affected_verts.add(vert)
                        affected_verts.add(cur_other_vert)
                        affected_verts.add(next_other_vert)
                        #print("vert for cut:", vert)
                
        return result

#TODO: move away
def shared_vert(e1, e2):
    for v1 in e1.verts:
        for v2 in e2.verts:
            if v1 == v2:
                return v1
    return None        

def menu_func(self, context):
    self.layout.operator(SimplePanels.bl_idname)

def register():
    bpy.utils.register_class(SimplePanels)
    bpy.types.VIEW3D_MT_edit_mesh.append(menu_func)  # Adds the new operator to an existing menu.

def unregister():
    bpy.utils.unregister_class(SimplePanels)


# This allows you to run the script directly from Blender's Text editor
# to test the add-on without having to install it.
# Solutions for duplicate menu items: https://blender.stackexchange.com/questions/3394/adding-custom-menu-run-script-button-causes-duplicate
if __name__ == "__main__":
    register()
