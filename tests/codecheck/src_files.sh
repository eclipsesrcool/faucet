#!/bin/bash

FAUCETHOME=`dirname $0`"/../.."
TMPFILE=`tempfile`.srcfiles

if [[ "$*" == "" ]] ; then
  for i in clib faucet tests ; do find $FAUCETHOME/$i/ -type f -name [a-z]*.py ; done | xargs realpath > $TMPFILE || exit 1
else
  (cd $FAUCETHOME && readlink -f $*) > $TMPFILE || exit 1
fi

sort < $TMPFILE || exit 1
rm -f $TMPFILE
exit 0
