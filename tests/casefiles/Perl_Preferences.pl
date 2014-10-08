#!/usr/bin/perl -w -- 
#
# generated by wxGlade "faked test version"
#
# To get wxPerl visit http://wxPerl.sourceforge.net/
#

use Wx 0.15 qw[:allclasses];
use strict;

# begin wxGlade: dependencies
# end wxGlade

# begin wxGlade: extracode
# end wxGlade

package wxGladePreferencesUI;

use Wx qw[:everything];
use base qw(Wx::Dialog);
use strict;

use Wx::Locale gettext => '_T';
sub new {
    my( $self, $parent, $id, $title, $pos, $size, $style, $name ) = @_;
    $parent = undef              unless defined $parent;
    $id     = -1                 unless defined $id;
    $title  = ""                 unless defined $title;
    $pos    = wxDefaultPosition  unless defined $pos;
    $size   = wxDefaultSize      unless defined $size;
    $name   = ""                 unless defined $name;

    # begin wxGlade: wxGladePreferencesUI::new
    $style = wxDEFAULT_DIALOG_STYLE 
        unless defined $style;

    $self = $self->SUPER::new( $parent, $id, $title, $pos, $size, $style, $name );
    $self->{notebook_1} = Wx::Notebook->new($self, wxID_ANY);
    $self->{notebook_1_pane_1} = Wx::Panel->new($self->{notebook_1}, wxID_ANY, wxDefaultPosition, wxDefaultSize, );
    $self->{use_menu_icons} = Wx::CheckBox->new($self->{notebook_1_pane_1}, wxID_ANY, _T("Use icons in menu items"));
    $self->{frame_tool_win} = Wx::CheckBox->new($self->{notebook_1_pane_1}, wxID_ANY, _T("Show properties and tree windows as small frames"));
    $self->{show_progress} = Wx::CheckBox->new($self->{notebook_1_pane_1}, wxID_ANY, _T("Show progress dialog when loading wxg files"));
    $self->{remember_geometry} = Wx::CheckBox->new($self->{notebook_1_pane_1}, wxID_ANY, _T("Remember position and size of wxGlade windows"));
    $self->{show_sizer_handle} = Wx::CheckBox->new($self->{notebook_1_pane_1}, wxID_ANY, _T("Show \"handles\" of sizers"));
    $self->{use_kde_dialogs} = Wx::CheckBox->new($self->{notebook_1_pane_1}, wxID_ANY, _T("Use native file dialogs on KDE"));
    $self->{open_save_path} = Wx::TextCtrl->new($self->{notebook_1_pane_1}, wxID_ANY, "");
    $self->{codegen_path} = Wx::TextCtrl->new($self->{notebook_1_pane_1}, wxID_ANY, "");
    $self->{number_history} = Wx::SpinCtrl->new($self->{notebook_1_pane_1}, wxID_ANY, "4", wxDefaultPosition, wxDefaultSize, wxSP_ARROW_KEYS, 0, 100, 4);
    $self->{buttons_per_row} = Wx::SpinCtrl->new($self->{notebook_1_pane_1}, wxID_ANY, "5", wxDefaultPosition, wxDefaultSize, wxSP_ARROW_KEYS, 1, 100, 5);
    $self->{notebook_1_pane_2} = Wx::Panel->new($self->{notebook_1}, wxID_ANY, wxDefaultPosition, wxDefaultSize, );
    $self->{use_dialog_units} = Wx::CheckBox->new($self->{notebook_1_pane_2}, wxID_ANY, _T("Use dialog units by default for size properties"));
    $self->{wxg_backup} = Wx::CheckBox->new($self->{notebook_1_pane_2}, wxID_ANY, _T("Create backup wxg files"));
    $self->{codegen_backup} = Wx::CheckBox->new($self->{notebook_1_pane_2}, wxID_ANY, _T("Create backup files for generated source"));
    $self->{allow_duplicate_names} = Wx::CheckBox->new($self->{notebook_1_pane_2}, wxID_ANY, _T("Allow duplicate widget names"));
    $self->{default_border} = Wx::CheckBox->new($self->{notebook_1_pane_2}, wxID_ANY, _T("Default border width for widgets"));
    $self->{default_border_size} = Wx::SpinCtrl->new($self->{notebook_1_pane_2}, wxID_ANY, "", wxDefaultPosition, wxDefaultSize, wxSP_ARROW_KEYS, 0, 20, );
    $self->{autosave} = Wx::CheckBox->new($self->{notebook_1_pane_2}, wxID_ANY, _T("Auto save wxg files every "));
    $self->{autosave_delay} = Wx::SpinCtrl->new($self->{notebook_1_pane_2}, wxID_ANY, "120", wxDefaultPosition, wxDefaultSize, wxSP_ARROW_KEYS, 30, 300, 120);
    $self->{write_timestamp} = Wx::CheckBox->new($self->{notebook_1_pane_2}, wxID_ANY, _T("Insert timestamp on generated source files"));
    $self->{write_generated_from} = Wx::CheckBox->new($self->{notebook_1_pane_2}, wxID_ANY, _T("Insert .wxg file name on generated source files"));
    $self->{backup_suffix} = Wx::RadioBox->new($self->{notebook_1_pane_2}, wxID_ANY, _T("Backup options"), wxDefaultPosition, wxDefaultSize, [_T("append ~ to filename"), _T("append .bak to filename")], 2, wxRA_SPECIFY_COLS);
    $self->{local_widget_path} = Wx::TextCtrl->new($self->{notebook_1_pane_2}, wxID_ANY, "");
    $self->{choose_widget_path} = Wx::Button->new($self->{notebook_1_pane_2}, wxID_ANY, _T("..."), wxDefaultPosition, wxDefaultSize, wxBU_EXACTFIT);
    $self->{sizer_6_staticbox} = Wx::StaticBox->new($self->{notebook_1_pane_2}, wxID_ANY, _T("Local widget path") );
    $self->{ok} = Wx::Button->new($self, wxID_OK, "");
    $self->{cancel} = Wx::Button->new($self, wxID_CANCEL, "");

    $self->__set_properties();
    $self->__do_layout();

    # end wxGlade
    return $self;

}


sub __set_properties {
    my $self = shift;
    # begin wxGlade: wxGladePreferencesUI::__set_properties
    $self->SetTitle(_T("wxGlade: preferences"));
    my $icon = &Wx::wxNullIcon();
    $icon->CopyFromBitmap(Wx::Bitmap->new(_T("icons/icon.xpm"), wxBITMAP_TYPE_ANY));
    $self->SetIcon($icon);
    $self->{use_menu_icons}->SetValue(1);
    $self->{frame_tool_win}->SetValue(1);
    $self->{show_progress}->SetValue(1);
    $self->{remember_geometry}->SetValue(1);
    $self->{show_sizer_handle}->SetValue(1);
    $self->{use_kde_dialogs}->SetValue(1);
    $self->{open_save_path}->SetMinSize(Wx::Size->new(196, -1));
    $self->{codegen_path}->SetMinSize(Wx::Size->new(196, -1));
    $self->{number_history}->SetMinSize(Wx::Size->new(196, -1));
    $self->{buttons_per_row}->SetMinSize(Wx::Size->new(196, -1));
    $self->{wxg_backup}->SetValue(1);
    $self->{codegen_backup}->SetValue(1);
    $self->{allow_duplicate_names}->Show(0);
    $self->{default_border_size}->SetMinSize(Wx::Size->new(45, 22));
    $self->{autosave_delay}->SetMinSize(Wx::Size->new(45, 22));
    $self->{write_timestamp}->SetValue(1);
    $self->{backup_suffix}->SetSelection(0);
    $self->{ok}->SetDefault();
    # end wxGlade
}

sub __do_layout {
    my $self = shift;
    # begin wxGlade: wxGladePreferencesUI::__do_layout
    $self->{sizer_1} = Wx::BoxSizer->new(wxVERTICAL);
    $self->{sizer_2} = Wx::BoxSizer->new(wxHORIZONTAL);
    $self->{sizer_5} = Wx::BoxSizer->new(wxVERTICAL);
    $self->{sizer_6_staticbox}->Lower();
    $self->{sizer_6} = Wx::StaticBoxSizer->new($self->{sizer_6_staticbox}, wxHORIZONTAL);
    $self->{sizer_7_copy} = Wx::BoxSizer->new(wxHORIZONTAL);
    $self->{sizer_7} = Wx::BoxSizer->new(wxHORIZONTAL);
    $self->{sizer_3} = Wx::BoxSizer->new(wxVERTICAL);
    $self->{sizer_4} = Wx::FlexGridSizer->new(4, 2, 0, 0);
    $self->{sizer_3}->Add($self->{use_menu_icons}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_3}->Add($self->{frame_tool_win}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_3}->Add($self->{show_progress}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_3}->Add($self->{remember_geometry}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_3}->Add($self->{show_sizer_handle}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_3}->Add($self->{use_kde_dialogs}, 0, wxALL|wxEXPAND, 5);
    my $label_1 = Wx::StaticText->new($self->{notebook_1_pane_1}, wxID_ANY, _T("Initial path for \nfile opening/saving dialogs:"));
    $self->{sizer_4}->Add($label_1, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5);
    $self->{sizer_4}->Add($self->{open_save_path}, 1, wxALIGN_CENTER_VERTICAL|wxALL, 5);
    my $label_2_copy = Wx::StaticText->new($self->{notebook_1_pane_1}, wxID_ANY, _T("Initial path for \ncode generation file dialogs:"));
    $self->{sizer_4}->Add($label_2_copy, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5);
    $self->{sizer_4}->Add($self->{codegen_path}, 1, wxALIGN_CENTER_VERTICAL|wxALL, 5);
    my $label_2 = Wx::StaticText->new($self->{notebook_1_pane_1}, wxID_ANY, _T("Number of items in file history"));
    $self->{sizer_4}->Add($label_2, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5);
    $self->{sizer_4}->Add($self->{number_history}, 1, wxALIGN_CENTER_VERTICAL|wxALL, 5);
    my $label_2_copy_1 = Wx::StaticText->new($self->{notebook_1_pane_1}, wxID_ANY, _T("Number of buttons per row\nin the main palette"));
    $self->{sizer_4}->Add($label_2_copy_1, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5);
    $self->{sizer_4}->Add($self->{buttons_per_row}, 1, wxALIGN_CENTER_VERTICAL|wxALL, 5);
    $self->{sizer_4}->AddGrowableCol(1);
    $self->{sizer_3}->Add($self->{sizer_4}, 0, wxEXPAND, 3);
    $self->{notebook_1_pane_1}->SetSizer($self->{sizer_3});
    $self->{sizer_5}->Add($self->{use_dialog_units}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_5}->Add($self->{wxg_backup}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_5}->Add($self->{codegen_backup}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_5}->Add($self->{allow_duplicate_names}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_7}->Add($self->{default_border}, 0, wxALIGN_CENTER_VERTICAL|wxALL, 5);
    $self->{sizer_7}->Add($self->{default_border_size}, 0, wxALL, 5);
    $self->{sizer_5}->Add($self->{sizer_7}, 0, wxEXPAND, 0);
    $self->{sizer_7_copy}->Add($self->{autosave}, 0, wxALIGN_CENTER_VERTICAL|wxBOTTOM|wxLEFT|wxTOP, 5);
    $self->{sizer_7_copy}->Add($self->{autosave_delay}, 0, wxBOTTOM|wxTOP, 5);
    my $label_3 = Wx::StaticText->new($self->{notebook_1_pane_2}, wxID_ANY, _T(" seconds"));
    $self->{sizer_7_copy}->Add($label_3, 0, wxALIGN_CENTER_VERTICAL|wxBOTTOM|wxFIXED_MINSIZE|wxTOP, 5);
    $self->{sizer_5}->Add($self->{sizer_7_copy}, 0, wxEXPAND, 0);
    $self->{sizer_5}->Add($self->{write_timestamp}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_5}->Add($self->{write_generated_from}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_5}->Add($self->{backup_suffix}, 0, wxALL|wxEXPAND, 5);
    $self->{sizer_6}->Add($self->{local_widget_path}, 1, wxALL, 3);
    $self->{sizer_6}->Add($self->{choose_widget_path}, 0, wxALIGN_CENTER_VERTICAL|wxALL, 3);
    $self->{sizer_5}->Add($self->{sizer_6}, 0, wxALL|wxEXPAND, 5);
    $self->{notebook_1_pane_2}->SetSizer($self->{sizer_5});
    $self->{notebook_1}->AddPage($self->{notebook_1_pane_1}, _T("Interface"));
    $self->{notebook_1}->AddPage($self->{notebook_1_pane_2}, _T("Other"));
    $self->{sizer_1}->Add($self->{notebook_1}, 1, wxALL|wxEXPAND, 5);
    $self->{sizer_2}->Add($self->{ok}, 0, 0, 0);
    $self->{sizer_2}->Add($self->{cancel}, 0, wxLEFT, 10);
    $self->{sizer_1}->Add($self->{sizer_2}, 0, wxALIGN_RIGHT|wxALL, 10);
    $self->SetSizer($self->{sizer_1});
    $self->{sizer_1}->Fit($self);
    $self->Layout();
    $self->Centre();
    # end wxGlade
}

# end of class wxGladePreferencesUI

1;

