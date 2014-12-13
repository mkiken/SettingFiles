#!/bin/sh

cli=/Applications/Karabiner.app/Contents/Library/bin/karabiner

$cli set repeat.wait 13
/bin/echo -n .
$cli set repeat.initial_wait 200
/bin/echo -n .
$cli set remap.jis_escape2eisuuAndEscape 1
/bin/echo -n .
/bin/echo
