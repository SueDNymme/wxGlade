#!/usr/bin/env lisp
;;;
;;; generated by wxGlade 0.9.9pre on Wed Oct  9 21:43:25 2019
;;;

(asdf:operate 'asdf:load-op 'wxcl)
(use-package "FFI")
(ffi:default-foreign-language :stdc)


;;; begin wxGlade: dependencies
(use-package :wxCL)
(use-package :wxColour)
(use-package :wxEvent)
(use-package :wxEvtHandler)
(use-package :wxFrame)
(use-package :wxMenu)
(use-package :wxMenuBar)
(use-package :wxSizer)
(use-package :wxToolBar)
(use-package :wxWindow)
(use-package :wx_main)
(use-package :wx_wrapper)
;;; end wxGlade

;;; begin wxGlade: extracode
;;; end wxGlade


(defclass MyFrame()
        ((top-window :initform nil :accessor slot-top-window)
        (frame-menubar :initform nil :accessor slot-frame-menubar)
        (frame-toolbar :initform nil :accessor slot-frame-toolbar)
        (sizer-1 :initform nil :accessor slot-sizer-1)))

(defun make-MyFrame ()
        (let ((obj (make-instance 'MyFrame)))
          (init obj)
          (set-properties obj)
          (do-layout obj)
          obj))

(defmethod init ((obj MyFrame))
"Method creates the objects contained in the class."
        ;;; begin wxGlade: MyFrame.__init__
        (setf (slot-top-window obj) (wxFrame_create nil wxID_ANY "" -1 -1 -1 -1 wxDEFAULT_FRAME_STYLE))
        (slot-top-window obj).wxWindow_SetSize((400, 300))
        (wxFrame_SetTitle (slot-top-window obj) "frame")
        
        ;;; Menu Bar
        (setf (slot-frame-menubar obj) (wxMenuBar_Create 0))
        (let ((wxglade_tmp_menu (wxMenu_Create "" 0)))
        (wxMenu_Append wxglade_tmp_menu wxID_ANY "My Menu Item 1" "" 0)
        (wxMenu_Append wxglade_tmp_menu wxID_ANY "My Menu Item 1" "without attribute name" 0)
        		(wxMenuBar_Append (slot-frame-menubar obj) wxglade_tmp_menu "Menu 1"))
        (wxFrame_SetMenuBar (slot-top-window obj) (slot-frame-menubar obj))
        ;;; Menu Bar end        
        
        ;;; Tool Bar
        (setf (slot-frame-toolbar obj) (wxToolBar_Create (slot-top-window obj) -1 -1 -1 -1 -1 wxTB_HORIZONTAL))
        (wxToolBar_AddTool (slot-frame-toolbar obj) wxID_ANY "My Tool" (wxBitmap_CreateLoad "D:\\Python\\wxglade\\wxglade_dev_master\\icons\\button.xpm" wxBITMAP_TYPE_ANY) wxNullBitmap wxITEM_NORMAL "" "")
        (wxToolBar_Realize (slot-frame-toolbar obj))
        (wxToolBar_Realize (slot-frame-toolbar obj))
        (wxFrame_SetToolBar (slot-top-window obj) (slot-frame-toolbar obj))
        ;;; Tool Bar end
        
        (setf (slot-sizer-1 obj) (wxBoxSizer_Create wxVERTICAL))
        
        (wxSizer_AddWindow (slot-sizer-1 obj) ((0, 0) obj) 0 0 0 nil)
        
        (wxWindow_SetSizer (slot-top-window obj) (slot-sizer-1 obj))
        
        (wxFrame_layout (slot-frame self))
        ;;; end wxGlade
        )

;;; end of class MyFrame


(defun init-func (fun data evt)
        (let ((frame (make-MyFrame)))
        (ELJApp_SetTopWindow (slot-top-window frame))
        (wxWindow_Show (slot-top-window frame))))
;;; end of class MyApp


(unwind-protect
    (Eljapp_initializeC (wxclosure_Create #'init-func nil) 0 nil)
    (ffi:close-foreign-library "../miscellaneous/wxc-msw2.6.2.dll"))
