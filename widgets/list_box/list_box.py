# list_box.py: wxListBox objects
#
# Copyright (c) 2002-2003 Alberto Griggio <albgrig@tiscalinet.it>
# License: MIT (see license.txt)
# THIS PROGRAM COMES WITH NO WARRANTY

from wxPython.wx import *
import common, misc
from edit_windows import ManagedBase
from tree import Tree
from widget_properties import *
from ChoicesProperty import *

class EditListBox(ManagedBase):
    def __init__(self, name, parent, id, choices, sizer, pos, property_window,
                 show=True):
        """\
        Class to handle wxListBox objects
        """
        ManagedBase.__init__(self, name, 'wxListBox', parent, id, sizer,
                             pos, property_window, show=show)
        self.selection = 0
        self.choices = choices
        # properties
        self.access_functions['choices'] = (self.get_choices, self.set_choices)
        self.properties['choices'] = ChoicesProperty(self, 'choices', None,
                                                     [('Label',
                                                       GridProperty.STRING)],
                                                     len(choices))
        self.access_functions['selection'] = (self.get_selection,
                                              self.set_selection)
        self.style = 0
        self.access_functions['style'] = (self.get_style, self.set_style)
        self.properties['selection'] = SpinProperty(self, 'selection', None,
                                                    r=(0, len(choices)-1))
        self.style_pos  = (wxLB_SINGLE, wxLB_MULTIPLE, wxLB_EXTENDED,
                           wxLB_HSCROLL, wxLB_ALWAYS_SB, wxLB_NEEDED_SB,
                           wxLB_SORT)
        style_labels  = ('#section#Style', 'wxLB_SINGLE', 'wxLB_MULTIPLE',
                         'wxLB_EXTENDED', 'wxLB_HSCROLL', 'wxLB_ALWAYS_SB',
                         'wxLB_NEEDED_SB', 'wxLB_SORT')
        self.properties['style'] = CheckListProperty(self, 'style', None,
                                                     style_labels)
        
    def create_widget(self):
        self.widget = wxListBox(self.parent.widget, self.id,
                                choices=self.choices)
        self.set_selection(self.selection)
        EVT_LEFT_DOWN(self.widget, self.on_set_focus)        

    def create_properties(self):
        ManagedBase.create_properties(self)
        panel = wxScrolledWindow(self.notebook, -1)
        szr = wxBoxSizer(wxVERTICAL)
        self.properties['choices'].display(panel)
        self.properties['style'].display(panel)
        self.properties['selection'].display(panel)
        szr.Add(self.properties['style'].panel, 0, wxEXPAND)
        szr.Add(self.properties['selection'].panel, 0, wxEXPAND)
        ch = self.properties['choices'].panel
        ch.SetSize((ch.GetSize()[0]-20, 200))
        szr.Add(self.properties['choices'].panel, 0, wxEXPAND)
        panel.SetAutoLayout(True)
        panel.SetSizer(szr)
        szr.Fit(panel)
        w, h = panel.GetSize()
        from math import ceil
        panel.SetScrollbars(5, 5, ceil(w/5.0), ceil(h/5.0))
        self.notebook.AddPage(panel, 'Widget')
        self.properties['choices'].set_col_sizes([-1])
        
    def get_property_handler(self, prop_name):
        if prop_name == 'choices':
            return ChoicesHandler(self)
        return ManagedBase.get_property_handler(self, prop_name)

    def get_choices(self):
        return zip(self.choices)

    def set_choices(self, values):
        self.choices = [ v[0] for v in values ]
        self.properties['selection'].set_range(0, len(self.choices)-1)
        if self.widget:
            self.widget.Clear()
            for c in self.choices: self.widget.Append(c)
            if not self.properties['size'].is_active():
                self.sizer.set_item(self.pos, size=self.widget.GetBestSize())
            self.widget.SetSelection(
                int(self.properties['selection'].get_value()))

    def get_style(self):
        retval = [0] * len(self.style_pos)
        try:
            for i in range(len(self.style_pos)):
                if self.style & self.style_pos[i]:
                    retval[i] = 1
        except AttributeError: pass
        return retval

    def set_style(self, value):
        value = self.properties['style'].prepare_value(value)
        self.style = 0
        for v in range(len(value)):
            if value[v]:
                self.style |= self.style_pos[v]
        if self.widget: self.widget.SetWindowStyleFlag(self.style)

    def get_selection(self):
        return self.selection

    def set_selection(self, value):
        value = int(value)
        if value != self.selection:
            self.selection = value
            if self.widget:
                self.widget.SetSelection(value)

# end of class EditListBox


def builder(parent, sizer, pos, number=[1]):
    """\
    factory function for EditListBox objects.
    """
    name = 'list_box_%d' % number[0]
    while common.app_tree.has_name(name):
        number[0] += 1
        name = 'list_box_%d' % number[0]
    list_box = EditListBox(name, parent, wxNewId(),
                           [misc._encode('choice 1')], sizer, pos,
                           common.property_panel)
    node = Tree.Node(list_box)
##     sizer.set_item(pos, size=list_box.GetBestSize())
    list_box.node = node
    list_box.show_widget(True)
    common.app_tree.insert(node, sizer.node, pos-1)

def xml_builder(attrs, parent, sizer, sizeritem, pos=None):
    """\
    factory to build EditListBox objects from an xml file
    """
    from xml_parse import XmlParsingError
    try: name = attrs['name']
    except KeyError: raise XmlParsingError, "'name' attribute missing"
    if sizer is None or sizeritem is None:
        raise XmlParsingError, "sizer or sizeritem object cannot be None"
    list_box = EditListBox(name, parent, wxNewId(), [], sizer, pos,
                           common.property_panel)
    sizer.set_item(list_box.pos, option=sizeritem.option,
                   flag=sizeritem.flag, border=sizeritem.border)
##                    size=list_box.GetBestSize())
    node = Tree.Node(list_box)
    list_box.node = node
    if pos is None: common.app_tree.add(node, sizer.node)
    else: common.app_tree.insert(node, sizer.node, pos-1)
    return list_box

    
def initialize():
    """\
    initialization function for the module: returns a wxBitmapButton to be
    added to the main palette.
    """
    common.widgets['EditListBox'] = builder
    common.widgets_from_xml['EditListBox'] = xml_builder

    return common.make_object_button('EditListBox', 'icons/list_box.xpm')
