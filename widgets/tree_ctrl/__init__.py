# __init__.py: tree ctrl widget module initialization
# $Id: __init__.py,v 1.3 2004/09/17 13:09:48 agriggio Exp $
#
# Copyright (c) 2002-2004 Alberto Griggio <agriggio@users.sourceforge.net>
# License: MIT (see license.txt)
# THIS PROGRAM COMES WITH NO WARRANTY

def initialize():
    import common
    import codegen
    codegen.initialize()
    if common.use_gui:
        import tree_ctrl
        return tree_ctrl.initialize()
