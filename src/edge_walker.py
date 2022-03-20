import bpy
import bmesh
import random
from functools import reduce

def flat_map(array):
    return reduce(list.__add__, array)

def do_edges_share_vertex(e1, e2):
    return e1.verts[0] == e2.verts[0] or e1.verts[1] == e2.verts[0] or e1.verts[0] == e2.verts[1] or e1.verts[1] == e2.verts[1]

def shared_vert(e1, e2):
    for v1 in e1.verts:
        for v2 in e2.verts:
            if v1 == v2:
                return v1
    return None

def find_next_edge_in_loop(e, v):
    v_comp = e.other_vert(v)
    #print('>> getNextEdgeInLoop:',e,v,'len(loops)=',len(e.link_loops))
    for ll in e.link_loops:
        for radial_continuation in [ll.link_loop_prev.link_loop_radial_next, ll.link_loop_next.link_loop_radial_next]:
            #print('!radial_continuation_edge=', radial_continuation.edge.index)
            #we don't know the direction, so just pick the next/prev that has a vertex on current edge
            for continuation_edge in [radial_continuation.link_loop_prev.edge, radial_continuation.link_loop_next.edge]:
                other_v = continuation_edge.other_vert(v_comp)
                if other_v != None and e != continuation_edge: #edge is connected to current one
                    return continuation_edge
    return None

def random_next_edge_after_turn(e, v):
    v_comp = e.other_vert(v)
    choices = flat_map([ll.link_loop_prev, ll.link_loop_next] for ll in e.link_loops)
    # if loop.edge.other_vert(v) == None]
    #for c in choices:
    #    print('> choice=', c.edge.index)
    choices = list(filter(lambda loop: loop.edge.other_vert(v_comp) != None, choices))
    #print('> choice.len=', len(choices))
    return random.choice(choices).edge


class EdgeWalker:
    def __init__(self, bmesh):
        self.bmesh = bmesh
        self.traversed_verts = set()#doesn't contain other_vert of current_edge initially
        self.traversed_edges = set()
        self.edge_count_by_vert = dict()

    def start(self, start_edge, start_vert):
        #print('walker start at v=', start_vert.index)
        self.current_edge = start_edge
        self.current_vert = start_vert
        self.current_path = list()
        self.current_path_corners = list()
        self.__mark_current_traversed()
        #self.traversed_verts.add(self.current_edge.other_vert(self.current_vert))
        
    def __add_edge_count(self, vert):
        #print('add_cnt', vert.index)
        cnt = self.edge_count_by_vert.get(vert)
        if cnt == None:
            cnt = 0
        self.edge_count_by_vert[vert] = cnt + 1
    
    def __mark_current_traversed(self):
        if self.current_vert != None:
            self.traversed_verts.add(self.current_vert)
            self.current_path.append(self.current_vert)
        if self.current_edge != None:
            for v in self.current_edge.verts:
                self.__add_edge_count(v)
            self.traversed_edges.add(self.current_edge)

    def forward(self):
        #print('forward')
        next_edge = find_next_edge_in_loop(self.current_edge, self.current_vert)
        self.current_vert = self.current_edge.other_vert(self.current_vert)
        self.current_edge = next_edge
        self.__mark_current_traversed()

    def turn(self):
        #print('turn')
        self.current_path_corners.append(self.current_vert)
        next_edge = random_next_edge_after_turn(self.current_edge, self.current_vert)
        self.current_vert = self.current_edge.other_vert(self.current_vert)
        self.current_edge = next_edge
        self.__mark_current_traversed()
    
    def log(self):
        if self.is_valid():
            print('> walker v=',self.current_vert.index,'e=',self.current_edge.index)
        else:
            print('> walker not valid')
        
    def is_valid(self):
        return self.current_vert != None and self.current_edge != None
    
    def ends_at_traversed_vertex(self):
        other = self.current_edge.other_vert(self.current_vert)
        return other in self.traversed_verts

    # If current path ended on itself, returns list of vertices in the "loop", None otherwise
    def current_path_loop_until_current_vertex(self, corners_only):
        if self.is_valid() == False:
            return None
        segment = list()
        if self.ends_at_traversed_vertex():
            endpoint = self.current_edge.other_vert(self.current_vert)
            for v in reversed(self.current_path):
                if v == endpoint:
                    return segment
                if corners_only == False or v in self.current_path_corners:
                    segment.append(v)
        return None
    
    def first_open_vert(self):
        #print('edge_count_by_vert=', self.edge_count_by_vert)
        for vert, count in self.edge_count_by_vert.items():
            if count == 1:
                return vert
        return None
    
    def random_non_traversed_vert(self):
        choices = list(vert for vert in self.bmesh.verts if vert not in self.traversed_verts)
        if len(choices) == 0:
            return None
        return random.choice(choices)
    
    def random_bi_connected_vert(self):
        choices = list(vert for vert, count in self.edge_count_by_vert.items() if count == 2)
        if len(choices) == 0:
            return None
        return random.choice(choices)
    
    def random_non_traversed_edge_from_vertex(self, vert):
        if vert == None:
            return None
        choices = list()
        for ll in vert.link_loops:
            for ll2 in [ll, ll.link_loop_prev]:#prev shares the vert but has a different edge
                if ll2.edge not in self.traversed_edges:
                    choices.append(ll2.edge)
                
        #choices = list(ll.edge for ll in vert.link_loops if ll.edge not in self.traversed_edges)
        if len(choices) == 0:
            return None
        return random.choice(choices)
  

#TODO: maybe add an option to subdivide before applying operator?
#bmesh.ops.subdivide_edges(bm,
#                          edges=bm.edges,
#                          cuts=1,
#                          use_grid_fill=True,
#                          )
    
#test code for walking forward
#while edge_walker.is_valid():
#    edge_walker.forward()
#    edge_walker.log()
#    if edge_walker.current_edge != None:
#        edge_walker.current_edge.select = True
