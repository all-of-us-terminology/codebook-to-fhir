#!/bin/bash

git checkout gh-pages
git rm -rf CodeSystem sheets
cp -r dist/CodeSystem/ dist/sheets/ .
git add CodeSystem/ sheets/
git commit -m "Publish v$1"
git tag $1
git checkout master
rm -rf sheets CodeSystem
