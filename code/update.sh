#!/bin/bash

CURDIR="${BASH_SOURCE[0]}";RL="readlink";([[ `uname -s`=='Darwin' ]] || RL="$RL -f")
while([ -h "${CURDIR}" ]) do CURDIR=`$RL "${CURDIR}"`; done
N="/dev/null";pushd .>$N;cd `dirname ${CURDIR}`>$N;CURDIR=`pwd`;popd>$N

echo "*** Downloading updates ***"
git -C $CURDIR pull

echo "*** Installing updates ***"
$CURDIR/bin/pip install -e $CURDIR/zato-cy
$CURDIR/bin/pip install -e $CURDIR/zato-lib
$CURDIR/bin/pip install -r $CURDIR/requirements.txt

