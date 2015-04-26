"""\
Common code used by all code generators

@copyright: 2011-2015 Carsten Grohmann
@license: MIT (see license.txt) - THIS PROGRAM COMES WITH NO WARRANTY
"""

import copy
import StringIO
import logging
import os
import os.path
import random
import re
import sys
import time
import types

import common
import config
import errors
import misc
import wcodegen
from xml_parse import XmlParsingError


class DummyPropertyHandler(object):
    """Empty handler for properties that do not need code"""

    def __init__(self):
        self.handlers = {}
        self.event_name = None
        self.curr_handler = []

    def start_elem(self, name, attrs):
        pass

    def end_elem(self, name, code_obj):
        return True

    def char_data(self, data):
        pass

# end of class DummyPropertyHandler


class EventsPropertyHandler(DummyPropertyHandler):
    """\
    Handler for event properties
    """

    def start_elem(self, name, attrs):
        if name == 'handler':
            self.event_name = attrs['event']

    def end_elem(self, name, code_obj):
        if name == 'handler':
            if self.event_name and self.curr_handler:
                self.handlers[self.event_name] = ''.join(self.curr_handler)
            self.event_name = None
            self.curr_handler = []
        elif name == 'events':
            code_obj.properties['events'] = self.handlers
            return True

    def char_data(self, data):
        data = data.strip()
        if data:
            self.curr_handler.append(data)

# end of class EventsPropertyHandler


class ExtraPropertiesPropertyHandler(DummyPropertyHandler):

    def __init__(self):
        DummyPropertyHandler.__init__(self)
        self.props = {}
        self.curr_prop = []
        self.prop_name = None

    def start_elem(self, name, attrs):
        if name == 'property':
            name = attrs['name']
            self.prop_name = name

    def end_elem(self, name, code_obj):
        if name == 'property':
            if self.prop_name and self.curr_prop:
                self.props[self.prop_name] = ''.join(self.curr_prop)
            self.prop_name = None
            self.curr_prop = []
        elif name == 'extraproperties':
            code_obj.properties['extraproperties'] = self.props
            return True  # to remove this handler

    def char_data(self, data):
        data = data.strip()
        if data:
            self.curr_prop.append(data)

# end of class ExtraPropertiesPropertyHandler


# custom property handlers
class FontPropertyHandler(object):
    """Handler for font properties"""

    font_families = {'default': 'wxDEFAULT', 'decorative': 'wxDECORATIVE',
                     'roman': 'wxROMAN', 'swiss': 'wxSWISS',
                     'script': 'wxSCRIPT', 'modern': 'wxMODERN',
                     'teletype': 'wxTELETYPE'}
    font_styles = {'normal': 'wxNORMAL', 'slant': 'wxSLANT',
                   'italic': 'wxITALIC'}
    font_weights = {'normal': 'wxNORMAL', 'light': 'wxLIGHT',
                    'bold': 'wxBOLD'}

    def __init__(self):
        self.dicts = {'family': self.font_families, 'style': self.font_styles,
                      'weight': self.font_weights}
        self.attrs = {'size': '0', 'style': '0', 'weight': '0', 'family': '0',
                       'underlined': '0', 'face': ''}
        self.current = None
        self.curr_data = []

    def start_elem(self, name, attrs):
        self.curr_data = []
        if name != 'font' and name in self.attrs:
            self.current = name
        else:
            self.current = None

    def end_elem(self, name, code_obj):
        if name == 'font':
            code_obj.properties['font'] = self.attrs
            return True
        elif self.current is not None:
            decode = self.dicts.get(self.current)
            if decode:
                val = decode.get("".join(self.curr_data), '0')
            else:
                val = "".join(self.curr_data)
            self.attrs[self.current] = val

    def char_data(self, data):
        self.curr_data.append(data)

# end of class FontPropertyHandler


class BaseSourceFileContent(object):
    """\
    Keeps info about an existing file that has to be updated, to replace only
    the lines inside a wxGlade block, an to keep the rest of the file as it was

    @ivar classes:        Classes declared in the file
    @type classes:        dict

    @ivar class_name:     Name of the current processed class
    @type class_name:     str

    @ivar content:        Content of the source file, if it existed
                          before this session of code generation
    @type content:        str

    @ivar event_handlers: List of event handlers for each class
    @type event_handlers: dict

    @ivar name:           Name of the file
    @type name:           str

    @ivar new_classes:    New classes to add to the file (they are inserted
                          BEFORE the old ones)
    @type new_classes:    list

    @ivar new_classes_inserted: Flag if the placeholder for new classes has
                                been inserted in source file already
    @type new_classes_inserted: bool

    @ivar code_writer: Reference to the parent code writer object
    @type code_writer: BaseLangCodeWriter
    
    @ivar spaces: Indentation level for each class
    @type spaces: str

    @cvar rec_block_start:   Regexp to match the begin of a wxglade block
    @cvar rec_block_end:     Regexp to match the end of a wxGlade block
    @cvar rec_class_decl:    Regexp to match class declarations
    @cvar rec_event_handler: Regexp to match event handlers

    @ivar _logger: Class specific logging instance
    """

    def __init__(self, name, code_writer):
        # initialise instance logger
        self._logger = logging.getLogger(self.__class__.__name__)

        # initialise instance
        self.name = name
        self.code_writer = code_writer
        self.content = None
        self.new_classes = []
        self.classes = {}
        self.spaces = {}
        self.event_handlers = {}
        self.nonce = code_writer.nonce
        self.out_dir = code_writer.out_dir
        self.multiple_files = code_writer.multiple_files
        if not self.content:
            self.build_untouched_content()
        self.class_name = None
        self.new_classes_inserted = False

    def build_untouched_content(self):
        """\
        Builds a string with the contents of the file that must be left as is,
        and replaces the wxGlade blocks with tags that in turn will be replaced
        by the new wxGlade blocks
        """
        self.class_name = None
        self.new_classes_inserted = False

    def format_classname(self, class_name):
        """\
        Format class name read from existing source file

        @param class_name: Class name
        @type class_name:  str

        @rtype: str

        @note: You may overwrite this function in the derived class
        """
        return class_name

    def is_end_of_class(self, line):
        """\
        True if the line is the marker for class end.
        
        @rtype: bool
        """
        return line.strip().startswith('# end of class ')

    def is_import_line(self, line):
        """\
        True if the line imports wx

        @note: You may overwrite this function in the derived class
        
        @rtype: bool
        """
        return False

    def _load_file(self, filename):
        """\
        Load a file and return the content

        The read source file will be decoded to unicode automatically.

        @note: Separated for debugging purposes

        @rtype: list[str] | list[Unicode]
        """
        fh = open(filename)
        lines = fh.readlines()
        fh.close()

        encoding = self.code_writer.app_encoding
        if encoding:
            try:
                lines = [line.decode(encoding) for line in lines]
            except UnicodeDecodeError:
                raise errors.WxgReadSourceFileUnicodeError(filename)

        return lines

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_logger']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

        # re-initialise logger instance deleted from __getstate__
        self._logger = logging.getLogger(self.__class__.__name__)

# end of class BaseSourceFileContent


class BaseWidgetHandler(object):
    """\
    Interface the various code generators for the widgets must implement
    """

    import_modules = []
    """\
    List of modules to import (eg. ['use Wx::Grid;\n'])
    """

    def __init__(self):
        """\
        Initialise instance variables
        """
        self.import_modules = []

    def get_code(self, obj):
        """\
        Handler for normal widgets (non-toplevel): returns 3 lists of strings,
        init, properties and layout, that contain the code for the
        corresponding methods of the class to generate
        """
        return [], [], []

    def get_properties_code(self, obj):
        """\
        Handler for the code of the set_properties method of toplevel objects.
        Returns a list of strings containing the code to generate
        """
        return []

    def get_init_code(self, obj):
        """\
        Handler for the code of the constructor of toplevel objects.  Returns a
        list of strings containing the code to generate.  Usually the default
        implementation is ok (i.e. there are no extra lines to add). The
        generated lines are appended at the end of the constructor
        """
        return []

    def get_layout_code(self, obj):
        """\
        Handler for the code of the do_layout method of toplevel objects.
        Returns a list of strings containing the code to generate.
        Usually the default implementation is ok (i.e. there are no
        extra lines to add)
        """
        return []

# end of class BaseWidgetHandler

class BaseLangCodeWriter(wcodegen.BaseCodeWriter):
    """\
    Dictionary of objects used to generate the code in a given language.

    A code writer object B{must} implement those interface and set those
    variables:
      - L{init_lang()}
      - L{init_files()}
      - L{finalize()}
      - L{wcodegen.BaseLanguageMixin.language}
      - L{add_app()}
      - L{add_class()}
      - L{add_object()}
      - L{add_property_handler()}
      - L{add_sizeritem()}
      - L{add_widget_handler()}
      - L{generate_code_background()}
      - L{generate_code_font()}
      - L{generate_code_foreground()}
      - L{generate_code_id()}
      - L{generate_code_size()}
      - L{_get_code_name()}
      - L{_code_statements}

    A code writer object B{could} implement those interfaces and set those
    variables:
      - L{setup()}
      - L{quote_str()}
      - L{quote_path()}
      - L{wcodegen.BaseLanguageMixin.cn()}
      - L{wcodegen.BaseLanguageMixin.cn_f()}

    @ivar app_encoding: Encoding of the application; will be initialised with
                        L{config.default_encoding}
    @type app_encoding: str

    @ivar app_filename: File name to store the application start code within
                        multi file projects
    @type app_filename: str

    @ivar app_mapping: Default mapping of template variables for substituting
                       in templates (see L{lang_mapping}, L{add_app()})
    @type app_mapping: dict

    @ivar lang_mapping: Language specific mapping of template variables for
                        substituting in templates (see L{app_mapping},
                        L{add_app()})
    @type lang_mapping: dict

    @ivar app_name: Application name
    @type app_name: str

    @ivar blacklisted_widgets: Don't add those widgets to sizers because they
        are not supported for the requested wx version or there is no code
        generator available.
    @type blacklisted_widgets: dict

    @ivar classes: Dictionary that maps the lines of code of a class to the
                   name of such class:
                   the lines are divided in 3 categories: '__init__',
                   '__set_properties' and '__do_layout'
    @type classes: dict

    @ivar curr_tab: Current indentation level
    @type curr_tab: int

    @ivar for_version: wx version we are generating code for (e.g. C{(2, 8)})
    @type for_version: Tuple of major and minor version number

    @ivar header_lines: Lines common to all the generated files
                        (import of wxCL, ...)
    @type header_lines: list[str]

    @ivar indent_amount: An indentation level is L{indent_symbol} *
                         L{indent_amount}; will be initialised
                         with L{config.default_indent_amount}
    @type indent_amount: int

    @ivar indent_symbol: Character to use for indentation; will be initialised
                         with L{config.default_indent_symbol}
    @type indent_symbol: str

    @ivar multiple_files: If True, generate a file for each custom class
    @type multiple_files: bool

    @ivar nonce: Random number used to be sure that the replaced tags in the
                 sources are the right ones (see L{BaseSourceFileContent},
                 L{add_class} and L{create_nonce})
    @type nonce: str

    @ivar obj_builders: "writers" for the various objects
    @type obj_builders: dict

    @ivar obj_properties: "property writer" functions, used to set the
                          properties of a toplevel object
    @type obj_properties: dict

    @ivar out_dir: If not None, it is the directory inside which the output
                   files are saved
    @type out_dir: None | str

    @ivar output_file: Output string buffer for the code
    @type output_file: None or StringIO

    @ivar output_file_name: Name of the output file
    @type output_file_name: str

    @ivar previous_source: If not None, it is an instance of
                           L{BaseSourceFileContent} that keeps info about the
                           previous version of the source to generate
    @type previous_source: None | BaseSourceFileContent

    @ivar _app_added: True after wxApp instance has been generated
    @type _app_added: bool

    @ivar _current_extra_code: Set of lines for extra code to add to the
                               current file
    @type _current_extra_code: list[str]

    @ivar _current_extra_modules: Set of lines of extra modules to add to the
                                  current file
    @type _current_extra_modules: list[str]

    @ivar _overwrite: If True, overwrite any previous version of the source
                      file instead of updating only the wxGlade blocks; 
                      will be initialised with L{config.default_overwrite}
    @type _overwrite: bool

    @ivar _property_writers: Dictionary of dictionaries of property handlers
                             specific for a widget the keys are the class
                             names of the widgets (E.g.
                             _property_writers['wxRadioBox'] = {'choices',
                             choices_handler})
    @type _property_writers: dict

    @ivar _textdomain: gettext textdomain (see L{_use_gettext})
    @type _textdomain: str

    @ivar _use_gettext: If True, enable gettext support; will be initialised
                        with L{config.default_use_gettext} (see
                        L{_textdomain})
    @type _use_gettext: bool

    @ivar _widget_extra_modules: Map of widget class names to a list of extra
                                 modules needed for the widget (e.g.
                                 C{'wxGrid': 'from wxLisp.grid import *\\n'}).
    @type _widget_extra_modules: dict
    """

    _code_statements = {}
    """\
    Language specific code templates for for small statements.

    The statements are stored in a dictionary. The property names are the
    keys.
    
    The keys may have one of two different extensions: 
     - "C{_<major version>X}" e.g. "C{tooltip_3X}" to generate tooltips source
       code for wxWidgets 3.x
     - "C{_<major version><minor version>}" e.g. "C{wxcolour_28}" to generate
       source code for wxWidgets 2.8 only

    The extensions will be evaluated from most specific to generic.

    Example::
        >>> _code_statements = {
        ... 'disabled':    "<code sequence for all wxWidget versions>",
        ... 'wxcolour_28': "<code sequence for wxWidgets 2.8 only>",
        ... 'tooltip_3':  "<code sequence for wxWidgets 3.X only>",
        }

    The function L{_get_code_statement()} handles the extensions properly and
    returns the requested template.

    @type: dict[str]
    @see: L{_get_code_statement()}
    @see: L{_generic_code()}
    @see: L{generate_code_extraproperties()}
    """

    classattr_always = []
    """\
    List of classes to store always as class attributes
    
    @type: list[str]
    @see: L{test_attribute()}
    """

    class_separator = ''
    """\
    Separator between class and attribute or between different name space
    elements.
    
    E.g "." for Python or "->" for Perl.
    
    @type: str
    """

    global_property_writers = {}
    """\
    Custom handlers for widget properties

    @type: dict
    """

    indent_level_func_body = 1
    """\
    Indentation level for bodies of class functions.
    
    @type: int
    """

    language_note = ""
    """\
    Language specific notice written into every file header

    @note: Please add a newline sequence to the end of the language note.
    @type: str
    @see:  L{save_file()}
    """

    name_ctor = ''
    """\
    Name of the constructor. E.g. "__init__" in Python or "new" in Perl.
    
    @type: str
    """

    shebang = None
    """\
    Shebang line, the first line of the generated main files.

    @note: Please add a newline sequence to the end of the shebang.
    @type: str
    @see:  L{save_file()}
    """

    SourceFileContent = None
    """\
    Just a reference to the language specific instance of SourceFileContent
    
    @type: BaseSourceFileContent
    """

    tmpl_encoding = None
    """\
    Template of the encoding notices

    The file encoding will be added to the output in L{save_file()}.

    @type: str
    """

    tmpl_block_begin = '%(tab)s%(comment_sign)s begin wxGlade: ' \
                       '%(klass)s%(class_separator)s%(function)s\n'

    tmpl_cfunc_end = ''
    """\
    Statement to add at the end of a class function. e.g.
    'return $self;' for Perl.
    
    @type: str
    """

    tmpl_class_end = ''
    """\
    Statement to add at the end of a class.
    
    @type: str
    """

    tmpl_ctor_call_layout = ''
    """\
    Code add to the contructor to call '__do_layout()' and
    '__set_properties()'.
    
    @type: str
    """

    tmpl_name_do_layout = ''
    """\
    Name of the function __do_layout() in wxGlade begin tag.
    
    This name differs between the various code generators.
    
    @type: str
    @see: L{generate_code_do_layout()}
    """

    tmpl_name_set_properties = ''
    """\
    Name of the function __set_properties() in wxGlade begin tag.
    
    This name differs between the various code generators.
    
    @type: str
    @see:  L{generate_code_set_properties()}
    """
    
    tmpl_func_empty = ''
    """\
    Statement for an empty function e.g. "pass" for Python or "return;" for
    perl.
    
    @note: This statement differs between the various code generators.
    @type: str
    """

    tmpl_func_do_layout = ''
    """\
    Statement for the __do_layout() function.
    
    @note: This statement differs between the various code generators.
    
    @type: str
    @see: L{generate_code_do_layout()}
    """

    tmpl_func_event_stub = ''
    """\
    Statement for a event handler stub.
    
    @note: This statement differs between the various code generators.
    
    @type: str
    @see: L{generate_code_event_handler()}
    """

    tmpl_func_set_properties = ''
    """\
    Statement for the __set_properties() function.
    
    @note: This statement differs between the various code generators.
    
    @type: str
    @see: L{generate_code_set_properties()}
    """

    tmpl_generated_by = \
        "%(comment_sign)s %(generated_by)s\n%(comment_sign)s\n"
    """\
    Template of the "generated by ..." message

    @type: str
    @see: L{create_generated_by()}
    @see: L{save_file()}
    """

    tmpl_overwrite = \
        "%(comment_sign)s This is an automatically generated file.\n" \
        "%(comment_sign)s Manual changes will be overwritten without " \
        "warning!\n\n"
    """\
    Template of the overwrite message in all standalone app files.

    @type: str
    @see: L{add_app()}
    """

    tmpl_sizeritem = ''
    """\
    Template for adding a widget to a sizer.
    
    @type: str
    @see: L{add_sizeritem()}
    """

    tmpl_style = ''
    """\
    Template for setting style in constructor
    
    @type: str
    @see:  L{_format_style()}
    """

    tmpl_appfile = None
    """\
    Template of the file header for standalone files with application start
    code.

    A standalone file will be created if a separate file for each class is
    selected.

    @type: None | str
    @see: L{add_app}
    """

    tmpl_detailed = None
    """\
    Template for detailed application start code without gettext support

    @type: None | str
    @see: L{add_app}
    """

    tmpl_gettext_detailed = None
    """\
    Template for detailed application start code with gettext support

    @type: None | str
    @see: L{add_app}
    """

    tmpl_simple = None
    """\
    Template for simplified application start code without gettext support

    @type: None | str
    @see: L{add_app}
    """

    tmpl_gettext_simple = None
    """\
    Template for simplified application start code with gettext support

    @type: None or str
    @see: L{add_app}
    """

    tmpl_empty_string = '""'
    """\
    Template for an empty string.
    """

    _show_warnings = True
    """\
    Enable or disable printing of warning messages

    @type: bool
    @see: L{self.warning()}
    """

    class ClassLines(object):
        """\
        Stores the lines of source code for a custom class

        @ivar dependencies:      Names of the modules this class depends on
        @ivar event_handlers:    Lines to bind events (see
                                 L{wcodegen.BaseWidgetWriter.get_event_handlers()})
        @ivar extra_code:        Extra code to output before this class
        @ivar done:              If True, the code for this class has already
                                 been generated
        @ivar init:              Lines of code to insert in the __init__ method
                                 (for children widgets)
        @ivar layout:            Lines to insert in the __do_layout method
        @ivar parents_init:      Lines of code to insert in the __init__ for
                                 container widgets (panels, splitters, ...)
        @ivar props:             Lines to insert in the __set_properties method
        @ivar sizers_init :      Lines related to sizer objects declarations
        """
        def __init__(self):
            self.child_order = []
            self.dependencies = {}
            self.deps = []
            self.done = False
            self.event_handlers = []
            self.extra_code = []
            self.init = []
            self.init_lines = {}
            self.layout = []
            self.parents_init = []
            self.props = []
            self.sizers_init = []

    # end of class ClassLines

    DummyPropertyHandler = DummyPropertyHandler
    EventsPropertyHandler = EventsPropertyHandler
    ExtraPropertiesPropertyHandler = ExtraPropertiesPropertyHandler
    FontPropertyHandler = FontPropertyHandler

    def __init__(self):
        """\
        Initialise only instance variables using there defaults.
        """
        wcodegen.BaseCodeWriter.__init__(self)
        self.obj_builders = {}
        self.obj_properties = {}
        self._property_writers = {}
        self._init_vars()

    def _init_vars(self):
        """\
        Set instance variables (back) to default values during class
        instantiation (L{__init__}) and before loading new data
        (L{initialize()}).
        """
        self.app_encoding = config.default_encoding
        self.app_filename = None
        self.app_mapping = {}
        self.app_name = None
        self.classes = {}
        self.curr_tab = 0
        self.dependencies = {}
        self.for_version = config.for_version
        self.header_lines = []
        self.indent_symbol = config.default_indent_symbol
        self.indent_amount = config.default_indent_amount
        self.is_template = 0
        self.blacklisted_widgets = {}
        self.lang_mapping = {}
        self.multiple_files = False

        # this is to be more sure to replace the right tags
        self.nonce = self.create_nonce()

        self.out_dir = None
        self.output_file_name = None
        self.output_file = None
        self.previous_source = None
        self._app_added = False
        self._current_extra_code = []
        self._current_extra_modules = {}
        self._overwrite = config.default_overwrite
        self._textdomain = 'app'
        self._use_gettext = config.default_use_gettext
        self._widget_extra_modules = {}

    def initialize(self, app_attrs):
        """\
        Initialise generic and language independent code generator settings.

        @see: L{init_lang()}
        @see: L{init_files()}
        """
        # set (most of) instance variables back to default values
        self._init_vars()

        self.multiple_files = app_attrs.get('option',
                                            config.default_multiple_files)

        # application name
        self.app_name = app_attrs.get('name')
        if self.app_name:
            self.app_filename = '%s.%s' % (
                self.app_name,
                self.default_extensions[0],
            )
            self._textdomain = self.app_name

        # file encoding
        try:
            self.app_encoding = app_attrs['encoding'].upper()
            # wx doesn't like latin-1
            if self.app_encoding == 'latin-1':
                self.app_encoding = 'ISO-8859-1'
        except (KeyError, ValueError):
            # set back to default
            self.app_encoding = config.default_encoding

        # Indentation level based on the project options
        try:
            self.indent_symbol = app_attrs['indent_symbol']
            if self.indent_symbol == 'tab':
                self.indent_symbol = '\t'
            elif self.indent_symbol == 'space':
                self.indent_symbol = ' '
            else:
                self.indent_symbol = config.default_indent_symbol
        except (KeyError, ValueError):
            self.indent_symbol = config.default_indent_symbol

        try:
            self.indent_amount = int(app_attrs['indent_amount'])
        except (KeyError, ValueError):
            self.indent_amount = config.default_indent_amount

        try:
            self._use_gettext = int(app_attrs['use_gettext'])
        except (KeyError, ValueError):
            self._use_gettext = config.default_use_gettext

        try:
            self._overwrite = int(app_attrs['overwrite'])
        except (KeyError, ValueError):
            self._overwrite = config.default_overwrite

        try:
            self.for_version = tuple([int(t) for t in
                                      app_attrs['for_version'].split('.')[:2]])
        except (KeyError, ValueError):
            if common.app_tree is not None:
                self.for_version = \
                tuple([int(t) for t in
                       common.app_tree.app.for_version.split('.')])

        try:
            self.is_template = int(app_attrs['is_template'])
        except (KeyError, ValueError):
            self.is_template = 0

        if self.multiple_files:
            self.out_dir = app_attrs.get('path', config.default_output_path)
        else:
            self.out_dir = app_attrs.get('path', config.default_output_file)
        self.out_dir = os.path.normpath(
            os.path.expanduser(self.out_dir.strip()))

        # call initialisation of language specific settings
        self.init_lang(app_attrs)

        # check the validity of the set values
        self.check_values()

        # call initialisation of the file handling
        self.init_files(self.out_dir)

    def init_lang(self, app_attrs):
        """\
        Initialise language specific settings.

        @note: You may overwrite this function in the derived class
        """
        raise NotImplementedError

    def init_files(self, out_path):
        """\
        Initialise the file handling

        @param out_path: Output path for the generated code (a file if
                         L{self.multiple_files} is False, a dir otherwise)
        @type out_path: str | None

        @note: You may overwrite this function in the derived class
        """
        if self.multiple_files:
            self.previous_source = None
            if not os.path.isdir(out_path):
                raise errors.WxgOutputPathIsNotDirectory(out_path)
            self.out_dir = out_path
        else:
            if os.path.isdir(out_path):
                raise errors.WxgOutputPathIsDirectory(out_path)
            if not self._overwrite and self._file_exists(out_path):
                # the file exists, we must keep all the lines not inside a
                # wxGlade block. NOTE: this may cause troubles if out_path is
                # not a valid source file, so be careful!
                self.previous_source = self.SourceFileContent(out_path, self)
            else:
                # if the file doesn't exist, create it and write the ``intro''
                self.previous_source = None
                self.output_file = StringIO.StringIO()
                self.output_file_name = out_path
                for line in self.header_lines:
                    self.output_file.write(line)
                self.output_file.write('<%swxGlade extra_modules>\n' % self.nonce)
                self.output_file.write('\n')
                self.output_file.write('<%swxGlade replace dependencies>\n' % self.nonce)
                self.output_file.write('<%swxGlade replace extracode>\n' % self.nonce)

    def check_values(self):
        """\
        Check the validity of the set application values. Raises exceptions for
        errors.

        @see: L{errors}
        """
        # Check if the values of use_multiple_files and out_path agree
        if self.multiple_files:
            if not os.path.isdir(self.out_dir):
                raise errors.WxgOutputDirectoryNotExist(self.out_dir)
            if not os.access(self.out_dir, os.W_OK):
                raise errors.WxgOutputDirectoryNotWritable(self.out_dir)
        else:
            if os.path.isdir(self.out_dir):
                raise errors.WxgOutputPathIsDirectory(self.out_dir)
            directory = os.path.dirname(self.out_dir)
            if directory:
                if not os.path.isdir(directory):
                    raise errors.WxgOutputDirectoryNotExist(directory)
                if not os.access(directory, os.W_OK):
                    raise errors.WxgOutputDirectoryNotWritable(directory)

        # It's not possible to generate code from a template directly
        if self.is_template:
            raise errors.WxgTemplateCodegenNotPossible

    def finalize(self):
        """\
        Code generator finalization function.
        """
        if self.previous_source:
            # insert all the new custom classes inside the old file
            tag = '<%swxGlade insert new_classes>' % self.nonce
            if self.previous_source.new_classes:
                code = "".join(self.previous_source.new_classes)
            else:
                code = ""
            self.previous_source.content = self.previous_source.content.replace(tag, code)
            tag = '<%swxGlade extra_modules>\n' % self.nonce
            code = "".join(self._current_extra_modules.keys())
            self.previous_source.content = self.previous_source.content.replace(tag, code)

            # module dependencies of all classes
            tag = '<%swxGlade replace dependencies>' % self.nonce
            dep_list = self.dependencies.keys()
            dep_list.sort()
            code = self._tagcontent('dependencies', dep_list)
            self.previous_source.content = \
                self.previous_source.content.replace(tag, code)

            # extra code (see the 'extracode' property of top-level widgets)
            tag = '<%swxGlade replace extracode>' % self.nonce
            code = self._tagcontent(
                'extracode',
                self._current_extra_code
                )
            self.previous_source.content = \
                self.previous_source.content.replace(tag, code)

            # now remove all the remaining <123415wxGlade ...> tags from the
            # source: this may happen if we're not generating multiple files,
            # and one of the container class names is changed
            self.previous_source.content = self._content_notfound(
                self.previous_source.content
                )

            tags = re.findall(
                r'<%swxGlade event_handlers \w+>' % self.nonce,
                self.previous_source.content
                )
            for tag in tags:
                self.previous_source.content = self.previous_source.content.replace(tag, "")

            # write the new file contents to disk
            self.save_file(
                self.previous_source.name,
                self.previous_source.content,
                content_only=True
                )

        elif not self.multiple_files:
            em = "".join(self._current_extra_modules.keys())
            content = self.output_file.getvalue().replace(
                '<%swxGlade extra_modules>\n' % self.nonce, em)

            # module dependencies of all classes
            tag = '<%swxGlade replace dependencies>' % self.nonce
            dep_list = self.dependencies.keys()
            dep_list.sort()
            code = self._tagcontent('dependencies', dep_list)
            content = content.replace(tag, code)

            # extra code (see the 'extracode' property of top-level widgets)
            tag = '<%swxGlade replace extracode>' % self.nonce
            code = self._tagcontent('extracode', self._current_extra_code)
            content = content.replace(tag, code)

            self.output_file.close()
            self.save_file(self.output_file_name, content, self._app_added)
            del self.output_file

    def add_app(self, app_attrs, top_win_class):
        """\
        Generates the code for a wxApp instance.
        If the file to write into already exists, this function does nothing.

        If gettext support is requested and there is not template with
        gettext support but there is a template without gettext support,
        template without gettext support will be used.

        This fallback mechanism works bidirectional.

        L{app_mapping} will be reset to default values and updated with
        L{lang_mapping}.

        @see: L{tmpl_appfile}
        @see: L{tmpl_detailed}
        @see: L{tmpl_gettext_detailed}
        @see: L{tmpl_simple}
        @see: L{tmpl_gettext_simple}
        @see: L{app_mapping}
        @see: L{lang_mapping}
        """
        self._app_added = True

        if not self.multiple_files:
            prev_src = self.previous_source
        else:
            # overwrite apps file always
            prev_src = None

        # do nothing if the file exists
        if prev_src:
            return

        klass = app_attrs.get('class')
        top_win = app_attrs.get('top_window')

        # top window and application name are mandatory
        if not top_win or not self.app_name:
            return

        # check for templates for detailed startup code
        if klass and self._use_gettext:
            if self.tmpl_gettext_detailed:
                tmpl = self.tmpl_gettext_detailed
            else:
                self.warning(
                    _("Skip generating detailed startup code "
                      "because no suitable template found.")
                    )
                return

        elif klass and not self._use_gettext:
            if self.tmpl_detailed:
                tmpl = self.tmpl_detailed
            else:
                self.warning(
                    _("Skip generating detailed startup code "
                      "because no suitable template found.")
                    )
                return

        # check for templates for simple startup code
        elif not klass and self._use_gettext:
            if self.tmpl_gettext_simple:
                tmpl = self.tmpl_gettext_simple
            else:
                self.warning(
                    _("Skip generating simple startup code "
                      "because no suitable template found.")
                    )
                return
        elif not klass and not self._use_gettext:
            if self.tmpl_simple:
                tmpl = self.tmpl_simple
            else:
                self.warning(
                    _("Skip generating simple startup code "
                      "because no suitable template found.")
                    )
                return
        else:
            self.warning(
                _('No application code template for klass "%(klass)s" '
                  'and gettext "%(gettext)s" found!' % {
                        'klass':   klass,
                        'gettext': self._use_gettext,
                        }
                  ))
            return

        # map to substitute template variables
        self.app_mapping = {
            'comment_sign': self.comment_sign,
            'header_lines': ''.join(self.header_lines),
            'klass': klass,
            'name': self.app_name,
            'overwrite': self.tmpl_overwrite % {'comment_sign': self.comment_sign},
            'tab': self.tabs(1),
            'textdomain': self._textdomain,
            'top_win_class': top_win_class,
            'top_win': top_win,
            }

        # extend default mapping with language specific mapping
        if self.lang_mapping:
            self.app_mapping.update(self.lang_mapping)

        code = tmpl % self.app_mapping

        if self.multiple_files:
            filename = os.path.join(self.out_dir, self.app_filename)
            code = "%s%s" % (
                self.tmpl_appfile % self.app_mapping,
                code,
                )
            # write the wxApp code
            self.save_file(filename, code, True)
        else:
            self.output_file.write(code)

    def add_class(self, code_obj):
        """\
        Add class behaves very differently for XRC output than for other
        languages (i.e. python): since custom classes are not supported in
        XRC, this has effect only for true toplevel widgets, i.e. frames and
        dialogs. For other kinds of widgets, this is equivalent to add_object
        """
        if self.classes.has_key(code_obj.klass) and \
           self.classes[code_obj.klass].done:
            return  # the code has already been generated

        if self.multiple_files:
            # let's see if the file to generate exists, and in this case
            # create a SourceFileContent instance
            filename = self._get_class_filename(code_obj.klass)
            if self._overwrite or not self._file_exists(filename):
                prev_src = None
            else:
                prev_src = self.SourceFileContent(filename, self)
            self._current_extra_modules = {}
        else:
            # in this case, previous_source is the SourceFileContent instance
            # that keeps info about the single file to generate
            prev_src = self.previous_source

        try:
            builder = self.obj_builders[code_obj.base]
            mycn = getattr(builder, 'cn', self.cn)
            mycn_f = getattr(builder, 'cn_f', self.cn_f)
        except KeyError:
            self._logger.error('%s', code_obj)
            # this is an error, let the exception be raised
            # the details are logged by the global exception handler
            raise

        if prev_src and prev_src.classes.has_key(code_obj.klass):
            is_new = False
            indentation = prev_src.spaces[code_obj.klass]
        else:
            # this class wasn't in the previous version of the source (if any)
            is_new = True
            indentation = self.tabs(self.indent_level_func_body)
            mods = getattr(builder, 'extra_modules', [])
            if mods:
                for m in mods:
                    self._current_extra_modules[m] = 1

        obuffer = []
        write = obuffer.append

        if not self.classes.has_key(code_obj.klass):
            # if the class body was empty, create an empty ClassLines
            self.classes[code_obj.klass] = self.ClassLines()

        # collect all event handlers
        event_handlers = self.classes[code_obj.klass].event_handlers
        for win_id, evt, handler, evt_type in builder.get_event_handlers(code_obj):
            event_handlers.append((win_id, mycn(evt), handler, evt_type))

        # try to see if there's some extra code to add to this class
        if not code_obj.preview:
            extra_code = getattr(builder, 'extracode',
                                 code_obj.properties.get('extracode', ""))
            if extra_code:
                extra_code = re.sub(r'\\n', '\n', extra_code)
                self.classes[code_obj.klass].extra_code.append(extra_code)
                if not is_new:
                    self.warning(
                        '%s has extra code, but you are not overwriting '
                        'existing sources: please check that the resulting '
                        'code is correct!' % code_obj.name
                        )

            # Don't add extra_code to self._current_extra_code here, that is
            # handled later.  Otherwise we'll emit duplicate extra code for
            # frames.

        tab = indentation

        # generate code for first constructor stage
        code_lines = self.generate_code_ctor(code_obj, is_new, tab)
        obuffer.extend(code_lines)

        # now check if there are extra lines to add to the constructor
        if hasattr(builder, 'get_init_code'):
            for l in builder.get_init_code(code_obj):
                write(tab + l)

        write(self.tmpl_ctor_call_layout % {
            'tab': tab,
            })

        # generate code for binding events
        code_lines = self.generate_code_event_bind(
            code_obj,
            tab,
            event_handlers,
            )
        obuffer.extend(code_lines)

        # end tag
        write('%s%s end wxGlade\n' % (tab, self.comment_sign))

        # write class function end statement
        if self.tmpl_cfunc_end and is_new:
            write(self.tmpl_cfunc_end % {
                'tab': tab,
                })

        # end of ctor generation

        # replace code inside existing constructor block
        if prev_src and not is_new:
            # replace the lines inside the ctor wxGlade block
            # with the new ones
            tag = '<%swxGlade replace %s %s>' % (self.nonce, code_obj.klass,
                                                 self.name_ctor)
            if prev_src.content.find(tag) < 0:
                # no __init__ tag found, issue a warning and do nothing
                self.warning(
                    "wxGlade %(ctor)s block not found for %(name)s, %(ctor)s code "
                    "NOT generated" % {
                        'name': code_obj.name,
                        'ctor': self.name_ctor,
                        }
                    )
            else:
                prev_src.content = prev_src.content.replace(tag, "".join(obuffer))
            obuffer = []
            write = obuffer.append

        # generate code for __set_properties()
        code_lines = self.generate_code_set_properties(
            builder,
            code_obj,
            is_new,
            tab
            )
        obuffer.extend(code_lines)

        # replace code inside existing __set_properties() function
        if prev_src and not is_new:
            # replace the lines inside the __set_properties wxGlade block
            # with the new ones
            tag = '<%swxGlade replace %s %s>' % (self.nonce, code_obj.klass,
                                                 '__set_properties')
            if prev_src.content.find(tag) < 0:
                # no __set_properties tag found, issue a warning and do nothing
                self.warning(
                    "wxGlade __set_properties block not found for %s, "
                    "__set_properties code NOT generated" % code_obj.name
                    )
            else:
                prev_src.content = prev_src.content.replace(tag, "".join(obuffer))
            obuffer = []
            write = obuffer.append

        # generate code for __do_layout()
        code_lines = self.generate_code_do_layout(
            builder,
            code_obj,
            is_new,
            tab
            )
        obuffer.extend(code_lines)

        # replace code inside existing __do_layout() function
        if prev_src and not is_new:
            # replace the lines inside the __do_layout wxGlade block
            # with the new ones
            tag = '<%swxGlade replace %s %s>' % (self.nonce, code_obj.klass,
                                                 '__do_layout')
            if prev_src.content.find(tag) < 0:
                # no __do_layout tag found, issue a warning and do nothing
                self.warning(
                    "wxGlade __do_layout block not found for %s, __do_layout "
                    "code NOT generated" % code_obj.name
                    )
            else:
                prev_src.content = prev_src.content.replace(tag, "".join(obuffer))

        # generate code for event handler stubs
        code_lines = self.generate_code_event_handler(
            code_obj,
            is_new,
            tab,
            prev_src,
            event_handlers,
            )

        # replace code inside existing event handlers
        if prev_src and not is_new:
            tag = \
                '<%swxGlade event_handlers %s>' % (self.nonce, code_obj.klass)
            if prev_src.content.find(tag) < 0:
                # no event_handlers tag found, issue a warning and do nothing
                self.warning(
                    "wxGlade event_handlers block not found for %s, "
                    "event_handlers code NOT generated" % code_obj.name
                    )
            else:
                prev_src.content = prev_src.content.replace(
                    tag,
                    "".join(code_lines),
                    )
        else:
            obuffer.extend(code_lines)

        # the code has been generated
        self.classes[code_obj.klass].done = True

        # write "end of class" statement
        if self.tmpl_class_end:
            write(
                self.tmpl_class_end % {
                    'klass':   self.cn_class(code_obj.klass),
                    'comment': self.comment_sign,
                    }
                )

        if self.multiple_files:
            if prev_src:
                tag = '<%swxGlade insert new_classes>' % self.nonce
                prev_src.content = prev_src.content.replace(tag, "")

                # insert the extra modules
                tag = '<%swxGlade extra_modules>\n' % self.nonce
                code = "".join(self._current_extra_modules.keys())
                prev_src.content = prev_src.content.replace(tag, code)

                # insert the module dependencies of this class
                tag = '<%swxGlade replace dependencies>' % self.nonce
                dep_list = self.classes[code_obj.klass].dependencies.keys()
                dep_list.extend(self.dependencies.keys())
                dep_list.sort()
                code = self._tagcontent('dependencies', dep_list)
                prev_src.content = prev_src.content.replace(tag, code)

                # insert the extra code of this class
                extra_code = "".join(self.classes[code_obj.klass].extra_code[::-1])
                # if there's extra code but we are not overwriting existing
                # sources, warn the user
                if extra_code:
                    self.warning(
                        '%s (or one of its children) has extra '
                        'code classes, but you are not overwriting '
                        'existing sources: please check that the resulting '
                        'code is correct!' %
                        code_obj.name
                        )
                tag = '<%swxGlade replace extracode>' % self.nonce
                code = self._tagcontent('extracode', extra_code)
                prev_src.content = prev_src.content.replace(tag, code)

                # store the new file contents to disk
                self.save_file(filename, prev_src.content, content_only=True)
                return

            # create the new source file
            filename = self._get_class_filename(code_obj.klass)
            out = StringIO.StringIO()
            write = out.write
            # write the common lines
            for line in self.header_lines:
                write(line)

            # write the module dependencies for this class
            dep_list = self.classes[code_obj.klass].dependencies.keys()
            dep_list.extend(self.dependencies.keys())
            dep_list.sort()
            code = self._tagcontent('dependencies', dep_list, True)
            write(code)

            # insert the extra code of this class
            code = self._tagcontent(
                'extracode',
                self.classes[code_obj.klass].extra_code[::-1],
                True
                )
            write(code)

            # write the class body
            for line in obuffer:
                write(line)
            # store the contents to filename
            self.save_file(filename, out.getvalue())
            out.close()
        else:  # not self.multiple_files
            if prev_src:
                # if this is a new class, add its code to the new_classes
                # list of the SourceFileContent instance
                if is_new:
                    prev_src.new_classes.append("".join(obuffer))
                elif self.classes[code_obj.klass].extra_code:
                    self._current_extra_code.extend(self.classes[code_obj.klass].extra_code[::-1])
                return
            else:
                # write the class body onto the single source file
                for dep in self.classes[code_obj.klass].dependencies:
                    self._current_extra_modules[dep] = 1
                if self.classes[code_obj.klass].extra_code:
                    self._current_extra_code.extend(self.classes[code_obj.klass].extra_code[::-1])
                write = self.output_file.write
                for line in obuffer:
                    write(line)

    def add_object(self, top_obj, sub_obj):
        """\
        Adds the code to build 'sub_obj' to the class body of 'top_obj'.

        @see: L{_add_object_init()}
        @see: L{add_object_format_name()}
        """
        sub_obj.name = self._format_name(sub_obj.name)
        sub_obj.parent.name = self._format_name(sub_obj.parent.name)

        # get top level source code object and the widget builder instance
        klass, builder = self._add_object_init(top_obj, sub_obj)
        if not klass or not builder:
            return

        try:
            init, props, layout = builder.get_code(sub_obj)
        except:
            self._logger.error('%s', sub_obj)
            # this is an error, let the exception be raised
            # the details are logged by the global exception handler
            raise

        if sub_obj.in_windows:  # the object is a wxWindow instance
            if sub_obj.is_container and not sub_obj.is_toplevel:
                init.reverse()
                klass.parents_init.extend(init)
            else:
                klass.init.extend(init)

            # Add a dependency of the current object on its parent
            klass.deps.append((sub_obj, sub_obj.parent))
            klass.child_order.append(sub_obj)
            klass.init_lines[sub_obj] = init

            mycn = getattr(builder, 'cn', self.cn)
            for win_id, evt, handler, evt_type in \
                    builder.get_event_handlers(sub_obj):
                klass.event_handlers.append(
                    (win_id, mycn(evt), handler, evt_type))

            # try to see if there's some extra code to add to this class
            if not sub_obj.preview:
                extra_code = getattr(builder, 'extracode',
                                     sub_obj.properties.get('extracode', ""))
                if extra_code:
                    extra_code = re.sub(r'\\n', '\n', extra_code)
                    klass.extra_code.append(extra_code)
                    # if we are not overwriting existing source, warn the user
                    # about the presence of extra code
                    if not self.multiple_files and self.previous_source:
                        self.warning(
                            '%s has extra code, but you are not '
                            'overwriting existing sources: please check '
                            'that the resulting code is correct!' % \
                            sub_obj.name
                            )

        else:  # the object is a sizer
            if sub_obj.base == 'wxStaticBoxSizer':
                i = init.pop(0)
                klass.parents_init.insert(1, i)

                # Add a dependency of the current object on its parent
                klass.deps.append((sub_obj, sub_obj.parent))
                klass.child_order.append(sub_obj)
                klass.init_lines[sub_obj] = [i]

            klass.sizers_init.extend(init)

        klass.props.extend(props)
        klass.layout.extend(layout)
        if self.multiple_files and \
               (sub_obj.is_toplevel and sub_obj.base != sub_obj.klass):
            key = self._format_import(sub_obj.klass)
            klass.dependencies[key] = 1
        for dep in getattr(self.obj_builders.get(sub_obj.base),
                           'import_modules', []):
            klass.dependencies[dep] = 1

    def _add_object_init(self, top_obj, sub_obj):
        """\
        Perform some initial actions for L{add_object()}
        
        Widgets without code generator or widget that are not supporting the
        requested wx version are blacklisted at L{blacklisted_widgets}.

        @return: Top level source code object and the widget builder instance
                 or C{None, None} in case of errors.
        """
        # initialise internal variables first
        klass = None
        builder = None

        # Check for proper source code instance
        if top_obj.klass in self.classes:
            klass = self.classes[top_obj.klass]
        else:
            klass = self.classes[top_obj.klass] = self.ClassLines()

        # Check for widget builder object
        try:
            builder = self.obj_builders[sub_obj.base]
        except KeyError:
            # no code generator found: write a comment about it
            msg = _("""\
Code for instance "%s" of "%s" not generated: no suitable writer found""") % (
                sub_obj.name,
                sub_obj.klass, 
                )
            self._source_warning(klass, msg, sub_obj)
            self.warning(msg)
            # ignore widget later too
            self.blacklisted_widgets[sub_obj] = 1
            return None, None

        # check for supported versions
        if hasattr(builder, 'is_widget_supported'):
            is_supported = builder.is_widget_supported(*self.for_version)
        else:
            is_supported = True
        if not is_supported:
            supported_versions = ', '.join(
                [misc.format_supported_by(version) for version in
                 builder.config['supported_by']]
                )
            msg = _("""\
Code for instance "%(name)s" of "%(klass)s" was
not created, because the widget is not available for wx version %(requested_version)s.
It is available for wx versions %(supported_versions)s only.""") % {
                    'name':  sub_obj.name, 
                    'klass': sub_obj.klass, 
                    'requested_version':  str(misc.format_for_version(self.for_version)), 
                    'supported_versions': str(supported_versions), 
                    }
            self._source_warning(klass, msg, sub_obj)
            self.warning(msg)
            # ignore widget later too
            self.blacklisted_widgets[sub_obj] = 1
            return None, None

        return klass, builder

    def add_property_handler(self, property_name, handler, widget_name=None):
        """\
        Sets a function to parse a portion of XML to get the value of the
        property property_name. If widget_name is not None, the function is
        called only if the property in inside a widget whose class is
        widget_name.
        """
        if not widget_name:
            self.global_property_writers[property_name] = handler
        else:
            try:
                self._property_writers[widget_name][property_name] = handler
            except KeyError:
                self._property_writers[widget_name] = {property_name: handler}

    def add_sizeritem(self, toplevel, sizer, obj, option, flag, border):
        """\
        Writes the code to add the object 'obj' to the sizer 'sizer' in the
        'toplevel' object.
        
        All widgets in L{blacklisted_widgets} are ignored.
        
        @see: L{tmpl_sizeritem}
        """
        # don't process widgets listed in blacklisted_widgets
        if obj in self.blacklisted_widgets:
            return

        # the name attribute of a spacer is already formatted
        # "<width>, <height>". This string can simply inserted in Add() call.
        obj_name = self._format_classattr(obj)

        if toplevel.klass in self.classes:
            klass = self.classes[toplevel.klass]
        else:
            klass = self.classes[toplevel.klass] = self.ClassLines()

        # check if sizer has to store as a class attribute
        sizer_name = self._format_classattr(sizer)

        stmt = self.tmpl_sizeritem % (
            sizer_name,
            obj_name,
            option,
            self.cn_f(flag),
            border,
            )

        klass.layout.append(stmt)

    def add_widget_handler(self, widget_name, handler, *args, **kwds):
        self.obj_builders[widget_name] = handler

    def create_generated_by(self):
        """\
        Create I{generated by wxGlade} string without leading comment
        characters and without tailing new lines

        @rtype:  str
        """
        generated_from = ''
        if config.preferences.write_generated_from and common.app_tree and \
               common.app_tree.app.filename:
            generated_from = ' from "%s"' % common.app_tree.app.filename

        if config.preferences.write_timestamp:
            msg = 'generated by wxGlade %s on %s%s' % (
                config.version,
                time.asctime(),
                generated_from,
                )
        else:
            msg = 'generated by wxGlade %s%s' % (
                config.version,
                generated_from,
                )
        return msg

    def create_nonce(self):
        """\
        Create a random number used to be sure that the replaced tags in the
        sources are the right ones (see SourceFileContent and add_class)

        @return: A random nonce
        @rtype:  str
        """
        nonce = '%s%s' % (str(time.time()).replace('.', ''),
                          random.randrange(10 ** 6, 10 ** 7))
        return nonce

    def get_property_handler(self, property_name, widget_name):
        """\
        Return the widget specific property handler

        @see: L{add_property_handler}
        @see: L{global_property_writers}
        @see: L{_property_writers}
        """
        try:
            cls = self._property_writers[widget_name][property_name]
        except KeyError:
            cls = self.global_property_writers.get(property_name, None)
        if cls:
            return cls()
        return None

    def generate_code_background(self, obj):
        """\
        Returns the code fragment that sets the background colour of
        the given object.

        @rtype: str

        @see: L{_get_colour()}
        """
        # check if there is an code template for this property
        tmpl = self._get_code_statement('backgroundcolour')
        if not tmpl:
            msg = " %s WARNING: no code template for property '%s' " \
                  "registered!\n" % (self.comment_sign, 'backgroundcolour')
            self.warning(msg)
            return msg

        objname = self._get_code_name(obj)
        color = self._get_colour(obj.properties['background'])
        stmt = tmpl % {
            'objname': objname,
            'value':   color,
            }
        return stmt

    def generate_code_ctor(self, code_obj, is_new, tab):
        """\
        Generate constructor code for top-level object

        @param code_obj: Object to generate code for
        @type code_obj:  CodeObject
        
        @param is_new: Flag if a new file is creating
        @type is_new:  bool
        
        @param tab: Indentation
        @type tab:  str

        @rtype: list[str]
        """
        return []

    def generate_code_disabled(self, obj):
        """\
        Returns the code fragment that disables the given object.

        @rtype: str
        """
        return self._generic_code(obj, 'disabled')
        
    def generate_code_do_layout(self, builder, code_obj, is_new, tab):
        """\
        Generate code for the function C{__do_layout()}.

        If C{is_new} is set, this function returns source code for the whole
        function. Otherwise it returns just the function body framed by
        "begin wxGlade" and "end wxGlade".

        @param builder: Widget specific builder

        @param code_obj: Object to generate code for
        @type code_obj:  CodeObject

        @param is_new: Indicates if previous source code exists
        @type is_new:  bool

        @param tab: Indentation of function body
        @type tab:  str

        @rtype: list[str]

        @see: L{tmpl_name_do_layout}
        @see: L{tmpl_func_do_layout}
        @see: L{tmpl_func_empty}
        @see: L{_generate_function()}
        """
        code_lines = []
        write = code_lines.append

        # generate content of function body first
        layout_lines = self.classes[code_obj.klass].layout
        sizers_init_lines = self.classes[code_obj.klass].sizers_init

        # check if there are extra layout lines to add
        if hasattr(builder, 'get_layout_code'):
            extra_layout_lines = builder.get_layout_code(code_obj)
        else:
            extra_layout_lines = []

        if layout_lines or sizers_init_lines or extra_layout_lines:
            sizers_init_lines.reverse()
            for l in sizers_init_lines:
                write(l)
            for l in layout_lines:
                write(l)
            for l in extra_layout_lines:
                write(l)

        code_lines = self._generate_function(
            code_obj,
            is_new,
            tab,
            self.tmpl_name_do_layout,
            self.tmpl_func_do_layout,
            code_lines,
            )
        
        return code_lines

    def generate_code_event_bind(self, code_obj, tab, event_handlers):
        """\
        Generate code to bind events

        @param code_obj: Object to generate code for
        @type code_obj:  CodeObject

        @param tab: Indentation of function body
        @type tab:  str

        @param event_handlers: List of event handlers
        @type event_handlers:  list[(str, str, str)]

        @rtype: list[str]
        """
        return []

    def generate_code_event_handler(self, code_obj, is_new, tab, prev_src,
                                    event_handlers):
        """\
        Generate the event handler stubs
        
        @param code_obj: Object to generate code for
        @type code_obj:  CodeObject

        @param is_new: Indicates if previous source code exists
        @type is_new:  bool

        @param tab: Indentation of function body
        @type tab:  str

        @param prev_src: Previous source code
        @type prev_src: SourceFileContent
        
        @param event_handlers: List of event handlers
        
        @rtype: list[str]
        @see: L{tmpl_func_event_stub}
        """
        code_lines = []
        write = code_lines.append

        if prev_src and not is_new:
            already_there = prev_src.event_handlers.get(code_obj.klass, {})
        else:
            already_there = {}
            
        for win_id, event, handler, unused in event_handlers:
            # don't create handler twice
            if handler in already_there:
                continue

            # add an empty line for
            # TODO: Remove later
            if self.language in ['python', 'lisp',]:
                if not (prev_src and not is_new):
                    write('\n')
            write(self.tmpl_func_event_stub % {
                'tab':     tab,
                'klass':   self.cn_class(code_obj.klass),
                'handler': handler,
                })
            already_there[handler] = 1

        return code_lines

    def generate_code_extraproperties(self, obj):
        """\
        Returns a code fragment that set extra properties for the given object

        @rtype: list[str]
        """
        tmpl = self._get_code_statement('extraproperties')
        if not tmpl:
            return []
        objname = self._get_code_name(obj)
        prop = obj.properties['extraproperties']

        ret = []
        for name in sorted(prop):
            name_cap = name[0].upper() + name[1:]
            stmt = tmpl % {
                'klass': obj.klass,
                'objname': objname,
                'propname': name,
                'propname_cap': name_cap,
                'value': prop[name],
                }
            ret.append(stmt)
        return ret

    def generate_code_focused(self, obj):
        """\
        Returns the code fragment that get the focus to the given object.

        @rtype: str
        """
        return self._generic_code(obj, 'focused')

    def generate_code_font(self, obj):
        """\
        Returns the code fragment that sets the font of the given object.

        @rtype: str
        """
        stmt = None

        # check if there is an code template for this property
        tmpl = self._get_code_statement('setfont' )
        if not tmpl:
            msg = " %s WARNING: no code template for property '%s' " \
                  "registered!\n" % (self.comment_sign, 'setfont')
            self.warning(msg)
            return msg

        objname = self._get_code_name(obj)
        cnfont = self.cn('wxFont')
        font = obj.properties['font']
        family = self.cn(font['family'])
        face = '"%s"' % font['face'].replace('"', r'\"')
        size = font['size']
        style = self.cn(font['style'])
        underlined = font['underlined']
        weight = self.cn(font['weight'])

        stmt = tmpl % {
            'objname':    objname,
            'cnfont':     cnfont,
            'face':       face,
            'family':     family,
            'size':       size,
            'style':      style,
            'underlined': underlined,
            'weight':     weight,
            }
        return stmt

    def generate_code_foreground(self, obj):
        """\
        Returns the code fragment that sets the foreground colour of
        the given object.

        @rtype: str

        @see: L{_get_colour()}
        """
        # check if there is an code template for this property
        tmpl = self._get_code_statement('foregroundcolour' )
        if not tmpl:
            msg = " %s WARNING: no code template for property '%s' " \
                  "registered!\n" % (self.comment_sign, 'foregroundcolour')
            self.warning(msg)
            return msg

        objname = self._get_code_name(obj)
        color = self._get_colour(obj.properties['foreground'])
        stmt = tmpl % {
            'objname': objname,
            'value':   color,
            }
        return stmt

    def generate_code_hidden(self, obj):
        """\
        Returns the code fragment that hides the given object.

        @rtype: str
        """
        return self._generic_code(obj, 'hidden')

    def generate_code_id(self, obj, id=None):
        """\
        Generate the code for the widget ID.

        The parameter C{id} is evaluated first. An empty string for
        C{id} returns C{'', 'wxID_ANY'}.

        Returns a tuple of two string. The two strings are:
         1. A line to the declare the variable. It's empty if the object id
            is a constant
         2. The value of the id

        @param obj: An instance of L{xml_parse.CodeObject}
        @param id:  Widget ID definition as String.

        @rtype: (str, str)
        """
        raise NotImplementedError

    def generate_code_set_properties(self, builder, code_obj, is_new, tab):
        """\
        Generate code for the function C{__set_properties()}.

        If C{is_new} is set, this function returns source code for the whole
        function. Otherwise it returns just the function body framed by
        "begin wxGlade" and "end wxGlade".

        @param builder: Widget specific builder

        @param code_obj: Object to generate code for
        @type code_obj:  CodeObject

        @param is_new: Indicates if previous source code exists
        @type is_new:  bool

        @param tab: Indentation of function body
        @type tab:  str

        @rtype: list[str]

        @see: L{tmpl_name_set_properties}
        @see: L{tmpl_func_set_properties}
        @see: L{tmpl_func_empty}
        @see: L{_generate_function()}        
        """
        # check if there are property lines to add
        _get_properties = getattr(
            builder,
            'get_properties_code',
            self.generate_common_properties)
        property_lines = _get_properties(code_obj)
        property_lines.extend(self.classes[code_obj.klass].props)
        
        code_lines = self._generate_function(
            code_obj,
            is_new,
            tab,
            self.tmpl_name_set_properties,
            self.tmpl_func_set_properties,
            property_lines,
            )
        
        return code_lines

    def generate_code_size(self, obj):
        """\
        Returns the code fragment that sets the size of the given object.

        @rtype: str
        """
        raise NotImplementedError

    def generate_code_tooltip(self, obj):
        """\
        Returns the code fragment that sets the tooltip of the given object.

        @rtype: str
        """
        return self._generic_code(obj, 'tooltip')

    def generate_common_properties(self, widget):
        """\
        generates the code for various properties common to all widgets
        (background and foreground colours, font, ...)

        @return: a list of strings containing the generated code
        @rtype: list[str]

        @see: L{generate_code_background()}
        @see: L{generate_code_disabled()}
        @see: L{generate_code_extraproperties()}
        @see: L{generate_code_focused()}
        @see: L{generate_code_font()}
        @see: L{generate_code_foreground()}
        @see: L{generate_code_hidden()}
        @see: L{generate_code_size()}
        @see: L{generate_code_tooltip()}
        """
        prop = widget.properties
        out = []
        if prop.get('size', '').strip():
            out.append(self.generate_code_size(widget))
        if prop.get('background'):
            out.append(self.generate_code_background(widget))
        if prop.get('foreground'):
            out.append(self.generate_code_foreground(widget))
        if prop.get('font'):
            out.append(self.generate_code_font(widget))
        # tooltip
        if prop.get('tooltip'):
            out.append(self.generate_code_tooltip(widget))
        # trivial boolean properties
        if prop.get('disabled'):
            out.append(self.generate_code_disabled(widget))
        if prop.get('focused'):
            out.append(self.generate_code_focused(widget))
        if prop.get('hidden'):
            out.append(self.generate_code_hidden(widget))
        if prop.get('extraproperties') and not widget.preview:
            out.extend(self.generate_code_extraproperties(widget))
        return out

    def quote_str(self, s):
        """\
        Returns a quoted / escaped version of 's', suitable to insert in a
        source file as a string object. Takes care also of gettext support.

        Escaped are (check implementation for details):
         - quotations marks
         - backslash
         - characters with special meaning

        @param s: String to quote

        @return: A quoted / escaped version of 's'
        @rtype:  str

        @note: Please use L{quote_path()} to quote / escape filenames or
        paths.

        @note: Please check the test case 
        L{tests.test_codegen.TestCodeGen.test_quote_str()} for additional
        details about the different cases to quote and to escape.

        @note: The language specific implementations are in L{_quote_str()}.

        @see: L{_do_replace_backslashes}
        @see: L{_do_replace_doublequotes}
        @see: L{tmpl_empty_string}
        """
        if not s:
            return self.tmpl_empty_string

        # find and escape backslashes
        s = re.sub(
            r'\\\\+',
            self._do_replace_backslashes,
            s
            )
        # the string will be embedded within double quotes, thereby double
        # quotes inside have to escape
        s = re.sub(
            r'\\?"',
            self._do_replace_doublequotes,
            s,            
            )
        # a single tailing backslash breaks the quotation
        s = re.sub(
            r'(?<!\\)\\$',
            r'\\',
            s
            )

        return self._quote_str(s)

    def _quote_str(self, s):
        """\
        Language specific implementation for escaping or quoting.
        
        @see: L{quote_str()}
        """
        raise NotImplementedError

    def quote_path(self, s):
        """\
        Escapes all quotation marks and backslashes,
        thus making a path suitable to insert in a list source file

        @note: You may overwrite this function in the derived class
        @rtype: str
        """  # " ALB: to avoid emacs going insane with colorization..
        s = s.replace('\\', '\\\\')
        s = s.replace('"', r'\"')
        s = s.replace('$', r'\$')  # sigh
        s = s.replace('@', r'\@')
        return '"%s"' % s

    def save_file(self, filename, content, mainfile=False, content_only=False):
        """\
        Store the content in a file.

        A L{shebang} is added in top of all mainfiles. The permissions
        of mainfiles will be set to C{0755} too.

        L{common.save_file()} is used for storing content.

        @param filename:     File name
        @type filename:      str
        @param content:      File content
        @type content:       str
        @param mainfile:     Mainfiles gets a L{shebang} and C{0755} permissions.
        @type mainfile:      bool
        @param content_only: Write only content to the file
        @type content_only:  bool

        @see: L{common.save_file()}
        """
        # create an temporary StringIO file to add header
        tmp = ""

        # write additional information to file header
        if not content_only:
            # add shebang to main file
            if self.shebang and mainfile or self.language == 'C++':
                tmp += self.shebang

            # add file encoding notice
            if self.tmpl_encoding and self.app_encoding:
                tmp += self.tmpl_encoding % self.app_encoding

            # add created by notice
            if self.tmpl_generated_by:
                tmp += self.tmpl_generated_by % {
                    'comment_sign': self.comment_sign,
                    'generated_by': self.create_generated_by(),
                    }

            # add language specific note
            if self.language_note:
                tmp += "%s" % self.language_note

            # add a empty line
            tmp += "\n"

        # add original file content
        tmp += content

        # convert the file encoding from Unicode to self.app_encoding
        if isinstance(tmp, types.UnicodeType):
            try:
                tmp = tmp.encode(self.app_encoding)
            except UnicodeEncodeError, inst:
                raise errors.WxgOutputUnicodeError(
                    self.app_encoding,
                    inst.object[inst.start:inst.end].encode('unicode-escape'),
                    inst.start,
                    inst.end)

        # check for necessary sub directories e.g. for Perl or Python modules
        dirname = os.path.dirname(filename)
        if dirname and not os.path.isdir(dirname):
            try:
                os.makedirs(dirname)
            except:
                self._logger.exception(
                    _('Can not create output directory "%s"'), dirname
                    )

        # save the file now
        try:
            common.save_file(filename, tmp, 'codegen')
        except IOError, e:
            raise XmlParsingError(str(e))
        except:
            self._logger.exception(_('Internal Error'))
        if mainfile and sys.platform in ['linux2', 'darwin']:
            try:
                # make the file executable
                os.chmod(filename, 0755)
            except OSError, e:
                # this isn't necessarily a bad error
                self.warning(
                    _('Changing permission of main file "%s" failed: %s') % (
                        filename, str(e)
                        )
                    )

    def test_attribute(self, obj):
        """\
        Returns True if 'obj' should be added as an attribute of its parent's
        class, False if it should be created as a local variable of
        C{__do_layout}.
        
        The function returns True of the object klass is listed in
        L{classattr_always}.

        The function returns True for all widgets except sizers, if
         - the property exists and is an integer greater equal 1
         - the property does not exists
         - the property contains a non-integer value

        The function returns True for sizers, if
         - the property exists and is an integer greater equal 1

        @rtype: bool
        @see: L{classattr_always}
        """
        if obj.klass in self.classattr_always:
            return True
        try:
            return int(obj.properties['attribute'])
        except (KeyError, ValueError):
            if obj.in_sizers:
                return False
            return True  # this is the default

    def tabs(self, number):
        """\
        Return a proper formatted string for indenting lines

        @rtype: str
        """
        return self.indent_symbol * self.indent_amount * number

    def warning(self, msg):
        """\
        Show a warning message

        @param msg: Warning message
        @type msg:  str
        """
        if self._show_warnings:
            self._logger.warning(msg)

    def _content_notfound(self, source):
        """\
        Remove all the remaining <123415wxGlade ...> tags from the source
        and add a warning instead.

        This may happen if we're not generating multiple files, and one of
        the container class names is changed.

        The indentation of the string depends values detected during the
        initial parsing of the source file. Those values are stored in
        L{BaseSourceFileContent.spaces}.

        @param source: Source content with tags to replace
        @type source:  str

        @return: Changed content
        @rtype:  str
        """
        tags = re.findall(
            r'(<%swxGlade replace ([a-zA-Z_]\w*) +[.\w]+>)' % self.nonce,
            source
            )
        for tag in tags:
            # re.findall() returned a list of tuples (caused by grouping)
            # first element in tuple:  the whole match
            # second element in tuple: the class / block name
            indent = self.previous_source.spaces.get(tag[1], "")
            comment = '%(indent)s%(comment_sign)s Content of this block not found. ' \
                      'Did you rename this class?\n'
            tmpl = self._get_code_statement('contentnotfound' )
            if tmpl:
                comment += '%(indent)s%(command)s\n'
                command = tmpl
            else:
                command = ""
            comment = comment % {
                'command':      command,
                'comment_sign': self.comment_sign,
                'indent':       indent,
                }
            source = source.replace(tag[0], comment)
        return source

    def _do_replace_backslashes(self, match):
        """\
        Escape double backslashes in first RE match group
        
        @see: L{quote_str()}
        """
        return 2 * match.group(0)

    def _do_replace_doublequotes(self, match):
        """\
        Escape double quotes
        
        @see: L{quote_str()}
        """
        # " -> \"
        # \" -> \\"
        if match.group(0).startswith('\\'):
            return '\\\"'
        else:
            return '\\"'

    def _file_exists(self, filename):
        """\
        Check if the file exists

        @note: Separated for debugging purposes

        @rtype: bool
        """
        return os.path.isfile(filename)
 
    def add_object_format_name(self, name):
        """\
        Format a widget name to use in L{add_object()}.        
        
        @param name: Widget name
        @type name:  str
        @rtype: str
        @see: L{add_object()}
        """
        return name

    def _format_classattr(self, obj):
        """\
        Format the object name to store as a class attribute.
        
        @param obj: Instance of L{xml_parse.CodeObject}
        
        @rtype: str
        """
        if not obj:
            return ''
        elif not getattr(obj, 'name', None):
            return ''
        return obj.name

    def _format_comment(self, msg):
        """\
        Return message formatted to add as a comment string in generating
        source code.
        
        Trailing spaces will be removed. Leading spaces e.g. indentation
        won't be added.
        
        @type msg: str
        @rtype: str
        """
        return "%s %s" % (self.comment_sign, msg.rstrip())

    def _format_import(self, klass):
        """\
        Return formatted import statement for the given class

        @param klass: Class name
        @type klass:  str

        @rtype: str
        """
        return klass

    def _format_name(self, name):
        """\
        Format a class or a widget name by replacing forbidden characters.
        
        @rtype: str
        """
        return name

    def _format_style(self, style, code_obj):
        """\
        Return the formatted styles to insert into constructor code.
        
        The function just returned L{tmpl_style}. Write a derived version
        implementation if more logic is needed.
                
        @see: L{tmpl_style}
        
        @rtype: str
        """
        return self.tmpl_style

    def _generic_code(self, obj, prop_name):
        """\
        Create a code statement for calling a method e.g. to hide a widget.

        @param obj:       Instance of L{xml_parse.CodeObject}
        @param prop_name: Name of the property to set
        @type prop_name:  str

        @return: Code statement or None
        @rtype: str | None

        @see: L{_code_statements}
        """
        stmt = None
        value = None

        # check if there is an code template for this prop_name
        tmpl = self._get_code_statement(prop_name)
        if not tmpl:
            msg = " %s WARNING: no code template for property '%s' " \
                  "registered!\n" % (self.comment_sign, prop_name)
            self.warning(msg)
            return msg

        # collect detail informaton
        if prop_name in ['disabled', 'focused', 'hidden']:
            try:
                value = int(obj.properties[prop_name])
            except (KeyError, ValueError):
                # nothing to do
                return None
        elif prop_name == 'tooltip':
            value = self.quote_str(obj.properties['tooltip'])
        else:
            raise AssertionError("Unknown property name: %s" % prop_name)

        objname = self._get_code_name(obj)
        stmt = tmpl % {
            'objname': objname,
            'tooltip': value,
            }
        return stmt

    def _get_code_statement(self, prop_name):
        """\
        Return non-formatted code statement related to prop_name.
        
        This function handled the properties extensions described in
        L{_code_statements}.

        @param prop_name: Name of the property to set
        @type prop_name:  str

        @return: Code statement or None
        @rtype: str | None

        @see: L{_code_statements}
        """

        prop_name_major = '%s_%d' % (
            prop_name,
            self.for_version[0],
            )
        prop_name_detailed = '%s_%d%d' % (
            prop_name,
            self.for_version[0],
            self.for_version[1],
            )

        # check if there is an code template for this prop_name
        # most specific to generic
        if prop_name_detailed in self._code_statements:
            prop_name_use = prop_name_detailed 
        elif prop_name_major in self._code_statements:
            prop_name_use = prop_name_major
        elif prop_name in self._code_statements:
            prop_name_use = prop_name
        else:
            return None
            
        return self._code_statements[prop_name_use]

    def _get_code_name(self, obj):
        """\
        Returns the language specific name of the variable e.g. C{self}
        or C{$self}.

        @rtype: str
        """
        raise NotImplementedError

    def _get_colour(self, colourvalue):
        """\
        Returns the language specific colour statement
        
        @rtype: str
        """
        # check if there is an code template for this properties
        tmpl_wxcolour = self._get_code_statement('wxcolour' )
        if not tmpl_wxcolour:
            msg = " %s WARNING: no code template for property '%s' " \
                  "registered!\n" % (self.comment_sign, 'wxcolour')
            self.warning(msg)
            return msg
        tmpl_wxsystemcolour = self._get_code_statement('wxsystemcolour' )
        if not tmpl_wxsystemcolour:
            msg = " %s WARNING: no code template for property '%s' " \
                  "registered!\n" % (self.comment_sign, 'wxsystemcolour')
            self.warning(msg)
            return msg
        try:
            value = self._string_to_colour(colourvalue)
            tmpl = self.cn(tmpl_wxcolour)
        except (IndexError, ValueError):  # the color is from system settings
            value = self.cn(colourvalue)
            tmpl = self.cn(tmpl_wxsystemcolour)
        stmt = tmpl % {
            'value': value,
            }
        return stmt

    def _get_class_filename(self, klass):
        """\
        Returns the filename to store a single class in multi file projects.

        @param klass: Class name
        @type klass:  str

        @rtype: str
        """
        return ''

    def _generate_function(self, code_obj, is_new, tab, fname, ftmpl, body):
        """\
        Generic function to generate a complete function from given parts.

        @param code_obj: Object to generate code for
        @type code_obj:  CodeObject

        @param is_new: Indicates if previous source code exists
        @type is_new:  bool

        @param tab: Indentation of function body
        @type tab:  str
        
        @param fname: Name of the function
        @type fname:  str
        
        @param ftmpl: Template of the function
        @type ftmpl:  str
        
        @param body: Content of the function
        @type body:  list[str]
        
        @rtype: list[str]
        """
        code_lines = []
        write = code_lines.append

        # begin tag
        write(self.tmpl_block_begin % {
            'class_separator': self.class_separator,
            'comment_sign':    self.comment_sign,
            'function':        fname,
            'klass':           self.cn_class(code_obj.klass),
            'tab':             tab,
            })

        if body:
            for l in body:
                write(tab + l)
        else:
            write(self.tmpl_func_empty % {'tab': tab})

        # end tag
        write('%s%s end wxGlade\n' % (tab, self.comment_sign))

        # embed the content into function template
        if is_new:
            stmt = ftmpl % {
                'tab':     tab,
                'klass':   code_obj.klass,
                'content': ''.join(code_lines),
                }
            code_lines = ["%s\n" % line.rstrip() for line in stmt.split('\n')]

            # remove newline at last line
            code_lines[-1] = code_lines[-1].rstrip()

        return code_lines

    def _recode_x80_xff(self, s):
        """\
        Re-code characters in range 0x80-0xFF (Latin-1 Supplement - also
        called C1 Controls and Latin-1 Supplement) from \\xXX to \\u00XX
        """
        assert isinstance(s, types.StringType)

        def repl(matchobj):
            dec = ord(matchobj.group(0))
            if dec > 127:
                return '\u00%x' % dec
            return matchobj.group(0)

        s = re.sub(r'[\x80-\xFF]+', repl, s)

        return s

    def _source_warning(self, klass, msg, sub_obj):
        """\
        Format and add a warning message to the source code.
        
        The message msg will be split into single lines and every line will
        be properly formatted added to the source code.
        
        @param klass: Instance of L{ClassLines} to add the code in
        @param msg:   Multiline message
        @type msg:    str
        
        @param sub_obj: Object to generate code for
        @type sub_obj:  CodeObject
        
        @see: L{_format_comment()}
        """
        code_lines = []
        
        # add leading empty line
        code_lines.append('\n')
        
        # add a leading "WARNING:" to the message
        if not msg.upper().startswith(_('WARNING:')):
            msg = "%s %s" % (_('WARNING:'), msg)
        
        # add message text
        for line in msg.split('\n'):
            code_lines.append(
                "%s\n" % self._format_comment(line.rstrip())
                )

        # add tailing empty line
        code_lines.append('\n')

        # Add warning message to source code
        # TODO: Remove next three lines after C++ code gen uses dependencies
        # like Python, Perl and Lisp
        if self.language == 'C++':
            klass.init.extend(code_lines)
        else:
            klass.deps.append((sub_obj, sub_obj.parent))
            klass.child_order.append(sub_obj)
            klass.init_lines[sub_obj] = code_lines

    def _string_to_colour(self, s):
        """\
        Convert a colour values out of a hex string to comma separated
        decimal values.

        Example::
            >>> self._string_to_colour('#FFFFFF')
            '255, 255, 255'
            >>> self._string_to_colour('#ABCDEF')
            '171, 205, 239'

        @rtype:  str
        """
        return '%d, %d, %d' % (
            int(s[1:3], 16),
            int(s[3:5], 16),
            int(s[5:], 16)
            )

    def _tagcontent(self, tag, content, newline=False):
        """\
        Content embedded between C{begin wxGlade} and C{end wxGlade} sequence.

        @return: Embedded content
        @rtype:  str

        @param tag: Tag is used in C{begin wxGlade} statement for
                    separate different blocks
        @type tag:  str

        @param content: Content to enter
        @type content:  str | list[str]

        @param newline: Add a tailing empty line
        @type newline:  bool
        """
        code_list = []
        code_list.append(
            '%s begin wxGlade: %s' % (self.comment_sign, tag)
            )
        if type(content) == types.ListType:
            for entry in content:
                code_list.append(entry.rstrip())
        elif type(content) in types.StringTypes:
            # don't append empty content
            _content = content.rstrip()
            if _content:
                code_list.append(_content)
        else:
            raise AssertionError('Unknown content type: %s' % type(content))
        code_list.append(
            '%s end wxGlade' % self.comment_sign
            )
        # newline for "end wxGlade" line
        code_list.append('')
        if newline:
            code_list.append('')
        return "\n".join(code_list)

    def copy(self):
        """\
        Return a deep copy of the current instance. The instance will be
        reinitialised with defaults automatically in L{__setstate__()}.

        @see: L{__getstate__()}
        @see: L{__setstate__()}
        """
        new_codegen = copy.deepcopy(self)
        return new_codegen

    def __getstate__(self):
        """\
        Return the state of this instance except the L{_logger} and the
        L{classes} attributes.

        Both attributes caused copy errors due to file locking resp. weak
        references in XML SAX module.

        @rtype: dict
        """
        state = self.__dict__.copy()
        del state['_logger']
        del state['classes']
        return state

    def __setstate__(self, state):
        """\
        Update the instance using values from C{state}. The code generator
        will be reinitialised after the state has been updated.

        @type state: dict
        @see: L{initialize()}
        """
        self.__dict__.update(state)

        # re-initialise logger instance deleted from __getstate__ and
        # instance variables
        self._logger = logging.getLogger(self.__class__.__name__)
        self.initialize({})

# end of class BaseLangCodeWriter
