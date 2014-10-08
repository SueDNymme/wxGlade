#!/usr/bin/env lisp
;;;
;;; generated by wxGlade "faked test version"
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
(use-package :wxSizer)
(use-package :wxWindow)
(use-package :wx_main)
(use-package :wx_wrapper)
;;; end wxGlade

;;; begin wxGlade: extracode
;;; end wxGlade


(defclass StylelessDialog()
        ((top-window :initform nil :accessor slot-top-window)))

(defun make-StylelessDialog ()
        (let ((obj (make-instance 'StylelessDialog)))
          (init obj)
          (set-properties obj)
          (do-layout obj)
          obj))

(defmethod init ((obj StylelessDialog))
"Method creates the objects contained in the class."
        ;;; begin wxGlade: StylelessDialog.__init__
        ;;; end wxGlade
        )

(defmethod set-properties ((obj StylelessDialog))
        ;;; begin wxGlade: StylelessDialog.__set_properties
        (wxWindow_SetTitle (slot-dialog self) (_"Style-less Dialog"))
        ;;; end wxGlade
        )

(defmethod do-layout ((obj StylelessDialog))
        ;;; begin wxGlade: StylelessDialog.__do_layout
        (wxWindow_layout (slot-dialog self))
        ;;; end wxGlade
        )

;;; end of class StylelessDialog



(defclass StylelessFrame()
        ((top-window :initform nil :accessor slot-top-window)
        (sizer-1 :initform nil :accessor slot-sizer-1)))

(defun make-StylelessFrame ()
        (let ((obj (make-instance 'StylelessFrame)))
          (init obj)
          (set-properties obj)
          (do-layout obj)
          obj))

(defmethod init ((obj StylelessFrame))
"Method creates the objects contained in the class."
        ;;; begin wxGlade: StylelessFrame.__init__
        ;;; end wxGlade
        )

(defmethod set-properties ((obj StylelessFrame))
        ;;; begin wxGlade: StylelessFrame.__set_properties
        (wxFrame_SetTitle (slot-top-window obj) (_"Style-less Frame"))
        ;;; end wxGlade
        )

(defmethod do-layout ((obj StylelessFrame))
        ;;; begin wxGlade: StylelessFrame.__do_layout
        (setf (slot-sizer-1 obj) (wxBoxSizer_Create wxVERTICAL))
        (wxWindow_SetSizer (slot-top-window obj) (slot-sizer-1 obj))
        (wxSizer_Fit (slot-sizer-1 obj) (slot-top-window obj))
        (wxFrame_layout (slot-frame self))
        ;;; end wxGlade
        )

;;; end of class StylelessFrame


