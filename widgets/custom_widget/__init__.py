# __init__.py: custom widget module initialization
# $Id: __init__.py,v 1.5 2004/09/17 13:09:54 agriggio Exp $
#
# Copyright (c) 2002-2004 Alberto Griggio <agriggio@users.sourceforge.net>
# License: MIT (see license.txt)
# THIS PROGRAM COMES WITH NO WARRANTY

def initialize():
    import common
    import codegen
    codegen.initialize()
    if common.use_gui:
        import custom_widget
        return custom_widget.initialize()
