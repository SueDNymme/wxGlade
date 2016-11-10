"""Classes to handle the various properties of the widgets (name, size, colour, etc.)

File has been created in 2016; parts are from the old version of widget_properties.py:
@copyright: 2002-2007 Alberto Griggio, 2012-2016 Carsten Grohmann

Interface to owner modified; see below for class PropertyOwner

@copyright: 2016 Dietmar Schwertberger
@license: MIT (see LICENSE.txt) - THIS PROGRAM COMES WITH NO WARRANTY
"""

import common, config, compat, logging, misc
from collections import OrderedDict
import re
import wx

class _DefaultArgument(object):
    pass
_DefaultArgument = _DefaultArgument()

class Property(object):
    "Base class for property editors"
    deactivated = None # None: can not be deactivated; otherwise bool value
    readonly = False
    TOOLTIP = None
    LABEL = None # defaults to property name
    CONTROLNAMES = ["enabler"]  # for activation; also these attributes will be set to None when the editor is destroyed
    GROW = False # if this is True, no spacer is added after the control, so it may grow down to the lower edge
    def __init__(self, value, default_value=_DefaultArgument, name=None):#, write_always=False):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.value = value
        # when the property is assigned to an instance property, these will be set:
        self.owner = None
        self.name = name
        self.attributename = None
        self.modified = False  # either by the user or from loaded file; WidgetStyleProperty.write uses it
        # this can be set to True by the owner, depending on another property value; value will still be written to XML
        self.blocked = False
        self.default_value = default_value
        self.controls = None
        self.editing = False
    def set_owner(self, owner, attributename=None):
        self.owner = owner
        self.attributename = attributename
        if self.name is None: self.name = attributename
    ####################################################################################################################
    # the interface from owner and application
    def get(self):
        "get the value, or the default value if deactivated; usually not used directly, as owner.property will call it"
        if not self.deactivated:
            return self.value
        return self.default_value
    get_value = get  # XXX remove again?

    def _set_converter(self, value):
        return value

    def set(self, value, activate=None, deactivate=None, notify=False):
        """set the value of the property (note that the property need not be active)
        updates display if editor is visible; doesn't notify owner or application!
        optionally, the property will be activated or deactivated"""
        self.value = self._set_converter(value)
        self.modified = True
        if activate is None and deactivate is None:
            self.update_display()
            if notify: self._notify()
            return

        if activate and self.deactivated:
            self.set_active(True)  # set active will call update_display
        elif deactivate and not self.deactivated:
            self.set_active(False)
        else:
            self.update_display()
        if notify: self._notify()

    def load(self, value, activate=None, deactivate=None, notify=False):
        # called from xml_parse ... add_property(self, name, val)
        # a derived class like TextProperty may implement a load method, e.g. to unescape strings
        # (this should actually handled by xml_parse itself, but this might have side effects)
        self.set(value, activate, deactivate, notify)

    def set_default(self, default_value):
        default_value = self._set_converter(default_value)
        if default_value==self.default_value: return
        self.default_value = default_value
        if self.is_active(): return
        self.value = default_value
        self.update_display()

    def is_active(self):
        "check whether property is not deactivated"
        return not self.deactivated

    def set_active(self, active=True):
        "activates or deactivates the property; updates display if editor is visible; doesn't notify owner or application!"
        #assert self.default_value is not _DefaultArgument
        if active and not self.deactivated: return
        if not active and self.deactivated: return
        self.deactivated = not active
        self.update_display()
        self.activate_controls()

    def set_blocked(self, block=True):
        if block and self.blocked: return
        if not block and not self.blocked: return
        self.blocked = block
        self.activate_controls()

    ####################################################################################################################
    # internal interface from the editor controls
    def on_value_edited(self, value):
        """called from self when the user has entered a new value
        controls need not to be set, but the owner needs to be notified and the application"""
        self.set(value)
        self._notify()

    def on_activated(self, active=True):
        "activation checkbox toggled"
        # XXX  assert self.default_value is not _DefaultArgument
        if active != self.deactivated: return
        self.deactivated = not active
        self.activate_controls()
        self.owner.properties_changed([self.name])

    def _check_for_user_modification(self, new_value, force=False):
        # force: set to True when e.g. called from self.toggle_activate
        #new_value =
        if new_value == self.value and not force: return False
        self.value = new_value
        self._notify()
        return True

    def _notify(self):
        self.modified = True
        common.app_tree.app.saved = False
        self.owner.properties_changed([self.name])

    def toggle_active(self, active=None, refresh=True):
        "Toggle the activation state"
        # active is not given when refreshing target and enabler
        if active != self.deactivated: return
        self.deactivated = not active
        for controlname in self.CONTROLNAMES:
            if controlname=="enabler": continue
            getattr(self, controlname).Enable(active)
        self._notify()
        self.activate_controls()

    ####################################################################################################################
    # XML file
    def get_str_value(self):
        if self.value is True:  return '1'
        if self.value is False: return '0'
        return str(self.value)

    def write(self, outfile, tabs=0):
        """Writes the xml code for this property onto the given file or file-like object.
        Argument tabs (int) is the indentation level.
        This is the default implementation."""
        if not self.is_active():
            return
        if self.default_value is not _DefaultArgument and self.value==self.default_value:
            # value is the default value -> not to be written
            return
        if self.value is None or isinstance(self.value, compat.basestring) and not self.value:
            # value is empty string
            return

        # get the value as string
        string_getter = getattr(self.owner, "get_%s_string"%self.attributename, None)
        if string_getter:
            value = string_getter()
            if not value: return
        else:
            value = self.get_str_value()
        # write the value
        stmt = common.format_xml_tag(self.name, value, tabs)
        outfile.write(stmt)

    ####################################################################################################################
    # editor (controls are added to common.property_panel)
    def create_editor(self, panel, sizer):
        # when done, call self.update_display(start_editing=True)
        return None  # default implementation: no editor (hidden property, not user editable)

    def destroy_editor(self):
        # delete e.g. references to controls
        for att in self.CONTROLNAMES:
            setattr(self, att, None)
        self.editing = False

    def update_display(self, start_editing=False):
        # when the value has changed
        # if start_editing: self.editing = True
        # if not self.editing: return
        pass

    def activate_controls(self):
        if not self.editing: return
        if self.blocked:
            active = False
        else:
            active = not self.deactivated

        for controlname in self.CONTROLNAMES:
            if controlname=="enabler": continue
            control = getattr(self, controlname, None)
            if control is None: continue
            if isinstance(control, (tuple,list)):
                for c in control:
                    if c is not None: c.Enable(active)
            else:
                control.Enable(active)

        if "enabler" in self.CONTROLNAMES and self.enabler is not None:
            self.enabler.Enable(not self.blocked)


    ####################################################################################################################
    # helpers
    def _mangle(self, label):
        "Returns a mangled version of label, suitable for displaying the name of a property"
        return misc.wxstr(misc.capitalize(label).replace('_', ' '))
    def _find_label(self):
        "check self.LABEL; then go through base classes and check the _PROPERTY_LABELS dictionaries"
        if self.LABEL: return self.LABEL
        import inspect

        classes = inspect.getmro(self.owner.__class__)
        for cls in classes:
            if not hasattr(cls, "_PROPERTY_LABELS"): continue
            if self.name in cls._PROPERTY_LABELS:
                return cls._PROPERTY_LABELS[self.name]
        return self._mangle(self.name)
    def _find_tooltip(self):
        "go through base classes and check the _PROPERTY_HELP dictionaries"
        if self.TOOLTIP: return self.TOOLTIP
        import inspect

        classes = inspect.getmro(self.owner.__class__)
        for cls in classes:
            if not hasattr(cls, "_PROPERTY_HELP"): continue
            if self.name in cls._PROPERTY_HELP:
                return cls._PROPERTY_HELP[self.name]
        return None
    def _set_tooltip(self, *controls):
        tooltip = self._find_tooltip()
        if not tooltip: return
        for c in controls:
            if not c or c.GetToolTip(): continue
            compat.SetToolTip(c, tooltip)


# these classes are not really used, as they don't have an editor:
class PropertyA(Property):
    # can be activated/deactivated; active by default
    deactivated = False

class PropertyD(Property):
    # can be activated/deactivated; deactivated by default
    deactivated = True

class PropertyRO(Property):
    # can be activated/deactivated; deactivated by default
    readonly = True


class SpinProperty(Property):
    # int
    CONTROLNAMES = ["enabler", "spin"]
    def __init__(self, value, val_range=(0,1000), immediate=False, default_value=_DefaultArgument, name=None):
        # val_range: (min_value,max_value)
        if isinstance(val_range, int):    # we allow val_range to be supplied as integer
            if val_range<0 and value>=0:  # typically val_range is len(choices)-1  for empty choices
                value = val_range
                val_range = (val_range,val_range)
            elif val_range>=0:
                val_range = (0,val_range)
            else:
                val_range = (val_range,0)
        self.val_range = val_range
        self.immediate = immediate
        Property.__init__(self, value, default_value, name)

    def _set_converter(self, value):
        return int(value)

    def create_editor(self, panel, sizer):
        if self.val_range is None:
            self.val_range = (0, 1000)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        # label
        label = self._find_label()
        label = wx.lib.stattext.GenStaticText( panel, -1, label, size=(config.label_width, -1) )
        #hsizer.Add(label, 2, wx.ALL | wx.ALIGN_CENTER, 3)
        hsizer.Add(label, 0, wx.ALL | wx.ALIGN_CENTER, 3)
        # checkbox, if applicable
        self.enabler = None
        if self.deactivated is not None:
            self.enabler = wx.CheckBox(panel, -1, '')#, size=(1,-1))
            self.enabler.SetValue(not self.deactivated)
            self.enabler.Bind( wx.EVT_CHECKBOX, lambda event: self.toggle_active(event.IsChecked()) )
            hsizer.Add(self.enabler, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 3)
        #else:
            #hsizer.AddSpacer(20)
        # the spin control
        #if self.val_range[1] is None:
            #self.spin = wx.SpinCtrl( panel, -1, min=self.val_range[0] )
        #else:
        style = wx.TE_PROCESS_ENTER | wx.SP_ARROW_KEYS
        self.spin = wx.SpinCtrl( panel, -1, style=style, min=self.val_range[0], max=self.val_range[1] )
        val = self.value
        if not val: self.spin.SetValue(1)  # needed for GTK to display a '0'
        self.spin.SetValue(val)

        if self.deactivated is not None:
            self.spin.Enable(not self.deactivated)
        elif self.blocked or self.readonly:
            self.spin.Enable(False)

        # layout of the controls / sizers
        hsizer.Add(self.spin, 5, wx.ALL | wx.ALIGN_CENTER, 3)
        sizer.Add(hsizer, 0, wx.EXPAND)

        self._set_tooltip(label, self.spin, self.enabler)

        self.spin.Bind(wx.EVT_KILL_FOCUS, self.on_kill_focus) # by default, the value is only set when the focus is lost
        if wx.Platform == '__WXMAC__' or self.immediate:
            self.spin.Bind(wx.EVT_SPINCTRL, self.on_spin)
            self.spin.Bind(wx.EVT_TEXT_ENTER, self.on_spin)   # we want the enter key (see style above)
        self.editing = True

    def on_kill_focus(self, event):
        event.Skip()
        if self.spin is None: return
        if self.spin.IsBeingDeleted(): return
        if not compat.wxWindow_IsEnabled(self.spin): return  # XXX delete this?
        self._check_for_user_modification(self.spin.GetValue())

    def update_display(self, start_editing=False):
        if start_editing: self.editing = True
        if not self.editing: return
        self.spin.SetValue(self.value)

    def on_spin(self, event):
        event.Skip()
        self._check_for_user_modification(self.spin.GetValue())

    def set_range(self, min_v, max_v):
        new_range = (min_v, max_v)
        if new_range==self.val_range: return
        self.val_range = new_range
        try:
            self.spin.SetRange(min_v, max_v)
        except AttributeError:
            pass

    #def write(self, outfile, tabs=0):
        #if self.is_active():
            #Property.write(self, outfile, tabs)

class SpinPropertyA(SpinProperty):
    deactivated = False
class SpinPropertyD(SpinProperty):
    deactivated = True


def _is_gridbag(dummy):
    return False

class LayoutPosProperty(SpinProperty):
    readonly = True
    TOOLTIP = "Position of item within sizer; 1-based"

    def __init__(self, value, sizer):
        self.is_gridbag = _is_gridbag(sizer)
        SpinProperty.__init__(self, value, val_range=(1,1000), immediate=False, default_value=_DefaultArgument, name="pos")

    def set_sizer(self, sizer):
        self.is_gridbag = _is_gridbag(sizer)

    def write(self, *args, **kwds):
        pass



class CheckBoxProperty(Property):
    # bool
    CONTROLNAMES = ["checkbox"]

    def _set_converter(self, value):
        if isinstance(value, compat.basestring):
            return int(value) # keep 0/1 instead of False/True for writing to XML file
        return value

    def create_editor(self, panel, sizer):
        self.checkbox = wx.CheckBox(panel, -1, '')
        self.checkbox.SetValue( bool(self.value) )
        label = self._find_label()
        label_width = max(config.label_width, panel.GetTextExtent(label)[0])
        label = wx.lib.stattext.GenStaticText(panel, -1, label, size=(label_width, -1))
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        #hsizer.Add(label, 2, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        hsizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 3)
        #hsizer.SetItemMinSize(0, config.label_initial_width, -1)
        #hsizer.AddSpacer(20)
        hsizer.Add(self.checkbox, 0, wx.ALIGN_LEFT | wx.ALL, 3)
        hsizer.AddStretchSpacer(5)
        sizer.Add(hsizer, 0, wx.EXPAND)
        self._set_tooltip(label, self.checkbox)
        self.checkbox.Bind(wx.EVT_CHECKBOX, self.on_change_val)
        self.editing = True

    def update_display(self, start_editing=False):
        if start_editing: self.editing = True
        if not self.editing: return
        self.checkbox.SetValue(self.value)

    def on_change_val(self, event):
        new_value = event.IsChecked()
        self._check_for_user_modification(new_value)


class RadioProperty(Property):
    # choice
    CONTROLNAMES = ["options"]

    def __init__(self, value, values, labels=None, columns=1, aliases=None, tooltips=None, default_value=_DefaultArgument,
                 name=None):
        self.values = values    # e.g. a list of ints
        self.aliases = aliases  # e.g. a list of strings, corresponding to values; these can be set and will be written
        self.labels = labels or aliases or values
        self.tooltips = tooltips
        self.columns = columns
        Property.__init__(self, value, default_value, name)

    def _set_converter(self, value):
        if not value in self.values:
            value = self.values[self.aliases.index(value)]
        return value

    def get_str_value(self):
        if self.aliases and not self.value in self.aliases:
            return self.aliases[self.values.index(self.value)]
        return Property.get_str_value(self)

    def create_editor(self, panel, sizer):
        label = self._find_label()
        style = wx.RA_SPECIFY_COLS | wx.NO_BORDER | wx.CLIP_CHILDREN
        self.options = wx.RadioBox(panel, -1, label, choices=self.labels, majorDimension=self.columns, style=style)
        sizer.Add(self.options, 0, wx.EXPAND)

        if self.tooltips:
            for i,tooltip in enumerate(self.tooltips):
                if tooltip:
                    self.options.SetItemToolTip(i, tooltip)
        else:
            self._set_tooltip(self.options)

        self.update_display(True)
        self.options.Bind(wx.EVT_RADIOBOX, self.on_radio)

    def update_display(self, start_editing=False):
        if start_editing: self.editing = True
        if not self.editing: return
        self.options.SetSelection( self.values.index(self.value) )

    def on_radio(self, event):
        event.Skip()
        new_value = self.values[event.GetInt()]
        self._check_for_user_modification(new_value)

    def enable_item(self, index, enable=True):
        if not self.editing: return
        self.options.EnableItem(index, enable)

class IntRadioProperty(RadioProperty):
    #def set(self, value, activate=False, deactivate=False):
    #    RadioProperty.set(self, int(value), activate, deactivate)
    def _set_converter(self, value):
        return int(value)


class _CheckListProperty(Property):
    # common base class for Flags and WidgetStyleFlags; keeps self.value_set as a set of strings
    CONTROLNAMES = ["enabler", "_choices"]
    excludes = None

    def __init__(self, value, default_value=_DefaultArgument, name=None, names=None, values=None):
        self._names = names
        self._values = values  # these will sometimes only be calculated on demand, especially for WidgetStyle
        self.value_set = self._decode_value(value)
        self.enabler = self._choices = None
        Property.__init__(self, None, default_value, name) # with value=None, as this is to be calculated on demand only

    def _ensure_values(self):
        if self._names is None or self._values is None: raise ValueError("implementation error")

    def _decode_value(self, value):
        if not value:
            return set()
        if isinstance(value, compat.basestring):
            new_value = set( value.split("|") )
        elif isinstance(value, int):
            new_value = set()
            if value:
                # decode into set
                self._ensure_values()
                for name, flag_value in zip(self._names, self._values):
                    if flag_value is not None and value & flag_value == flag_value:
                        new_value.add(name)
        elif isinstance(value, (set,tuple,list)):
            new_value = set(value)  # avoid side effects
        return new_value

    def get(self):
        "get the value, or the default value if deactivated; usually not used directly, as owner.property will call it"
        if self.value is None and not self.deactivated and not self.blocked:
            # calculate the numeric value on demand
            if self.value_set: self._ensure_values()
            self.value = 0
            for i, name in enumerate(self._names):
                if name in self.value_set:
                    value = self._values[i]
                    if value is not None: self.value |= value
        return Property.get(self)

    def set(self, value, activate=False, deactivate=False, notify=False):
        new_value_set = self._decode_value(value)

        if new_value_set!=self.value_set:
            self.value_set = new_value_set
        Property.set(self, None, activate, deactivate, notify)  # with None, as this is to be calculated on demand only

    def add(self, value, activate=False, deactivate=False):
        if value in self.value_set: return
        self.value_set.add(value)
        Property.set(self, None, activate, deactivate)  # with value=None, as this is to be calculated on demand only

    def get_list_value(self):
        """Convert the current style in a list of boolean values."""
        combined_values = set()
        for name in self.value_set:
            combined_values.add(name)
            combined_values.update( self.style_defs[name].get("combination",[]) )
        ret = [(name in combined_values) for name in self._names]
        return ret

    def get_string_value(self):
        "Return the selected styles joined with '|', for writing to XML file"
        if not self.value_set: return ""

        ret = []
        for name in self._names:
            if name in self.value_set:
                ret.append(name)
        return '|'.join(ret)

    def write(self, outfile, tabs=0):
        value = self.get_string_value()
        if value:
            stmt = common.format_xml_tag(self.name, value, tabs)
            outfile.write(stmt)

    def create_editor(self, panel, sizer):
        self._choices = []
        tooltips = self._create_tooltip_text()
        for box_label in self.styles.keys():
            static_box = wx.StaticBox(panel, -1, box_label, style=wx.FULL_REPAINT_ON_RESIZE)
            box_sizer = wx.StaticBoxSizer(static_box, wx.VERTICAL)
            for style in self.styles[box_label]:
                checkbox = wx.CheckBox(panel, -1, style)

                if style in tooltips: compat.SetToolTip(checkbox, tooltips[style])

                self._choices.append(checkbox)
                box_sizer.Add(checkbox)

            sizer.Add(box_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.update_display(True)
        for checkbox in self._choices:
            checkbox.Bind(wx.EVT_CHECKBOX, self.on_checkbox)

    def on_checkbox(self, event):
        index = self._choices.index( event.GetEventObject() )
        value = self._names[index]
        checked = event.IsChecked()
        event.Skip()
        if checked:
            if value in self.value_set: return
            self.value_set.add(value)
            if self.excludes:
                excludes = self.excludes.get(value, [])
            else:
                excludes = self.style_defs[value].get("exclude",[])
            self.value_set.difference_update( excludes )
        else:
            if value in self.value_set:
                self.value_set.remove(value)
                self.value_set.difference_update( self.style_defs[value].get("combination",[]) )
            else:
                # check if it was set due to a combination
                for name in self._names:
                    combination = self.style_defs[name].get("combination",[])
                    if value in combination and name in self.value_set:
                        self.value_set.remove(name)
                        self.value_set.update(c for c in combination if c!=value)

        # check for combinations: if all flags of a combination are in value_set, we need only the combination
        for name in self._names:
            combination = self.style_defs[name].get("combination",[])
            if combination and self.value_set.issuperset(combination):
                self.value_set.difference_update( combination )
                self.value_set.add(name)

        self.value = None  # to be calculated on demand
        self._notify()
        self.update_display()

    def update_display(self, start_editing=False):
        # when the value has changed
        if start_editing: self.editing = True
        if not self.editing: return
        checked = self.get_list_value()
        for i,checkbox in enumerate(self._choices):
            name = self._names[i]
            if checked[i] and not checkbox.GetValue():
                checkbox.SetValue(True)
            elif not checked[i] and checkbox.GetValue():
                checkbox.SetValue(False)
            # display included flags in grey and excluded flags red
            if self.excludes:
                excludes = self.excludes.get(name, [])
            else:
                excludes = self.style_defs[name].get("exclude",[])
            default_color = wx.BLACK if not "rename_to" in self.style_defs[name] else wx.Colour(130,130,130)
            if checked[i] and not name in self.value_set:
                checkbox.SetForegroundColour(wx.Colour(120,120,100))  # grey
            elif self.value_set.intersection( excludes ):
                checkbox.SetForegroundColour(wx.RED)
            else:
                checkbox.SetForegroundColour(default_color)
            checkbox.Refresh()

    ####################################################################################################################
    # helpers for CheckBox tooltips
    def _tooltip_format_flags(self, details):
        "Create a tooltip text for generic style flags (aka attributes)."
        ret = []
        for attr_name, msg in [ ('default_style', _('This style is the default\n')),
                                ('obsolete',      _('This style is obsolete and should not be used.\nDetails: %s\n')),
                                ('rename_to',     _('This style will be renamed to %s.\n')),
                                ('synonym',       _('This style name is a synonym for %s.\n')) ]:
            if attr_name not in details: continue

            if '%s' in msg:
                ret.append( msg % details[attr_name] )
            else:
                ret.append( msg )

        return ret

    @staticmethod
    def _join_with_and(texts):
        # helper: join multiple texts with commas and 'and'
        if len(texts) == 1: return texts[0]
        first = texts[:-1]
        last = texts[-1]
        return _('%s and %s') % (', '.join(first), last)

    def _tooltip_format_generic(self, details):
        """Create a tooltip text for generic style attributes."""
        ret = []
        for attr_name, msg in [ ('include',     _('This style includes: %s\n')),
                                ('combination', _('This style is a combination of: %s\n')),
                                ('exclude',     _('This style excludes: %s\n')),
                                ('require',     _('This styles requires: %s\n')) ]:
            if attr_name not in details: continue
            style_text = self._join_with_and( sorted(details[attr_name]) )
            ret.append( msg % style_text )

        return ret

    def _tooltip_format_supported_by(self, details):
        "Create a tooltip text for the 'supported_by' style attribute."
        if 'supported_by' not in details: return []

        style_text = self._join_with_and( sorted(details['supported_by']) )
        return [_('This style is only supported on %s\n') % style_text]

    def _create_tooltip_text(self):
        "Create the texts for all tooltips based on widgets style configuration."
        tooltips = {}

        for style_name in self.style_defs:
            text = []
            details = self.style_defs.get(style_name, {})

            if 'desc' in details: text += [details['desc'],""]  # add a newline
            text += self._tooltip_format_generic(details)
            text += self._tooltip_format_supported_by(details)
            text += self._tooltip_format_flags(details)

            if style_name in self._names:
                # add a string with decimal, hexadecimal and binary values
                flag_value = self._values[self._names.index(style_name)]
                if flag_value is not None:
                    text.append( "%d 0x%x %s"%(flag_value, flag_value, bin(flag_value)) )

            tooltips[style_name] = "\n".join( text )

        return tooltips



class ManagedFlags(_CheckListProperty):
    # for ManagedBase.flags; e.g. wxEXPAND, wxALIGN_RIGHT,...,wxALL,
    # XXX handle combinations and exclusions
    # XXX support wxRESERVE_SPACE_EVEN_IF_HIDDEN for 3.x

    FLAG_DESCRIPTION = OrderedDict()
    FLAG_DESCRIPTION['Border'   ] = ['wxALL', 'wxLEFT', 'wxRIGHT', 'wxTOP', 'wxBOTTOM']
    FLAG_DESCRIPTION['Alignment'] = ['wxEXPAND', 'wxALIGN_RIGHT', 'wxALIGN_BOTTOM', 'wxALIGN_CENTER',
                                     'wxALIGN_CENTER_HORIZONTAL', 'wxALIGN_CENTER_VERTICAL',
                                     'wxSHAPED', 'wxFIXED_MINSIZE']
    remove = set( ['wxADJUST_MINSIZE',] )
    renames =  {'wxALIGN_CENTRE':'wxALIGN_CENTER',
                'wxALIGN_CENTRE_VERTICAL':'wxALIGN_CENTER_VERTICAL'}

    combinations = { "wxALL":set( 'wxLEFT|wxRIGHT|wxTOP|wxBOTTOM'.split("|") ),
                     "wxALIGN_CENTER":set( 'wxALIGN_CENTER_HORIZONTAL|wxALIGN_CENTER_VERTICAL'.split("|") ) }
    excludes = {'wxALIGN_RIGHT':            set(['wxALIGN_CENTER","wxALIGN_CENTER_HORIZONTAL']),
                'wxALIGN_BOTTOM':           set(['wxALIGN_CENTER","wxALIGN_CENTER_VERTICAL']),
                'wxALIGN_CENTER_HORIZONTAL':set(["wxALIGN_RIGHT"]),
                'wxALIGN_CENTER_VERTICAL':  set(["wxALIGN_BOTTOM"]),
                'wxALIGN_CENTER':           set(["wxALIGN_BOTTOM","wxALIGN_RIGHT"]) }

    FLAG_NAMES  = sum( FLAG_DESCRIPTION.values(), [] )
    FLAG_VALUES = [getattr(wx, name[2:]) for name in FLAG_NAMES]

    def __init__(self, value, default_value=_DefaultArgument, name=None):
        self.styles = self.FLAG_DESCRIPTION
        _CheckListProperty.__init__(self, value, default_value, name, self.FLAG_NAMES, self.FLAG_VALUES)
        self.style_defs = config.widget_config['generic_styles']

    def _decode_value(self, value):
        # handle obsolete and renamed flags
        new_value = _CheckListProperty._decode_value(self, value)
        if new_value:
            for name in self.remove:
                if name in new_value: new_value.remove(name)
        if new_value:
            for name, new_name in self.renames.items():
                if name in new_value:
                    new_value.remove(name)
                    new_value.add(new_name)
        return new_value

    def get_string_value(self):
        "Return the selected styles joined with '|', for writing to XML file"
        if not self.value_set: return ""
        # handle combinations
        ret_set = set(self.value_set)
        for name, combination in self.combinations.items():
            if ret_set.intersection(combination) == combination:
                ret_set.add(name)
                ret_set -= combination
        ret = []
        for name in self._names:
            if name in ret_set:
                ret.append(name)
        return '|'.join(ret)


class WidgetStyleProperty(_CheckListProperty):
    # for widget style flags; XXX handle combinations and exclusions
    def __init__(self):
        # the value will be set later in set_owner()
        _CheckListProperty.__init__(self, value=0)

    def set_owner(self, owner, attname):
        "style information is taken from self.owner.widget_writer"
        _CheckListProperty.set_owner(self, owner, attname)
        widget_writer = owner.widget_writer
        self.style_defs = widget_writer.style_defs
        self.styles = OrderedDict()
        self.styles[widget_writer.box_label] = widget_writer.style_list
        self._names = sum( self.styles.values(), [] )
        self._values = None
        self.set(widget_writer.default_style)
        self.modified = False
        self.default_value = set(self.value_set)

    def _ensure_values(self):
        self._values = []  # the associated flag values
        widget_writer = self.owner.widget_writer

        for name in self._names:
            wx_name = widget_writer.cn_f(name)
            if not wx_name:  # cn_f() returns an empty string if the given styles are not supported
                self._values.append(None)
                continue
            try:
                self._values.append( self.owner.wxname2attr(wx_name) )
            except:
                self._values.append(None)
                continue

    def create_editor(self, panel, sizer):
        self._choices = [] # the checkboxes
        self._ensure_values()

        widget_writer = self.owner.widget_writer

        tooltips = self._create_tooltip_text()

        box_label = _(widget_writer.box_label)
        static_box = wx.StaticBox(panel, -1, box_label, style=wx.FULL_REPAINT_ON_RESIZE)
        box_sizer = wx.StaticBoxSizer(static_box, wx.VERTICAL)
        for name, flag_value in zip(self._names, self._values):
            if name in widget_writer.style_defs:
                style_def = widget_writer.style_defs[name]
            else:
                # a generic style; no description in the class config
                style_def = config.widget_config["generic_styles"][name]
            checkbox = wx.CheckBox(panel, -1, name)

            if name in tooltips:
                compat.SetToolTip( checkbox, tooltips[name] )

            self._choices.append(checkbox)
            box_sizer.Add(checkbox)

        sizer.Add(box_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.update_display(True)
        for checkbox in self._choices:
            checkbox.Bind(wx.EVT_CHECKBOX, self.on_checkbox)

    def write(self, outfile, tabs=0):
        if isinstance(self.default_value, set) and self.value_set==self.default_value and not self.modified: return
        value = self.get_string_value()
        if value:
            stmt = common.format_xml_tag(self.name, value, tabs)
            outfile.write(stmt)




class TextProperty(Property):
    # text
    _HORIZONTAL_LAYOUT = True # label, checkbox, text in the same line; otherwise text will be in the second line
    CONTROLNAMES = ["enabler", "text"]
    validation_re = None # for derived classes
    STRIP = False
    def __init__(self, value="", multiline=False, strip=False, default_value=_DefaultArgument, name=None, fixed_height=False):
        self.multiline = multiline
        self.text = self.previous_value = None
        self.strip = strip
        self.fixed_height = fixed_height  # don't grow the edit field in vertical
        Property.__init__(self, value, default_value, name)

    def _set_converter(self, value):
        # used by set()
        if self.STRIP or self.strip:
            value = value.strip()
        return value

    def get_str_value(self):
        # for XML file writing: escape newline, \\n and tab
        return self.value.replace("\\n", "\\\\n").replace("\n", "\\n").replace("\t", "\\t")

    @staticmethod
    def _unescape(value):
        "unescape \t \n and \\n into newline and \n"
        splitted = value.split("\\")
        if len(splitted)==1: return value
        ret = []
        i = 0
        while i<len(splitted):
            s = splitted[i]
            more = len(splitted)-i-1
            if i==0:
                ret.append(s)
                i += 1
            elif not s and more>=1 and (splitted[i+1].startswith("n") or splitted[i+1].startswith("t")):
                # escaped \n sequence, i.e. backslash plus n
                ret.append("\\")
                ret.append(splitted[i+1])
                i += 2
            elif s.startswith("n"):
                # escaped newline character
                ret.append('\n')
                ret.append(s[1:])
                i += 1
            elif s.startswith("t"):
                # escaped tab character
                ret.append('\t')
                ret.append(s[1:])
                i += 1
            else:
                ret.append('\\')
                if s: ret.append(s)
                i+=1
        return "".join(ret)

    def load(self, value, activate=None, deactivate=None, notify=False):
        if value: value = self._unescape(value)
        self.set(value, activate, deactivate, notify)

    def create_editor(self, panel, sizer):
        "Actually builds the text control to set the value of the property interactively"

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        # label
        label = self._find_label()
        label = wx.lib.stattext.GenStaticText( panel, -1, label, size=(config.label_width, -1) )
        #hsizer.Add(label, 2, wx.ALL | wx.ALIGN_CENTER, 3)
        hsizer.Add(label, 0, wx.ALL | wx.ALIGN_CENTER, 3)
        # checkbox, if applicable
        self.enabler = None
        if self.deactivated is not None:
            self.enabler = wx.CheckBox(panel, -1, '')#, size=(1,-1))
            self.enabler.SetValue(not self.deactivated)
            self.enabler.Bind( wx.EVT_CHECKBOX, lambda event: self.toggle_active(event.IsChecked()) )
            #hsizer.Add(self.enabler, 0, wx.ALIGN_CENTER_VERTICAL)
            hsizer.Add(self.enabler, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 3)
        #else:
            #hsizer.AddSpacer(20)
        # the text control
        value = self.value
        if value is None:
            value = ""
        elif not isinstance(value, compat.basestring):
            value = self._value_to_str(value)
        self.text = self.create_text_ctrl(panel, value)
        if self.blocked:
            self.text.Enable(False)
        elif self.deactivated is not None:
            self.text.Enable(not self.deactivated)
        # layout of the controls / sizers
        if self._HORIZONTAL_LAYOUT:
            #self.text.SetMaxSize( (-1,200) )
            hsizer.Add(self.text, 5, wx.ALL | wx.ALIGN_CENTER | wx.EXPAND, 3)
            if self.multiline: # for multiline make it higher
                h = self.text.GetCharHeight()
                hsizer.SetItemMinSize(self.text, 100, h * 4)
            if self.fixed_height:
                sizer.Add(hsizer, 0, wx.EXPAND)
            else:
                sizer.Add(hsizer, 5 if self.multiline else 0, wx.EXPAND)
            #sizer.Add(hsizer, 0, wx.EXPAND)
        else:
            sizer.Add(hsizer, 0, wx.EXPAND)
            sizer.Add(self.text, 1, wx.ALL |wx.EXPAND, 3)
            if self.multiline: # for multiline make it higher
                h = self.text.GetCharHeight()
                hsizer.SetItemMinSize(self.text, -1, h * 3)

        self.additional_controls = self.create_additional_controls(panel, sizer, hsizer)

        self._set_tooltip(label, self.text, self.enabler, *self.additional_controls)
        self.editing = True

    def create_text_ctrl(self, panel, value):
        style = 0
        if self.readonly:               style = wx.TE_READONLY
        if self.multiline:              style |= wx.TE_MULTILINE
        else:                           style |= wx.TE_PROCESS_ENTER
        if not self._HORIZONTAL_LAYOUT: style |= wx.HSCROLL

        text = wx.TextCtrl( panel, -1, value or "", style=style )
        # bind KILL_FOCUS and Enter for non-multilines
        text.Bind(wx.EVT_KILL_FOCUS, self.on_kill_focus)
        # XXX
        text.Bind(wx.EVT_CHAR, self.on_char)
        if self.validation_re:
            text.Bind(wx.EVT_TEXT, self._on_text)
        return text

    def _on_text(self, event):
        if self.deactivated or self.blocked: return
        match = self.validation_re.match(event.GetString())
        if match:
            self.text.SetBackgroundColour(wx.WHITE)
            self.text.Refresh()
        else:
            self.text.SetBackgroundColour(wx.RED)
            self.text.Refresh()
        event.Skip()

    def create_additional_controls(self, panel, sizer, hsizer):
        # used e.g. by DialogProperty to create the button
        return []

    def update_display(self, start_editing=False):
        # when the value has changed
        if start_editing: self.editing = True
        if not self.editing: return
        self.text.SetValue(self._value_to_str(self.value))

    def _value_to_str(self, value):
        # change in derived classes where value might be a tuple or similar
        return value

    def on_char(self, event):
        if self.text is None: return
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            # reset
            #self.text.SetValue(self._unescape(self.value))
            self.text.SetValue(self.value)
            self.text.SetInsertionPointEnd()
        if not self.multiline and keycode==13:
            # enter
            self._check_for_user_modification()
        event.Skip()

    def on_kill_focus(self, event):
        event.Skip()
        if self.text is None: return
        if self.text.IsBeingDeleted(): return
        if not compat.wxWindow_IsEnabled(self.text): return
        self._check_for_user_modification()

    def _check_for_user_modification(self, new_value=None, force=False):
        if new_value is None:
            new_value = self._convert_from_text(self.text.GetValue())
        if new_value is None:  # e.g. validation failed
            wx.Bell()
            self.text.SetValue( self._value_to_str(self.value))
            return
        self.previous_value = self.value
        Property._check_for_user_modification(self, new_value)

    def _convert_from_text(self, value=None):
        """Convert newline and tab characters to a character sequences (FROM input widget TO property)
        Derived classes may return None to indicate a validation fail."""
        if value is None: value = self.text.GetValue()
        return value

    def check(self, value):
        "checks whether the string value matches the validation regular expression"
        if not self.validation_re: return True
        return bool( self.validation_re.match(value) )



class TextPropertyA(TextProperty):
    deactivated = False
class TextPropertyD(TextProperty):
    deactivated = True

class TextPropertyRO(TextProperty):
    readonly = True


########################################################################################################################
# some text properties with validation:

class NameProperty(TextProperty):
    validation_re  = re.compile(r'^[a-zA-Z_]+[\w-]*(\[\w*\])*$')
    def _check_name_uniqueness(self, name):
        # check whether the name is unique
        if config.preferences.allow_duplicate_names: return
        if name == self.value: return True
        if common.app_tree.has_name(name,self.owner.node):
            return False
        return True

    def _on_text(self, event):
        if self.deactivated or self.blocked: return
        name = event.GetString()
        match = self.validation_re.match(name)
        if match:
            if self._check_name_uniqueness(name):
                self.text.SetBackgroundColour(wx.WHITE)
            else:
                self.text.SetBackgroundColour(wx.YELLOW)
        else:
            self.text.SetBackgroundColour(wx.RED)
        self.text.Refresh()
        event.Skip()
    def _convert_from_text(self, value):
        "normalize string to e.g. '-1, -1'; return None if invalid"
        match = self.validation_re.match(value)
        #if not match: return self.value
        if not match: return None
        if not self._check_name_uniqueness(value): return None
        return value
    def check(self, value):
        # check whether it's valid to set value
        check = self._convert_from_text(value)
        if check is None: return False
        return True


# some building blocks for regular expressions:
_leading  = r"^\s*\(?\s*"          # whitespace, optionally including an opening "("
_int      = r"(0|(?:-?[1-9]\d*))"  # a number group matching any integer
_ge_m1    = r"((?:-1)|(?:\d+))"    # a number group matching integers >=-1
_g_0      = r"([1-9]\d*)"          # a number group matching integers >0
_ge_0     = r"(\d+)"               # a number group matching integers >=0
_comma    = r"\s*,\s*"             # a comma, optionally with surrounding whitespace
_trailing = r"\s*\)?\s*$"          # whitespace, optionally including a closing ")"


class SizePropertyD(TextPropertyD):
    validation_re = re.compile( _leading + _ge_m1 + _comma + _ge_m1 + _trailing )  # match pair of integers >=- 1
    normalization = "%s, %s" # for normalization % valiation_re.match(...).groups()
    def _set_converter(self, value):
        # value can be a tuple
        if isinstance(value, compat.basestring):
            return value
        if isinstance(value, wx.Size):
            return '%d, %d' % (value.x, value.y)
        return '%d, %d' % value

    def _convert_from_text(self, value):
        "normalize string to e.g. '-1, -1'; return None if invalid"
        match = self.validation_re.match(value)
        #if not match: return self.value
        if not match: return None
        return self.normalization%match.groups()

    def get_tuple(self):
        x, y = self.value.split(",")
        return (int(x), int(y))


class ScrollRatePropertyD(SizePropertyD):
    # the value is still a string, but it's guaranteed to have the right format
    validation_re = re.compile(_leading + _ge_0 + _comma + _ge_0 + _trailing )  # match a pair of positive integers


class IntRangePropertyA(SizePropertyD):
    deactivated = False
    validation_re = re.compile( _leading + _int + _comma + _int + _trailing )  # match pair of integers
    def _convert_from_text(self, value):
        # check that min is smaller than max
        match = self.validation_re.match(value)
        if not match: return None
        mi, ma = match.groups()
        if int(mi)>int(ma): return None
        return self.normalization%(mi,ma)


del _leading, _ge_m1, _g_0, _ge_0, _comma, _trailing
########################################################################################################################

class ComboBoxProperty(TextProperty):
    def __init__(self, value="", choices=[], default_value=_DefaultArgument, name=None):
        self.choices = choices
        TextProperty.__init__(self, value, False, default_value, name)

    def create_text_ctrl(self, panel, value):
        style = wx.CB_DROPDOWN | wx.CB_READONLY
        combo = wx.ComboBox( panel, -1, self.value, choices=self.choices, style=style )
        if self.value in self.choices:
            combo.SetStringSelection(self.value)
        else:
            combo.SetSelection(-1)
        combo.Bind(wx.EVT_COMBOBOX, self.on_combobox)
        combo.Bind(wx.EVT_KILL_FOCUS, self.on_kill_focus)
        combo.Bind(wx.EVT_CHAR, self.on_char)
        return combo

    def set_choices(self, choices=None):
        if choices is not None:
            if choices==self.choices: return
            self.choices[:] = choices
        if not self.value in self.choices:
            self.value = ""
        if not self.editing: return
        # update choices, but keep current selection, if possible
        if self.value in self.choices:
            if self.editing: self.text.SetStringSelection(self.value)
        else:
            if self.editing: self.text.SetSelection(-1)

    def add_choice(self, choice):
        self.choices.append(choice)
        self.choices.sort()
        self.set_choices()

    def remove_choice(self, choice):
        self.choices.remove(choice)
        self.set_choices()

    def on_combobox(self, event):
        event.Skip()
        if self.text is None: return
        if self.text.IsBeingDeleted(): return
        if not compat.wxWindow_IsEnabled(self.text): return
        self._check_for_user_modification()


class ComboBoxPropertyA(ComboBoxProperty):
    deactivated = False
class ComboBoxPropertyD(ComboBoxProperty):
    deactivated = True


#class ListBoxProperty(ComboBoxProperty):
    #def __init__(self, value="", choices=[], default_value=_DefaultArgument, name=None):
        #self.choices = choices
        #TextProperty.__init__(self, value, False, default_value, name)

    #def create_text_ctrl(self, panel, value):
        #style = wx.LB_SINGLE
        #combo = wx.ListBox( panel, -1, self.value, choices=self.choices, style=style )
        #combo.Bind(wx.EVT_LISTBOX, self.on_combobox)
        ##combo.Bind(wx.EVT_KILL_FOCUS, self.on_kill_focus)
        ##combo.Bind(wx.EVT_CHAR, self.on_char)
        #return combo

#class ListBoxPropertyA(ListBoxProperty):
    #deactivated = False
#class ListBoxPropertyD(ListBoxProperty):
    #deactivated = True



class DialogProperty(TextProperty):
    # for now, this is only a base class for FileName, Color and FontProperty
    CONTROLNAMES = ["enabler", "text", "button"]
    def __init__(self, value="", multiline=False, strip=True, default_value=_DefaultArgument, name=None):
        TextProperty.__init__(self, value, multiline, strip, default_value, name)
        self.dialog = self.button = None
    def create_additional_controls(self, panel, sizer, hsizer):
        # used e.g. by DialogProperty to create the button
        self.button = wx.Button(panel, -1, " ... ")
        if self.deactivated is not None:
            self.button.Enable(not self.deactivated)
        self.button.Bind(wx.EVT_BUTTON, self.display_dialog)
        hsizer.Add(self.button, 0, wx.ALL | wx.ALIGN_CENTER, 3)
        self._update_button()
        return [self.button]

    def set_dialog(self, dialog):
        self.dialog = dialog
    def _create_dialog(self):
        # create or update
        return self.dialog

    def display_dialog(self, event):
        dialog = self._create_dialog()
        if dialog is None or dialog.ShowModal()!=wx.ID_OK: return
        # the dialog needs to return a valid value!
        value = dialog.get_value()
        self.text.SetValue( self._value_to_str(value) )
        self._check_for_user_modification(value)
        self.update_display()
        #self.text.ProcessEvent( wx.FocusEvent(wx.wxEVT_KILL_FOCUS, self.text.GetId()) )

    def _update_button(self):
        # update e.g. color or font
        pass

    def update_display(self, start_editing=False):
        TextProperty.update_display(self, start_editing)
        self._update_button()


class DialogPropertyD(DialogProperty):
    deactivated = True
class DialogPropertyA(DialogProperty):
    deactivated = False


class _FileDialog:
    def __init__(self, parent, message, wildcard, extension, style):
        self.parent = parent
        self.message = message
        self.wildcard = wildcard
        self.default_extension = extension
        self.style = style
        self.value = None
    def ShowModal(self):
        #(message, default_path=EmptyString, default_filename=EmptyString, default_extension=EmptyString, wildcard=FileSelectorDefaultWildcardStr, flags=0, parent=None, x=DefaultCoord, y=DefaultCoord):
        self.value = wx.FileSelector( self.message, self.value, "", self.default_extension, wildcard=self.wildcard, flags=self.style )
        if self.value:
            return wx.ID_OK
    def set_value(self, value):
        self.value = value
    def get_value(self):
        return self.value


class FileNameProperty(DialogProperty):
    # these can be set on an instance
    message = _("Choose a file")
    wildcard = _("All files|*")
    default_extension = None
    def __init__(self, value="", style=0, default_value=_DefaultArgument, name=None):
        self.style = style
        DialogProperty.__init__(self, value, False, True, default_value, name)
    def _create_dialog(self):
        if self.dialog is not None: return self.dialog
        parent = self.text.GetTopLevelParent()
        dlg = _FileDialog(parent, self.message, self.wildcard, self.default_extension, style=self.style)
        dlg.set_value(self.value)
        return dlg

class FileNamePropertyD(FileNameProperty):
    deactivated = True


class ColorProperty(DialogProperty):
    STRIP = True
    str_to_colors = {
        'wxSYS_COLOUR_SCROLLBAR': wx.SYS_COLOUR_SCROLLBAR,
        'wxSYS_COLOUR_BACKGROUND': wx.SYS_COLOUR_BACKGROUND,
        'wxSYS_COLOUR_ACTIVECAPTION': wx.SYS_COLOUR_ACTIVECAPTION,
        'wxSYS_COLOUR_INACTIVECAPTION': wx.SYS_COLOUR_INACTIVECAPTION,
        'wxSYS_COLOUR_MENU': wx.SYS_COLOUR_MENU,
        'wxSYS_COLOUR_WINDOW': wx.SYS_COLOUR_WINDOW,
        'wxSYS_COLOUR_WINDOWFRAME': wx.SYS_COLOUR_WINDOWFRAME,
        'wxSYS_COLOUR_MENUTEXT': wx.SYS_COLOUR_MENUTEXT,
        'wxSYS_COLOUR_WINDOWTEXT': wx.SYS_COLOUR_WINDOWTEXT,
        'wxSYS_COLOUR_CAPTIONTEXT': wx.SYS_COLOUR_CAPTIONTEXT,
        'wxSYS_COLOUR_ACTIVEBORDER': wx.SYS_COLOUR_ACTIVEBORDER,
        'wxSYS_COLOUR_INACTIVEBORDER': wx.SYS_COLOUR_INACTIVEBORDER,
        'wxSYS_COLOUR_APPWORKSPACE': wx.SYS_COLOUR_APPWORKSPACE,
        'wxSYS_COLOUR_HIGHLIGHT': wx.SYS_COLOUR_HIGHLIGHT,
        'wxSYS_COLOUR_HIGHLIGHTTEXT': wx.SYS_COLOUR_HIGHLIGHTTEXT,
        'wxSYS_COLOUR_BTNFACE': wx.SYS_COLOUR_BTNFACE,
        'wxSYS_COLOUR_BTNSHADOW': wx.SYS_COLOUR_BTNSHADOW,
        'wxSYS_COLOUR_GRAYTEXT': wx.SYS_COLOUR_GRAYTEXT,
        'wxSYS_COLOUR_BTNTEXT': wx.SYS_COLOUR_BTNTEXT,
        'wxSYS_COLOUR_INACTIVECAPTIONTEXT': wx.SYS_COLOUR_INACTIVECAPTIONTEXT,
        'wxSYS_COLOUR_BTNHIGHLIGHT': wx.SYS_COLOUR_BTNHIGHLIGHT,
        'wxSYS_COLOUR_3DDKSHADOW': wx.SYS_COLOUR_3DDKSHADOW,
        'wxSYS_COLOUR_3DLIGHT': wx.SYS_COLOUR_3DLIGHT,
        'wxSYS_COLOUR_INFOTEXT': wx.SYS_COLOUR_INFOTEXT,
        'wxSYS_COLOUR_INFOBK': wx.SYS_COLOUR_INFOBK,
        'wxSYS_COLOUR_DESKTOP': wx.SYS_COLOUR_DESKTOP,
        'wxSYS_COLOUR_3DFACE': wx.SYS_COLOUR_3DFACE,
        'wxSYS_COLOUR_3DSHADOW': wx.SYS_COLOUR_3DSHADOW,
        'wxSYS_COLOUR_3DHIGHLIGHT': wx.SYS_COLOUR_3DHIGHLIGHT,
        'wxSYS_COLOUR_3DHILIGHT': wx.SYS_COLOUR_3DHILIGHT,
        'wxSYS_COLOUR_BTNHILIGHT': wx.SYS_COLOUR_BTNHILIGHT
        }
    colors_to_str = misc._reverse_dict(str_to_colors)

    def _create_dialog(self):
        if self.dialog is None:
            from color_dialog import wxGladeColorDialog
            self.dialog = wxGladeColorDialog(self.str_to_colors)
        self.dialog.set_value(self.value or "")
        return self.dialog

    def _set_converter(self, value):
        if not isinstance(value, compat.basestring):
            value = misc.color_to_string(value)
        return value

    def get_color(self):
        # return a wx.Colour instance
        color = self.get()
        if color is _DefaultArgument: return None
        if color in self.str_to_colors:
            # e.g. 'wxSYS_COLOUR_SCROLLBAR'
            return wx.SystemSettings_GetColour(self.str_to_colors[color])
        elif color.startswith("#"):
            return misc.string_to_color(color)
        ret = wx.NamedColour(color)
        if ret.IsOk():
            return ret
        return None

    def _update_button(self):
        if not self.button: return
        if self.is_active():
            color = self.get_color()
        else:
            color = None
        if color is None:
            self.set_active(False)  # invalid colour
            self.button.SetBackgroundColour(None) # wx.NullColor)
        else:
            self.button.SetBackgroundColour(color)




class ColorPropertyD(ColorProperty):
    deactivated = True

class FontProperty(DialogProperty):
    font_families_to = {'default': wx.DEFAULT,
                        'decorative': wx.DECORATIVE, 'roman': wx.ROMAN,
                        'swiss': wx.SWISS, 'script': wx.SCRIPT, 'modern': wx.MODERN }
    font_families_from = misc._reverse_dict(font_families_to)
    font_styles_to = {'normal': wx.NORMAL, 'slant': wx.SLANT, 'italic': wx.ITALIC }
    font_styles_from = misc._reverse_dict(font_styles_to)
    font_weights_to = {'normal': wx.NORMAL, 'light': wx.LIGHT, 'bold': wx.BOLD }
    font_weights_from = misc._reverse_dict(font_weights_to)

    font_families_to['teletype'] = wx.TELETYPE
    font_families_from[wx.TELETYPE] = 'teletype'

    validation_re = re.compile(" *\[(\d+), *'(default|decorative|roman|swiss|script|modern)', *"
                               "'(normal|slant|italic)', *'(normal|light|bold)', *(0|1), *'([a-zA-Z _]*)'] *")
    normalization = "[%s, '%s', '%s', '%s', %s, '%s']"
    def write(self, outfile, tabs=0):
        if not self.is_active(): return
        try:
            props = [common.encode_to_unicode(s) for s in self.value]
        except:
            self._logger.exception(_('Internal Error'))
            return
        if len(props) < 6:
            self._logger.error( _('error in the value of the property "%s"'), self.name )
            return
        inner_xml =  common.format_xml_tag(u'size',       props[0], tabs+1)
        inner_xml += common.format_xml_tag(u'family',     props[1], tabs+1)
        inner_xml += common.format_xml_tag(u'style',      props[2], tabs+1)
        inner_xml += common.format_xml_tag(u'weight',     props[3], tabs+1)
        inner_xml += common.format_xml_tag(u'underlined', props[4], tabs+1)
        inner_xml += common.format_xml_tag(u'face',       props[5], tabs+1)
        stmt = common.format_xml_tag( self.name, inner_xml, tabs, is_xml=True )
        outfile.write(stmt)

    def _create_dialog(self):
        if self.dialog is None:
            import font_dialog
            parent = self.text.GetTopLevelParent()
            self.dialog = font_dialog.wxGladeFontDialog(parent, -1, "")
        self.dialog.set_value(self.value)
        return self.dialog

    def _convert_from_text(self, value=None):
        if isinstance(value, list): return value
        if value is None:
            value = self.text.GetValue()
        match = self.validation_re.match(value)
        if not match: return None
        groups = match.groups()
        return (int(groups[0]), groups[1], groups[2], groups[3], int(groups[4]), groups[5])

    def _set_converter(self, value):
        if isinstance(value, compat.basestring): value = self._convert_from_text(value)
        return value

    def _value_to_str(self, value):
        return self.normalization%tuple(value)


class FontPropertyD(FontProperty):
    deactivated = True



class GridProperty(Property):
    """Property whose values are modified through a wxGrid table.

    value:           list of lists
    cols:            List of column labels and column types (GridProperty.STRING, INT, FLOAT, BOOL)
    default_row:     default values for inserted entries/rows
    can_add:         Add Button to add a new entry/row
    can_remove:      Add Button to remove a new entry/row
    can_insert:      Add Button to insert a new entry/row
    can_remove_last: Allow to remove last entry/row
    col_sizes:       List of column widths
    with_index:      if True, the owner's method 'set_%s'%self.attributename will be called with new value and indices
    """
    STRING, INT, FLOAT, BOOL = 0, 1, 2, 3
    # List of functions to set the column format:
    col_format = [lambda g, c: None,
                  lambda g, c: g.SetColFormatNumber(c),
                  lambda g, c: g.SetColFormatFloat(c),
                  lambda g, c: g.SetColFormatBool(c)]
    _DEFAULT_VALUES = {STRING:"",  INT:0, FLOAT:0.0, BOOL:False}

    CONTROLNAMES = ["btn", "buttons", "grid"]
    GROW = True
    validation_res = None # one per column
    def __init__(self, value, cols, default_row=None,
                 can_add=True, can_remove=True, can_insert=True, can_remove_last=True,
                 col_sizes=None, with_index=False, name=None):

        Property.__init__(self, value, name) # , label=label)
        if default_row is None:
            default_row = [self._DEFAULT_VALUES[col_def[1]] for col_def in cols]
        self.default_row = default_row  # when a row is inserted, these values will be taken
        self.with_index = with_index # display index; also provide the original indices to the owner when updating value
        self.col_defs = cols
        self.can_add = can_add
        self.can_remove = can_remove
        self.can_insert = can_insert
        self.can_remove_last = can_remove_last
        if col_sizes is None:
            self.col_sizes = []
        else:
            self.col_sizes = col_sizes
        self.cur_row = 0
        self.editing_values = None # before pressing Apply; stored here because the editor grid might be deleted
        self.grid = None

    def set(self, value, *args, **kwargs):
        Property.set(self, value, *args, **kwargs)
        self._initialize_indices()
        self.editing_values = None

    def create_editor(self, panel, sizer):
        "Actually builds the grid to set the value of the property interactively"

        label   = self._find_label()
        box_sizer = wx.StaticBoxSizer(wx.StaticBox(panel, -1, label), wx.VERTICAL)

        # the buttons ##################################################################################################
        extra_flag = wx.FIXED_MINSIZE
        if self.can_add or self.can_insert or self.can_remove:
            btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
            apply_btn = wx.Button(panel, wx.ID_ANY, _("  Apply  "), style=wx.BU_EXACTFIT)
            btn_sizer.Add(apply_btn, 0, extra_flag | wx.RIGHT, 16)

            # the add/insert/remove buttons
            add_btn = insert_btn = remove_btn = None
            if self.can_add:
                add_btn = wx.Button(panel, wx.ID_ANY, _("  Add  "), style=wx.BU_EXACTFIT)
                add_btn.Bind(wx.EVT_BUTTON, self.add_row)
            if self.can_insert:
                insert_btn = wx.Button(panel, wx.ID_ANY, _("  Insert  "), style=wx.BU_EXACTFIT)
                insert_btn.Bind(wx.EVT_BUTTON, self.insert_row)
            if self.can_remove:
                remove_btn = wx.Button(panel, wx.ID_ANY, _("  Remove  "), style=wx.BU_EXACTFIT)
                remove_btn.Bind(wx.EVT_BUTTON, self.remove_row)
            self.buttons = [add_btn, insert_btn, remove_btn]
            for btn in self.buttons:
                if btn: btn_sizer.Add( btn, 0, wx.LEFT | wx.RIGHT | extra_flag, 4 )
            self.buttons.insert(0, apply_btn)
        else:
            self.buttons = []

        # the grid #####################################################################################################
        self.grid = wx.grid.Grid(panel, -1)
        self.grid.CreateGrid( len(self.value), len(self.col_defs) )
        self.grid.SetMargins(0, 0)

        for i, (label,datatype) in enumerate(self.col_defs):
            self.grid.SetColLabelValue(i, label)
            GridProperty.col_format[datatype](self.grid, i)

        # set row/col sizes
        self.grid.SetRowLabelSize(20 if self.with_index else 0)
        self.grid.SetColLabelSize(20)
        if self.col_sizes:
            self._set_col_sizes(self.col_sizes)

        # add the button sizer and the grid to the sizer ###############################################################
        if self.buttons:
            box_sizer.Add(btn_sizer, 0, wx.BOTTOM | wx.EXPAND, 2)
        box_sizer.Add(self.grid, 1, wx.EXPAND)
        # add our sizer to the main sizer   XXX change if required
        sizer.Add(box_sizer, 5, wx.EXPAND)

        self.display_value(start_editing=True)

        self.grid.Bind(wx.grid.EVT_GRID_SELECT_CELL, self.on_select_cell)
        if self.buttons:
            apply_btn.Bind(wx.EVT_BUTTON, self.apply)
        if compat.IS_CLASSIC:
            self.grid.Bind(wx.grid.EVT_GRID_CMD_CELL_CHANGE, self.on_cell_changed)
        else:
            self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.on_cell_changed)
            self.grid.Bind(wx.grid.EVT_GRID_CELL_CHANGING, self.on_cell_changing)  # for validation

        self._set_tooltip(self.grid.GetGridWindow(), *self.buttons)

        self.grid.Bind(wx.EVT_SIZE, self.on_size)
        self._width_delta = None

    def on_size(self, event):
        # resize last column to fill the space
        if self._width_delta is None:
            self._width_delta = self.grid.GetParent().GetSize()[0] - self.grid.GetSize()[0]
        self.grid.SetColSize(1, 10)
        col_widths = 0
        for n in range(len(self.col_defs)-1):
            col_widths += self.grid.GetColSize(n)
        remaining_width = self.grid.GetParent().GetSize()[0] - col_widths - self._width_delta - self.grid.GetRowLabelSize()
        self.grid.SetColSize( len(self.col_defs)-1, max(remaining_width, 100) )

    def on_select_cell(self, event):
        self.cur_row = event.GetRow()
        event.Skip()

    def display_value(self, start_editing=False):
        if start_editing: self.editing = True
        if not self.editing: return

        # values is a list of lists with the values of the cells
        value = self.editing_values if self.editing_values is not None else self.value
        rows_new = len(value)

        # add or remove rows
        rows = self.grid.GetNumberRows()
        if rows < rows_new:
            self.grid.AppendRows(rows_new - rows)
        elif rows != rows_new:
            self.grid.DeleteRows(rows_new, rows - rows_new)

        # update content
        self._changing_value = True
        for i,row in enumerate(value):
            for j, col in enumerate(row):
                self.grid.SetCellValue(i, j, str(col))
        self._changing_value = False

        # update state of the remove button and the row label
        self._update_apply_button()
        self._update_remove_button()
        self._update_indices()

    def apply(self, event):
        """Apply the edited value; called by Apply button.

        If self.with_index and self.owner.set_... exists, this will be called with values and indices.
        In this case, self.owner.properties_changed will not be called additionally.
        Otherwise, the standard mechanism will be used."""
        self.grid.SaveEditControlValue() # end editing of the current cell
        new_value = self._get_new_value()
        if new_value is None:  # not modified
            event.Skip()
            return

        if self.with_index:
            setter = getattr(self.owner, "set_%s"%self.attributename, None)

        if not self.with_index or not setter:
            self.on_value_edited(new_value)
            self._update_apply_button()
            event.Skip()
            return

        indices = [int(i) if i else None  for i in self.indices]
        #self._changing_value = True
        old_value = self.value[:]
        self.value[:] = new_value
        setter(old_value, indices)
        #self._changing_value = False
        self.editing_values = None
        self._initialize_indices()
        self._update_indices()

        self._update_apply_button()
        event.Skip()

    def _get_new_value(self):
        # returns None if not edited
        if self.editing_values is None: return None
        ret = self.editing_values[:]
        modified = False
        # compare the lengths of the original vs. current values
        if len(self.value) != len(ret):
            modified = True
        # compare the indices
        if self.with_index and self.indices!=[str(i) for i in range(len(self.value))]:
            modified = True
        # go through the rows
        for i,row in enumerate(ret):
            if row is None:
                # empty row
                ret[i] = [""]*len(self.col_defs)
                modified = True
            if not modified:
                for j, col in enumerate(row):
                    if not misc.streq(col, self.value[i][j]):
                        modified = True
        if not modified:
            return None
        return ret

    # helpers for self.with_index  handling ############################################################################
    def _initialize_indices(self):
        if not self.with_index: return
        self.indices = [str(i) for i in range(len(self.value))]

    def _update_indices(self):
        if not self.grid or not self.with_index: return
        for i, index in enumerate(self.indices):
            self.grid.SetRowLabelValue(i, index)

    # edit handlers; add/remove/insert button handlers #################################################################
    def on_cell_changing(self, event):
        # XXX validate; event.Veto if not valid
        if not self.validation_res: return
        row,col = event.Row, event.Col


    def on_cell_changed(self, event):
        # user has entered a value
        row,col = event.Row, event.Col
        value = self.grid.GetCellValue(row,col)  # the new value
        if self.validation_res and self.validation_res[col]:
            validation_re = self.validation_res[col]
            match = validation_re.match(value)
            if not match:
                wx.Bell()
                event.Veto()
                return

        if not self.can_add and not self.can_insert and not self.can_insert:
            # immediate
            self.value[row][col] = value
            self._notify()
            event.Skip()
            return

        activate_apply = not self.editing_values
        data = self._ensure_editing_copy()
        if data[row] is None:
            data[row] = self.default_row[:]
        #if self.col_defs[col][1]==self.STRING:
        if self.col_defs[col][1]==self.INT:
            value = int(value)
        elif self.col_defs[col][1]==self.FLOAT:
            value = float(value)
        #elif self.col_defs[col][1]==self.BOOL:
            #value = bool(value)
        data[row][col] = value
        if activate_apply: self._update_apply_button()
        event.Skip()

    def add_row(self, event):
        self.grid.AppendRows()
        self.grid.MakeCellVisible(len(self.value), 0)
        self.grid.ForceRefresh()
        self._ensure_editing_copy()
        self.editing_values.append( None )
        if self.with_index:
            self.indices.append("")
        self._update_remove_button()
        self._update_apply_button()
        self._update_indices()

    def remove_row(self, event):
        if not self.can_remove_last and self.grid.GetNumberRows()==1:
            self._logger.warning( _('You can not remove the last entry!') )
            return
        self._ensure_editing_copy()
        if self.editing_values:
            self.grid.DeleteRows(self.cur_row)
            del self.editing_values[self.cur_row]
            if self.with_index:
                del self.indices[self.cur_row]
            if self.cur_row>=len(self.editing_values):
                self.cur_row -= 1

        self._update_remove_button()
        self._update_apply_button()
        self._update_indices()

    def insert_row(self, event):
        self.grid.InsertRows(self.cur_row)
        self.grid.MakeCellVisible(self.cur_row, 0)
        self.grid.ForceRefresh()
        self._ensure_editing_copy()
        self.editing_values.insert(self.cur_row, None)
        if self.with_index:
            self.indices.insert(self.cur_row, "")
        self._update_remove_button()
        self._update_apply_button()
        self._update_indices()

    def _ensure_editing_copy(self):
        if self.editing_values is None:
            self.editing_values = [[col for col in row] for row in self.value]
        return self.editing_values

    def _update_remove_button(self):
        """Enable or disable remove button

        The state of the remove button depends on the number of rows and L{self.can_remove_last}."""
        if not self.grid or not self.buttons: return
        if self.can_remove and not self.can_remove_last:
            self.buttons[-1].Enable(self.grid.GetNumberRows() > 1)

    def _update_apply_button(self):
        if not self.grid or not self.buttons: return
        self.buttons[0].Enable( self.editing_values is not None)

    # helpers ##########################################################################################################
    def _set_col_sizes(self, sizes):
        """sets the width of the columns.
        sizes is a list of integers with the size of each column: a value of 0 stands for a default size,
        while -1 means to expand the column to fitthe available space (at most one column can have size -1)"""
        col_to_expand = -1
        total_w = 0
        for i in range(self.grid.GetNumberCols()):
            try:
                w = sizes[i]
            except IndexError:
                return
            if not w:
                self.grid.AutoSizeColumn(i)
                total_w += self.grid.GetColSize(i)
            elif w < 0:
                col_to_expand = i
            else:
                self.grid.SetColSize(i, w)
                total_w += w
        if col_to_expand >= 0:
            self.grid.AutoSizeColumn(col_to_expand)
            w = self.grid.GetSize()[0] - total_w
            if w >= self.grid.GetColSize(col_to_expand):
                self.grid.SetColSize(col_to_expand, w)



class ActionButtonProperty(Property):
    # just a button to start an action
    CONTROLNAMES = ["button"]
    def __init__(self, callback):
        self.callback = callback
        self.label = None  # set to None; when creating an editor, self.set_label() may have been called
        Property.__init__(self, None)

    def get(self):
        return self

    def create_editor(self, panel, sizer):
        if self.label is None: self.label = self._find_label()
        self.button = wx.Button( panel, -1, self.label )
        sizer.Add(self.button, 0, wx.EXPAND)
        tooltip = self._find_tooltip()
        if tooltip: compat.SetToolTip(self.button, tooltip)
        self.button.Bind(wx.EVT_BUTTON, self.on_button)
        self.editing = True

    def set_label(self, label):
        self.label = label
        if self.editing: self.button.SetLabel(label)

    def on_button(self, event):
        self.callback()

    def __call__(self, *args, **kwargs):
        self.callback(*args, **kwargs)

    def write(self, outfile, tabs=0):
        return



########################################################################################################################

class PropertyOwner(object):
    def __init__(self):
        # property handling
        self.properties = {}
        self.property_names = []
    # property handling ################################################################################################
    def add_property(self, prop, attname):
        # link the property to the owner
        self.properties[attname] = prop
        if prop.name is not None:
            # allow also access via property name like 'class', but only via the properties dict
            self.properties[prop.name] = prop
            self.property_names.append(prop.name)
        else:
            self.property_names.append(attname)
        prop.set_owner(self, attname)
    def __getattr__(self, attr):
        if attr in self.properties:
            # return the value (either the user-provided or the default value)
            return self.properties[attr].get()
        raise AttributeError("%r object has no attribute %r" %(self.__class__, attr))
    def __setattr__(self, name, value):
        if isinstance(value, Property):
            self.add_property(value, name)
            return
        object.__setattr__(self, name, value)
    def copy_properties(self, other, properties):
        "copy named properties from other"
        # with short cut for properties with 'values_set'
        modified = set()
        for p in properties:
            if hasattr(other, "properties"):
                o_prop = other.properties[p]
                new = o_prop.value_set  if hasattr(o_prop, "value_set") else  o_prop.value
            else:
                new = getattr(other, p)
            prop = self.properties[p]
            if hasattr(prop, "value_set") and isinstance(new, set):
                old = prop.value_set
            else:
                old = prop.get()
            if new!=old:
                modified.add(p)
                prop.set(new)
        if modified:
            self.properties_changed(modified)
    def properties_changed(self, modified):
        """properties edited; trigger actions like widget or sizer update;
        'modified' is None or a list of property names;
        the properties_changed method of a derived class may add properties to 'modified' before calling base classes"""
        pass
    def get_properties(self, without=set()):
        # return list of properties to be written to XML file
        ret = []
        for name in self.property_names:
            if name in ("class","name","base") or name in without: continue
            prop = self.properties[name]
            if prop.attributename in without: continue  # for e.g. option/proportion
            if prop is not None: ret.append(prop)
        return ret

