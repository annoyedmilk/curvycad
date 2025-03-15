"""KiCad plugin to generate linear stepper track traces in KiCad"""


import pcbnew
import curvycad as cc
import os
import traceback
import wx

WIDTH=10.0
PITCH=4.0
WIDTH_MARGIN = 1.2
LINE_WIDTH = 0.45
VIA_DRILL = 0.2
VIA_PAD = 0.45
GUIDE_RAIL_WIDTH = 1.25
GUIDE_RAIL_SPACE = 6 + GUIDE_RAIL_WIDTH
CU_CLEARANCE = 0.2
OUTER_MARKING_WIDTH = 2.0

# Define a single cycle of a periodic pattern which is projected along the
# path. Points along the track are normalized to the range (0, 1), and they are
# expanded based on the computed pitch later. 
# Transverse distances -- positions left and right of the track are absolute and
# in millimeters. 
# This definition defines two tracks, one on the left of the centerline and one
# on the right. Each track has two guard rails on the bottom layer, and two 
# alternating drive phases.
TRACK_CENTER = 0.0
TRACK_MINOR = WIDTH / 2
TRACK_MAJOR = WIDTH / 2 + VIA_PAD / 2 + CU_CLEARANCE + LINE_WIDTH / 2
segment = [
    
    # Silkscreen
    cc.ParallelLine(0.0, 1.0, TRACK_CENTER + TRACK_MAJOR + OUTER_MARKING_WIDTH / 2, OUTER_MARKING_WIDTH, pcbnew.F_SilkS),
    cc.ParallelLine(0.0, 1.0, -(TRACK_CENTER + TRACK_MAJOR + OUTER_MARKING_WIDTH / 2), OUTER_MARKING_WIDTH, pcbnew.F_SilkS),
    #cc.ParallelLine(0.25, 0.75, 0.0, LANE_SEPARATOR_WIDTH, pcbnew.F_SilkS),

    # Guard rails
    cc.ParallelLine(0.0, 1.0, -GUIDE_RAIL_SPACE / 2, GUIDE_RAIL_WIDTH, pcbnew.F_Cu),
    cc.ParallelLine(0.0, 1.0, GUIDE_RAIL_SPACE / 2, GUIDE_RAIL_WIDTH, pcbnew.F_Cu),
    
    # Track 1 Phase A
    cc.TransverseLine(
        start=-(TRACK_CENTER - TRACK_MINOR),
        end=-(TRACK_CENTER + TRACK_MAJOR),
        offset=0,
        width=LINE_WIDTH,
        layer=pcbnew.In1_Cu,
    ),
    cc.ParallelLine(
        start=0,
        end=0.5,
        offset=-(TRACK_CENTER + TRACK_MAJOR),
        width=LINE_WIDTH,
        layer=pcbnew.In1_Cu,
    ),
    cc.TransverseLine(
        start=-(TRACK_CENTER + TRACK_MAJOR),
        end=-(TRACK_CENTER - TRACK_MINOR),
        offset=0.5,
        width=LINE_WIDTH,
        layer=pcbnew.In1_Cu,
    ),
    cc.Via(0.5, -(TRACK_CENTER - TRACK_MINOR), drill=VIA_DRILL, pad=VIA_PAD),
    cc.ParallelLine(
        start=0.5, 
        end=1.0,
        offset=-(TRACK_CENTER - TRACK_MINOR),
        width=LINE_WIDTH,
        layer=pcbnew.In2_Cu,
    ),
    cc.Via(1.0, -(TRACK_CENTER - TRACK_MINOR), drill=VIA_DRILL, pad=VIA_PAD),
    
    # Track 1 Phase B
    cc.ParallelLine(
        start=0.0, 
        end=0.25,
        offset=-(TRACK_CENTER - TRACK_MAJOR),
        width=LINE_WIDTH,
        layer=pcbnew.In1_Cu,
    ),
    cc.TransverseLine(
        start=-(TRACK_CENTER - TRACK_MAJOR),
        end=-(TRACK_CENTER + TRACK_MINOR),
        offset=0.25,
        width=LINE_WIDTH,
        layer=pcbnew.In1_Cu,
    ),
    cc.Via(0.25, -(TRACK_CENTER + TRACK_MINOR), drill=VIA_DRILL, pad=VIA_PAD),
    cc.ParallelLine(
        start=0.25,
        end=0.75,
        offset=-(TRACK_CENTER + TRACK_MINOR),
        width=LINE_WIDTH,
        layer=pcbnew.In2_Cu,
    ),
    cc.Via(0.75, -(TRACK_CENTER + TRACK_MINOR), drill=VIA_DRILL, pad=VIA_PAD),
    cc.TransverseLine(
        start=-(TRACK_CENTER + TRACK_MINOR),
        end=-(TRACK_CENTER - TRACK_MAJOR),
        offset=0.75,
        width=LINE_WIDTH,
        layer=pcbnew.In1_Cu,
    ),
    cc.ParallelLine(
        start=0.75, 
        end=1.00,
        offset=-(TRACK_CENTER - TRACK_MAJOR),
        width=LINE_WIDTH,
        layer=pcbnew.In1_Cu,
    ),
]

# Custom version of KicadTrackBuilder with fixes for KiCad 9.0
class FixedKicadTrackBuilder(cc.KicadTrackBuilder):
    def point_to_vector2i(self, p):
        """Convert a coordinate to a VECTOR2I object"""
        return pcbnew.VECTOR2I(int(p[0] * 1e6), int(p[1] * 1e6))
    
    def emit_line(self, p0, p1, width, layer):
        """Fixed version of emit_line for KiCad 9.0 compatibility"""
        if layer in self.routing_layers:
            track = pcbnew.PCB_TRACK(self.board)
        else:
            track = pcbnew.PCB_SHAPE(self.board)
            track.SetShape(pcbnew.SHAPE_T_SEGMENT)
            
        # Convert to VECTOR2I for start and end points
        start_point = self.point_to_vector2i(p0)
        end_point = self.point_to_vector2i(p1)
        
        track.SetStart(start_point)
        track.SetEnd(end_point)
        track.SetWidth(int(width * 1e6))
        track.SetLayer(layer)
        self.board.Add(track)
        self.group.AddItem(track)

    def emit_arc(self, start, mid, end, width, layer):
        """Fixed version of emit_arc for KiCad 9.0 compatibility"""
        # Convert points to VECTOR2I
        start_point = self.point_to_vector2i(start)
        mid_point = self.point_to_vector2i(mid)
        end_point = self.point_to_vector2i(end)
        
        if layer in self.routing_layers:
            # For routing layers, use PCB_ARC
            track = pcbnew.PCB_ARC(self.board)
            track.SetStart(start_point)
            track.SetMid(mid_point)
            track.SetEnd(end_point)
        else:
            # For other layers, use PCB_SHAPE as an arc
            track = pcbnew.PCB_SHAPE(self.board)
            track.SetShape(pcbnew.SHAPE_T_ARC)
            
            # For KiCad 9.0, we need to use SetArcGeometry with correct parameter types
            track.SetArcGeometry(start_point, mid_point, end_point)

        track.SetWidth(int(width * 1e6))
        track.SetLayer(layer)
        self.board.Add(track)
        self.group.AddItem(track)
    
    def emit_via(self, p, drill, pad):
        """Fixed version of emit_via for KiCad 9.0 compatibility"""
        # Try first to create a proper PCB_VIA
        try:
            via = pcbnew.PCB_VIA(self.board)
            position = self.point_to_vector2i(p)
            via.SetPosition(position)
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetDrill(int(drill * 1e6))
            via.SetWidth(int(pad * 1e6))  # Set via diameter
            self.board.Add(via)
            self.group.AddItem(via)
            return
        except Exception as e:
            print(f"Warning: Could not create via using PCB_VIA at {p}. Error: {e}")
        
        # Fall back to footprint approach if PCB_VIA fails
        try:
            module = pcbnew.FOOTPRINT(self.board)
            position = self.point_to_vector2i(p)
            module.SetPosition(position)
            module.SetReference("")
            module.SetValue("")
            
            pad_item = pcbnew.PAD(module)
            pad_item.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad_item.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
            pad_item.SetSize(pcbnew.VECTOR2I(int(pad * 1e6), int(pad * 1e6)))
            pad_item.SetPosition(position)
            pad_item.SetDrillSize(pcbnew.VECTOR2I(int(drill * 1e6), int(drill * 1e6)))
            pad_item.SetNumber("")
            
            module.Add(pad_item)
            self.board.Add(module)
            self.group.AddItem(module)
        except Exception as e2:
            print(f"Error creating via using footprint fallback: {e2}")

class TrackLayout(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Insert Gauss Speedway race track"
        self.category = "Modify PCB"
        self.description = "Insert Gauss Speedway race track"
        self.show_toolbar_button = True

    def Run(self):
        board = pcbnew.GetBoard()
        projdir = os.path.dirname(os.path.abspath(board.GetFileName()))
        
        # Create dialog to choose between default path or custom file
        dlg = wx.MessageDialog(None, 
                             "Do you want to use the default track.dxf in the project directory or select a custom file?",
                             "Track DXF Selection",
                             wx.YES_NO | wx.ICON_QUESTION)
        dlg.SetYesNoLabels("Default track.dxf", "Select Custom File")
        
        try:
            use_default = dlg.ShowModal() == wx.ID_YES
            dlg.Destroy()
            
            if use_default:
                # Use track.dxf from project directory
                dxf_file = os.path.join(projdir, 'track.dxf')
                if not os.path.exists(dxf_file):
                    wx.MessageBox(f"Default track.dxf not found in project directory: {projdir}", 
                                 "File Not Found", wx.OK | wx.ICON_ERROR)
                    return
            else:
                # Let user choose file
                with wx.FileDialog(None, "Select Track DXF file", wildcard="DXF files (*.dxf)|*.dxf",
                                 style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
                    
                    if fileDialog.ShowModal() == wx.ID_CANCEL:
                        return  # User canceled
                        
                    dxf_file = fileDialog.GetPath()
            
            try:
                guide = cc.read_dxf(dxf_file)
                for el in guide:
                    print(el)
                
                # Use the fixed track builder for KiCad 9.0 compatibility
                track = FixedKicadTrackBuilder(PITCH, segment, board)
                track.draw_path(guide)
                
                # Refresh the board
                pcbnew.Refresh()
                
            except Exception as e:
                error_msg = f"Error: {str(e)}\n\n{traceback.format_exc()}"
                wx.MessageBox(error_msg, "Error", wx.OK | wx.ICON_ERROR)
                
        except Exception as e:
            print(f"Dialog error: {str(e)}\n\n{traceback.format_exc()}")
   

TrackLayout().register()