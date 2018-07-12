#!/usr/bin/perl
use AppConfig;
use CGI;
use DBI;
use strict;
use warnings;

print "Content-type: text/html\r\n\r\n";

$SIG{'__DIE__'} = sub {
    print 'FATAL ERROR: '.$_[0]."\n";
};

my @WARNINGS = ();
$SIG{'__WARN__'} = sub {
    push @WARNINGS, $_[0];
};

my $SCRIPT_NAME = $0;
$SCRIPT_NAME =~ s/^.*?(\w+\.(cgi|pl))$/$1/;

my $CONFIG_FILE = ($ENV{HOME} || ($ENV{DOCUMENT_ROOT} ? $ENV{DOCUMENT_ROOT}.'/..' : undef) || '.').'/.ubinote';

my $config = AppConfig->new(
    {
        GLOBAL   => { ARGCOUNT => AppConfig::ARGCOUNT_ONE },
        PEDANTIC => 1,
    },
    # mandatory settings
    'db_host', 'db_name', 'db_user', 'db_pass', 'tbl_prefix',
    # optional settings
    'app_name'=> { DEFAULT => 'Ubiquitous Notebook' },
    'charset' => { DEFAULT => 'iso-8859-1' },
    'css'     => { DEFAULT => '/style.css' },
    'sql_now' => { DEFAULT => 'NOW()' },
);

unless (-f $CONFIG_FILE) {
    die("failed to find config file at '$CONFIG_FILE'");
}

unless ($config->file($CONFIG_FILE)) {
    die("failure reading configuration from file '$CONFIG_FILE'");
}

# verify mandatory settings
foreach my $setting ('db_host', 'db_name', 'db_user', 'db_pass', 'tbl_prefix') {
    unless (defined $config->get($setting)) {
        die("mandatory configuration item '$setting' is missing in file '$CONFIG_FILE'");
    }
}

my $STYLE_PADDING_LR = 'padding-left:8px;padding-right:8px;';
my $STYLE_BGCOLOR_ODD_LINE = 'background-color:#AAAAAA;';

my $ACTION_DELETE = 'delete';
my $ACTION_SAVE = 'save';

my $PARAM_ACTION = 'action';
my $PARAM_CATEGORY = 'category';
my $PARAM_CONFIRMED = 'confirmed';
my $PARAM_ID = 'id';
my $PARAM_TXT = 'txt';
my $PARAM_VIEW = 'view';

my $VIEW_EDIT = 'edit';
my $VIEW_READ = 'read';
my $VIEW_PRINT = 'print';

my $MENU = [
    [ $VIEW_READ, 'read' ],
    [ $VIEW_EDIT, 'write' ],
];

# -----------------------------------------------------------------------------

my $cgi = new CGI;

my $cgi_action    = $cgi->param($PARAM_ACTION) || '';
my $cgi_category  = $cgi->param($PARAM_CATEGORY);
my $cgi_confirmed = $cgi->param($PARAM_CONFIRMED);
my $cgi_id        = $cgi->param($PARAM_ID) || 0;
my $cgi_txt       = $cgi->param($PARAM_TXT);
my $cgi_view      = $cgi->param($PARAM_VIEW) || $VIEW_READ;

my $dbh = DBI->connect('dbi:mysql:database='.$config->db_name().';host='.$config->db_host(),
                       $config->db_user(), $config->db_pass(),
                       { 'PrintError' => 0, 'RaiseError' => 1 });

print_header($cgi_view);

show_menu($cgi_view, $cgi_category);

# PROCESS ACTION
if ($cgi_action eq $ACTION_SAVE) {
    if (save_entry($cgi_id, $cgi_category, $cgi_txt)) {
        $cgi_id = 0; # reset filter if save operation succeeded
    }
}
elsif ($cgi_action eq $ACTION_DELETE) {
    if ($cgi_confirmed) {
        if (delete_entry($cgi_id)) {
            $cgi_id = 0; # reset filter if delete succeeded
        }
    }
    else {
        confirm_action($cgi, 'Please confirm that you want to delete the entry below.');
    }
}

# SHOW VIEW
if ($cgi_view eq $VIEW_READ) {
    show_notes({
        note_id => $cgi_id,
        category => $cgi_category,
    });
}
elsif ($cgi_view eq $VIEW_PRINT) {
    print_entry($cgi_id);
}
elsif ($cgi_view eq $VIEW_EDIT) {
    edit_entry({
        edit_id => $cgi_id,
        category => $cgi_category,
    });
}
else {
    warn "Unknown view '$cgi_view'";
}

$dbh->disconnect();
print_errors();
print_footer();

# -----------------------------------------------------------------------------

sub print_header {
    my $subname = (caller(0))[3];
    die "$subname: wrong number of arguments" unless (@_ == 1);
    my ($req_view) = @_;

    my $css = $config->css();
    my $charset = $config->charset();

    # put a prefix in the title when editing to avoid closing these browser tabs hastily
    my $title = $config->app_name();
    $title = 'EDIT - '.$title if ($req_view eq $VIEW_EDIT);

    $css = qq(<link rel="stylesheet" type="text/css" href="$css" />);
    my $div_css = q( class="page");
    # suppress style sheet in print view
    $css = $div_css = '' if ($req_view eq $VIEW_PRINT);

    print <<EOT;
<!DOCTYPE html
        PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
         "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en-US" xml:lang="en-US">
<head>
<title>$title</title>
$css
<meta http-equiv="Content-Type" content="text/html; charset=$charset" />
<script type="text/javascript">
function autofocus() {
  if (document.noteeditor.$PARAM_TXT) {
    document.noteeditor.$PARAM_TXT.focus();
  }
}
</script>
</head>
<body onload="autofocus()">
<div${div_css}>
EOT
}

sub print_footer {
    print <<EOT;

</div>
</body>
EOT
}

sub print_errors {
    return unless (@WARNINGS);
    print "<hr/>\n<b>Warnings:</b><br/>\n";
    foreach my $line (@WARNINGS) {
        print "$line<br/>\n";
    }
}

sub show_menu {
    my $subname = (caller(0))[3];
    die "$subname: wrong number of arguments" unless (@_ == 2);
    my ($req_view, $req_cat) = @_;

    return if ($req_view eq $VIEW_PRINT); # suppress menu in print view

    my @items = ();
    foreach my $arr_ref (@{$MENU}) {
        my ($view, $label) = @{$arr_ref};
        if ($view eq $req_view) {
            push @items, uc($label);
        }
        else {
            my $arg_category = (defined $req_cat ? "&$PARAM_CATEGORY=$req_cat" : '');
            push @items, qq(<a href="$SCRIPT_NAME?$PARAM_VIEW=$view$arg_category">$label</a>);
        }
    }
    print join(' | ', @items).qq(\n<hr/>\n);
}

sub confirm_action {
    my $subname = (caller(0))[3];
    die "$subname: expected two arguments" unless (@_ == 2);
    my ($cgi, $message) = @_;
    die "$subname: first argument must be a reference" unless (ref($cgi));

    my @params = $cgi->param();
    my $params_html = '';
    foreach my $param (@params) {
        my $value = $cgi->param($param);
        $params_html .= qq(<input type="hidden" name="$param" value="$value"/>);
    }

    print <<EOT;
<form action="$SCRIPT_NAME" method="post">
    <input type="hidden" name="$PARAM_CONFIRMED" value="1"/>
    $params_html
    <p>
        <b>$message</b>&nbsp;&nbsp;
        <input type="submit" value="confirm"/>
    </p>
</form>
<hr/>
EOT
}

# edit_entry $args_hashref
# args_hashref = {
#       edit_id  => int,        # optional; use undef or 0 to create a new note
#       category => int,        # optional; for new notes: preselect an item in the category picker;
#                               # ignored for existing notes where this is read from the database
# }
sub edit_entry {
    my $subname = (caller(0))[3];
    my ($args) = @_;
    my $edit_id = $args->{edit_id} || 0;
    my $ed_cat_id = $args->{category} || 0;

    my ($headline, $txt) = ('New Entry', '');

    if ($edit_id) {
        $headline = 'Edit Entry #'.$edit_id;
        ($txt, $ed_cat_id) = $dbh->selectrow_array(
            'SELECT txt, category_id'.
            ' FROM '.$config->tbl_prefix().'notebook'.
            ' WHERE note_id = '.$edit_id);
        die "$subname: nothing found for note_id = $edit_id" unless ($ed_cat_id);
    }

    my $categories = '';
    my $category_count = 0;
    foreach my $category (@{&get_categories}) {
        my ($cat_id, $cat_name) = @{$category};
        ++$category_count;
        # edit: preselect current category / new: select first category
        my $selected = (($ed_cat_id == $cat_id ||
                         ($ed_cat_id == 0 && $category_count == 1))
                        ? ' selected="selected"' : '');
        $categories .= qq(<option value="$cat_id"$selected>$cat_name</option>);
    }

    print <<EOT;
<h2>$headline</h2>
<form name="noteeditor" action="$SCRIPT_NAME" method="post">
    <input type="hidden" name="$PARAM_ACTION" value="$ACTION_SAVE"/>
    <input type="hidden" name="$PARAM_ID" value="$edit_id"/>
    <table>
        <tr>
            <td>
                Note
            </td>
            <td>
                <textarea name="$PARAM_TXT" cols="100" rows="20">$txt</textarea>
            </td>
        </tr>
        <tr>
            <td>
                Category
            </td>
            <td>
                <select name="$PARAM_CATEGORY" size="$category_count"/>
                    $categories
                </select>
            </td>
        </tr>
        <tr>
            <td>
                <input type="submit" value="save" accesskey="s"/>
            </td>
            <td>
            </td>
        </tr>
    </table>
</form>

EOT
}


# show_notes $args_hashref
# args_hashref = {
#       note_id  => int,        # use 0 to show all notes
#       category => int,        # use 0 for no filtering (show all), use undef to show the category picker only
# }
sub show_notes {
    my $subname = (caller(0))[3];
    my ($args) = @_;
    die "missing note_id argument" unless (defined $args->{note_id});

    print '<p>Category: '.(join(' | ', get_category_links())).'</p>';

    return unless (defined $args->{category});

    my $result = get_notes($args);

    my $lines = '';
    my $line_count = 0;
    foreach my $row (@{$result}) {
        my ($note_id, $txt, $lastchange, $category) = @{$row};
        my $col_action =
            qq( <a href="$SCRIPT_NAME?$PARAM_VIEW=$VIEW_EDIT&$PARAM_ID=$note_id">[edit]</a>).
            qq( <a href="$SCRIPT_NAME?$PARAM_VIEW=$VIEW_PRINT&$PARAM_ID=$note_id">[print]</a>).
            qq( <a href="$SCRIPT_NAME?$PARAM_ACTION=$ACTION_DELETE&$PARAM_ID=$note_id&$PARAM_CATEGORY=$args->{category}">[delete]</a>);
        ++$line_count;
        my $row_attribs = ($line_count % 2 == 1 ? qq(style="$STYLE_BGCOLOR_ODD_LINE") : '');

        # generate cells of table row
        $lines .= "<tr $row_attribs>";

        my $note_txt = (defined $txt ? preprocess($txt) : '');


        foreach my $col ($category, $note_txt, $lastchange, $col_action) {
            $lines .= qq(<td style="$STYLE_PADDING_LR">$col</td>);
        }
        $lines .= "</tr>\n";
    }

    if ($lines) {
        print <<EOT;
<table>
<tr>
    <th style="${STYLE_PADDING_LR}text-align:left">Category</th>
    <th style="${STYLE_PADDING_LR}text-align:left">Note</th>
    <th style="${STYLE_PADDING_LR}text-align:left">Timestamp</th>
    <th style="${STYLE_PADDING_LR}text-align:left">Action</th>
</tr>
$lines
</table>
EOT
    }
    else {
        print "<p>Nothing found.</p>\n";
    }
}


sub print_entry {
    my $subname = (caller(0))[3];
    die "$subname: wrong number of arguments" unless (@_ == 1);
    my ($note_id) = @_;

    my $result = read_note_by_id($note_id);

    warn "note#$note_id not found." unless (@{$result} > 0);

    # note text is expected in the result set's 1st row, 2nd field
    my $note_txt = $result->[0]->[1];

    $note_txt = (defined $note_txt ? preprocess($note_txt) : '');

    print $note_txt;
}


sub save_entry {
    my $subname = (caller(0))[3];
    unless (@_ == 3) {
        warn "$subname: wrong number of arguments";
        return;
    }
    my ($pk, $category_id, $txt) = @_;

    unless (defined $category_id && defined $txt) {
        warn "$subname: undef arguments not supported";
        return;
    }

    # trim leading/trailing whitespace
    $txt =~ s/^\s+|\s+$//g;
    undef $txt if (length($txt) == 0);

    my $affected = 0;

    if ($pk) {
        $affected = $dbh->do(sprintf(
            "UPDATE %snotebook".
            " SET category_id = %d, txt = %s, lastchange = %s".
            " WHERE note_id = %d",
            $config->tbl_prefix(),
            $category_id, $dbh->quote($txt), $config->sql_now(),
            $pk));
    }
    else {
        $affected = $dbh->do(sprintf(
            "INSERT INTO %snotebook".
            ' (category_id, txt, lastchange)'.
            " VALUES (%d, %s, %s)",
            $config->tbl_prefix(),
            $category_id, $dbh->quote($txt), $config->sql_now()));
    }

    warn "$subname: $affected rows affected" if ($affected != 1);

    return ($affected == 1);
}


sub delete_entry {
    my $subname = (caller(0))[3];
    unless (@_ == 1) {
        warn "$subname: wrong number of arguments";
        return;
    }
    my ($pk) = @_;

    # delete given entry only if it has not been settled yet
    my $affected = $dbh->do(
        'DELETE FROM '.$config->tbl_prefix().'notebook'.
        ' WHERE note_id='.$pk);
    warn "$subname: $affected rows affected" if ($affected != 1);

    return ($affected == 1);
}

sub get_categories {
    return $dbh->selectall_arrayref(
        'SELECT category_id, name'.
        ' FROM '.$config->tbl_prefix().'category'.
        ' ORDER BY category_id');
}

# Returns a list of html links. When followed they show the notebook filtered by category
sub get_category_links {
    my @result = ();

    foreach my $category ([0, 'ALL'], @{&get_categories}) {
        my ($cat_id, $cat_name) = @{$category};
        push @result, qq(<a href="$SCRIPT_NAME?$PARAM_VIEW=$VIEW_READ&$PARAM_CATEGORY=$cat_id">$cat_name</a>);
    }

    return @result;
}

# Expects the args hash from show_notes as input parameter.
# Returns a reference to an array of arrays (selectall_arrayref result).
sub get_notes {
    my $subname = (caller(0))[3];
    die "$subname: wrong number of arguments" unless (@_ == 1);
    my ($args) = @_;
    my $result;

    if ($args->{note_id}) {
        $result = read_note_by_id($args->{note_id});
    }
    elsif ($args->{category}) {
        $result = read_notes_by_category($args->{category});
    }
    else {
        $result = read_all_notes();
    }

    return $result;
}

sub read_note_by_id {
    my $subname = (caller(0))[3];
    die "$subname: wrong number of arguments" unless (@_ == 1);
    my ($note_id) = @_;

    return $dbh->selectall_arrayref(sprintf(
        'SELECT n.note_id, n.txt, n.lastchange, c.name'.
        ' FROM %snotebook n, %scategory c'.
        ' WHERE n.category_id = c.category_id'.
        ' AND n.note_id = %d',
        $config->tbl_prefix(), $config->tbl_prefix(), $note_id));
}

sub read_notes_by_category {
    my $subname = (caller(0))[3];
    die "$subname: wrong number of arguments" unless (@_ == 1);
    my ($category_id) = @_;

    return $dbh->selectall_arrayref(sprintf(
        'SELECT n.note_id, n.txt, n.lastchange, c.name'.
        ' FROM %snotebook n, %scategory c'.
        ' WHERE n.category_id = c.category_id'.
        ' AND n.category_id = %d'.
        ' ORDER BY n.lastchange DESC, n.note_id DESC',
        $config->tbl_prefix(), $config->tbl_prefix(), $category_id));
}

sub read_all_notes {
    return $dbh->selectall_arrayref(sprintf(
        'SELECT n.note_id, n.txt, n.lastchange, c.name'.
        ' FROM %snotebook n, %scategory c'.
        ' WHERE n.category_id = c.category_id'.
        ' ORDER BY n.lastchange DESC, n.note_id DESC',
        $config->tbl_prefix(), $config->tbl_prefix()));
}

sub preprocess {
    my $subname = (caller(0))[3];
    die "$subname: wrong number of arguments" unless (@_ == 1);
    my ($txt) = @_;

    my @lines = split /\R/, $txt;

    preprocess_hyperlinks(\@lines);
    preprocess_markup(\@lines);

    return join("<br/>\n", @lines);
}

# Finds urls and creates html links.
sub preprocess_hyperlinks {
    my $subname = (caller(0))[3];
    die "$subname: wrong number of arguments" unless (@_ == 1);
    my ($lines) = @_;

    foreach my $line (@{$lines}) {
        while ($line =~ m{(^|\s)(([a-z]+://[^/\s]+/?)(\S*))}) {
            my ($whitespace, $url, $location, $path) = ($1, $2, $3, $4);
            my $display_url = $location.($path ? '...' : '');
            $line =
                substr($line, 0, $-[0]).
                ($whitespace || '').
                qq{<a href="$url">$display_url</a>}.
                substr($line, $+[0]);
        }
    }
}

# Converts wiki-like markup to html.
sub preprocess_markup {
    my $subname = (caller(0))[3];
    die "$subname: wrong number of arguments" unless (@_ == 1);
    my ($lines) = @_;

    foreach my $line (@{$lines}) {
        # characters surrounded by at least two asterisks become bold
        $line =~ s|\*{2,}(.+?)\*{2,}|<b>$1</b>|g;

        # characters surrounded by at least two underscores become emphasized
        $line =~ s|_{2,}(.+?)_{2,}|<em>$1</em>|g;

        # create links to amazon for ASIN key/value pairs
        $line =~ s|\bASIN[:=\s]\s*(\w+)\b|<a href="http://www.amazon.de/gp/product/$1">Amazon#$1</a>|g;

        # asterisks at the beginning of a line are replaced by indentation and bullet symbols
        if ($line =~ m|^(\*+)|) {
            my $depth = length($1);
            my $indent = '';
            for (my $count = 1; $count < $depth; ++$count) {
                $indent .= '&nbsp;&nbsp;&nbsp;';
            }
            $line = $indent.get_bullet_symbol($depth).substr($line, $depth);
        }
    }
}

sub get_bullet_symbol {
    my $subname = (caller(0))[3];
    die "$subname: wrong number of arguments" unless (@_ == 1);
    my ($depth) = @_;

    my $bullets_by_depth = {
            '1' => '&bull;',
            '2' => '&diams;',
            '3' => '&loz;',
    };

    return $bullets_by_depth->{$depth} || '&bull;';
}
