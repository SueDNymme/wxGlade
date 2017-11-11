// -*- C++ -*-
//
// generated by wxGlade "faked test version"
//
// Example for compiling a single file project under Linux using g++:
//  g++ MyApp.cpp $(wx-config --libs) $(wx-config --cxxflags) -o MyApp
//
// Example for compiling a multi file project under Linux using g++:
//  g++ main.cpp $(wx-config --libs) $(wx-config --cxxflags) -o MyApp Dialog1.cpp Frame1.cpp
//

#include <wx/wx.h>
#include "Bug179_Frame.hpp"

// begin wxGlade: ::extracode
// end wxGlade


Bug179_Frame::Bug179_Frame(wxWindow* parent, wxWindowID id, const wxString& title, const wxPoint& pos, const wxSize& size, long style):
    wxFrame(parent, id, title, pos, size, style)
{
    // begin wxGlade: Bug179_Frame::Bug179_Frame
    label_1 = new wxStaticText(this, wxID_ANY, _("Just a label"));

    set_properties();
    do_layout();
    // end wxGlade
}


void Bug179_Frame::set_properties()
{
    // begin wxGlade: Bug179_Frame::set_properties
    SetTitle(_("frame_1"));
    // end wxGlade
}


void Bug179_Frame::do_layout()
{
    // begin wxGlade: Bug179_Frame::do_layout
    wxBoxSizer* sizer_1 = new wxBoxSizer(wxVERTICAL);
    sizer_1->Add(label_1, 1, wxALL|wxEXPAND, 5);
    SetSizer(sizer_1);
    sizer_1->Fit(this);
    Layout();
    // end wxGlade
}

