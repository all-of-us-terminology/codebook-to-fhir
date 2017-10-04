#!/bin/bash

set -e


VERSION="v$(cat dist/version)"
echo "Run with tag $VERSION"


git checkout gh-pages
git rm -rf CodeSystem sheets
cp -r dist/CodeSystem/ CodeSystem
cp -r dist/sheets/ sheets
git add CodeSystem/ sheets/
git commit -m "Publish $VERSION"
git tag $VERSION
git checkout master
rm -rf sheets CodeSystem
