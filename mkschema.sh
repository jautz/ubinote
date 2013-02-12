#!/bin/bash
prefix="$1"
shift
[ -z "$prefix" ] && {
    cat <<EOT
Usage:
    $0 <table-prefix>

Example:
    $0 ubi_
EOT
    exit 1
}

cat schema-template.mysql | sed "s/tblprefix_/$prefix/g" > schema.mysql
