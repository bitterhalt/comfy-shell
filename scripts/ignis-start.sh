#!/usr/bin/env bash

log="$HOME/.cache/ignis.log"

kill() {
  pkill ignis
}

case "$1" in
stop)
  pkill ignis
  ;;
*)
  if pgrep -x "ignis" >/dev/null; then
    pkill ignis
    sleep 1
    ignis init >"$log" 2>&1 &
  else
    ignis init >"$log" 2>&1 &
  fi
  ;;

esac
