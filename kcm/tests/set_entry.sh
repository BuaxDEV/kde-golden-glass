# SPDX-FileCopyrightText: 2026 GoldenGlass contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Sourced by the test stand-ins in bin/. Like kwriteconfig6 they only change
# their own key: the rest of goldenglassrc (other groups) is kept.

# set_entry FILE GROUP KEY VALUE: writes GROUP/KEY=VALUE and leaves everything
# else alone; creates the group (and the file) if missing. Atomic replacement.
set_entry() {
  file=$1 group=$2 key=$3 value=$4
  tmp="$file.tmp.$$"
  [ -e "$file" ] || : >"$file"
  awk -v group="[$group]" -v key="$key" -v value="$value" '
    function emit() { if (!done) { print key "=" value; done = 1 } }
    /^\[.*\]$/ {
      if (in_group) emit()
      in_group = ($0 == group)
      if (in_group) seen = 1
      print
      next
    }
    in_group && index($0, key "=") == 1 { emit(); next }
    { print }
    END {
      if (in_group) emit()
      else if (!seen) { if (NR > 0) print ""; print group; emit() }
    }
  ' "$file" >"$tmp"
  mv -f "$tmp" "$file"
}
